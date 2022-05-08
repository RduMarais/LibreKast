# chat/consumers.py
import json
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.generic.websocket import WebsocketConsumer
from bleach import clean
from django.conf import settings
import threading

from .models import Choice, Question, Meeting,Attendee,Vote
from .views import get_previous_user_answers
from .youtube_handler import YoutubeHandler
from .twitch_handler import TwitchHandler


# there are 3 group channels joined if needed : 
# * meeting_group_name = evryone on the meeting (used for word cloud, results, and the questions content)
# * _admin : admins only (used for live results)
# * _chat : anyone that wants to get the live chat (used for live chat, obviously)
class MeetingConsumer(WebsocketConsumer):

	def check_attendee(self,username,is_subscriber=False,is_twitch=False,is_youtube=False):
		attendee = None
		attendee_queryset = self.meeting.attendee_set.all().filter(name=username)
		if(attendee_queryset): # is this secure ?
			attendee = attendee_queryset[0]
		else:
			attendee = Attendee(name=username,meeting=self.meeting,score=0,is_subscriber=is_subscriber,is_twitch=is_twitch,is_youtube=is_youtube)
			attendee.save()
		return attendee

	def connect(self):
		meeting_id = self.scope['url_route']['kwargs']['meeting_id']  
		self.meeting = Meeting.objects.get(pk=meeting_id)
		self.meeting_group_name = 'meeting_'+str(self.meeting.id)

		# Join group
		async_to_sync(self.channel_layer.group_add)(
			self.meeting_group_name,
			self.channel_name
		)
		# join admin group if needed
		if(self.is_user_authenticated()):
			async_to_sync(self.channel_layer.group_add)(
				self.meeting_group_name+'_admin',
				self.channel_name
			)
			async_to_sync(self.channel_layer.group_add)(
				self.meeting_group_name+'_chat',
				self.channel_name
			)

		self.accept()

		# setup user session
		if('attendee_id' in self.scope['session']):
			attendee_id = self.scope['session']['attendee_id']
			self.attendee = Attendee.objects.get(pk=attendee_id)
		elif(self.is_user_authenticated()):
			print(self.scope['user'].username)
		else:
			self.send(text_data=json.dumps({'message':'error no login'}))
		
		# ADMIN settings
		if(self.is_user_authenticated() and not hasattr(self, 'isAdmin')): 
			# check isAdmin ensures that there is always only one consumer for twitch and Youtube (but there may be several admins in the meeting)
			self.isAdmin = True
			# INIT live stream
			if(self.meeting.platform == 'YT' or self.meeting.platform == 'MX'):
				self.init_yt_polling()
			if(self.meeting.platform == 'TW' or self.meeting.platform == 'MX'):
				self.init_tw_polling()

	# leave group
	def disconnect(self, close_code):
		async_to_sync(self.channel_layer.group_discard)(
			self.meeting_group_name,
			self.channel_name
		)
		if(self.meeting.platform == 'YT' or self.meeting.platform == 'MX'):
			self.terminate_yt_polling()
		if(self.meeting.platform == 'TW' or self.meeting.platform == 'MX'):
			self.terminate_tw_polling()

	# Receive message from meeting group
	def meeting_message(self, event):
		message = event['message']
		# Send message to WebSocket
		self.send(text_data=json.dumps(message))

	def admin_message(self,event):
		message = event['message']
		# if(self.isAdmin):
		self.send(text_data=json.dumps(message))


	# handle message received from the client
	# This is the API
	def receive(self, text_data):
		text_data_json = json.loads(text_data)
		message_in = text_data_json['message']  # this is the format that should be modified
		
		if(settings.DEBUG):
			print('RECV : '+message_in)

		####################################
		#### THE MAIN APP LOGIC is here ####
		####################################
		if(message_in == "debug-question-start"):
			question = self.meeting.current_question()
			self.send_group_question(question)
		elif(message_in == "vote"):
			if(settings.DEBUG):
				print('debug : json data : '+str(text_data_json))
			async_to_sync(self.receive_vote(text_data_json,self.attendee))
		elif(message_in == "get-score"):
			self.send(text_data=json.dumps({
				'message':'update-score',
				'score':self.attendee.score,
				}))
		elif(message_in == "word-cloud-add"):
			word = clean(text_data_json['word'])
			async_to_sync(self.add_word(word,self.attendee))
			async_to_sync(self.notify_add_word(word))
		elif(message_in == "get-scoreboard"):
			self.send_scoreboard()
		elif(message_in == "admin-send-scoreboard"):
			if(self.is_user_authenticated()):
				self.send_group_scoreboard()
		elif(message_in == "admin-get-current-question"):
				question = self.meeting.current_question()
				self.send_current_question(question)
		elif(message_in == "admin-question-start"):
			if(self.is_user_authenticated()):
				question = self.meeting.current_question()
				self.send_group_question(question)
				if((self.meeting.platform == 'YT' or self.meeting.platform == 'MX') and question.question_type != 'TX'):
					self.start_yt_polling(question)
				if((self.meeting.platform == 'TW' or self.meeting.platform == 'MX') and question.question_type != 'TX'):
					self.start_tw_polling(question)
		elif(message_in == "admin-live-start"):
			if(self.is_user_authenticated()):
				question = self.meeting.current_question()
				async_to_sync(self.start_livestream_poll()) # TODO
		elif(message_in == "admin-live-stop"):
			if(self.is_user_authenticated()):
				question = self.meeting.current_question()
				async_to_sync(self.stop_livestream_poll()) # TODO
		elif(message_in == "admin-question-results"):
			if(self.is_user_authenticated()):
				question = self.meeting.current_question()
				self.send_group_results(question)
				if((self.meeting.platform == 'YT' or self.meeting.platform == 'MX') and question.question_type != 'TX'):
					self.stop_yt_polling(question)
				if((self.meeting.platform == 'TW' or self.meeting.platform == 'MX') and question.question_type != 'TX'):
					self.stop_tw_polling(question)
		elif(message_in == "admin-question-next"):
			if(self.is_user_authenticated()):
				self.next_question()
				self.notify_next_question()
		elif(message_in == "chat-subscribe"):
			self.subscribe_to_chat()
		else:
			message_out = {'message':'error'}
			self.send(text_data=json.dumps(message_out))




###### Functional logic #####


	# for basic access control
	def is_user_authenticated(self):
		if(self.scope['user'].is_anonymous):
			return False
		elif(self.scope['user'].is_authenticated):
			return True
		else:
			return False

	# sync method
	def next_question(self):
		# marks question as done
		question = self.meeting.current_question()
		question.is_done = True
		question.save() 


	def notify_next_question(self):
		# sends new question id
		question = self.meeting.current_question()
		if(not question):
			raise ValueError('there is no question')
		else:
			message_out = {
				'message' : "next-question",
				'question':{
					'id': question.id,
				},
			}
		async_to_sync(self.channel_layer.group_send)(
			self.meeting_group_name,
			{
				'type': 'meeting_message',
				'message': message_out,
			}
		)
		if(question.id == None):
			self.notify_end()


	def notify_end(self):
		message_out = {
			'message' : "question-go",
			'question':{
				'title': 'Thanks for attending',
				'desc': "This meeting is now over, thank you for using <b>LibreKast</b>."
					+"<br><br><p class='text-xs'>Feel free to check the author's <a href='https://www.pour-info.tech/'>youtube channel</a>"
					+"and consider subscribing, it's as free as this software.</p>",
				'type': 'TX',
				'id': 0,
				'choices':[]
			},
		}
		async_to_sync(self.channel_layer.group_send)(
			self.meeting_group_name,
			{
				'type': 'meeting_message',
				'message': message_out,
			}
		)

	# sync method
	# expects a json object like {'message': 'vote', 'question': '4', 'choice': 15}
	def receive_vote(self,text_data_json,attendee):
		try:
			question = self.meeting.current_question()
			choice = question.choice_set.get(pk=text_data_json['choice'])
			# I volontarily set the question based on user input to prevent async to sync
			# question = Question.objects.get(pk=text_data_json['question'])
			if(len(get_previous_user_answers(attendee,question))==0):
				vote=Vote(user=attendee,choice=choice)
				vote.save()

				if(choice.isTrue and question.question_type =='QZ'):
					if(question.first_correct_answer and self.meeting.reward_fastest):
						question.first_correct_answer = False
						question.save()
						attendee.score +=2
					attendee.score +=1
					attendee.save()
					# ADD +1 pt for subscribers in the case of a Youtube Live
					# if(self.meeting.platform == 'YT'):
					# 	if(attendee.isSubscriber)
					# 	attendee.score +=1
					# 	attendee.save()

				
				if(question.question_type =='QZ'):
					message_out = {'message':'voted'}
					self.send(text_data=json.dumps(message_out)) #
				elif(question.question_type =='PL'):
					self.send_results(question)
					self.notify_update_PL(question,choice)
				async_to_sync(self.notify_admin_vote(choice,question))
			else:
				message_out = {'message':'error : already voted'}
				self.send(text_data=json.dumps(message_out)) #
		except:
			message_out = {'message':'error : something happened'}
			self.send(text_data=json.dumps(message_out)) #

	# sync method
	def add_word(self,word,attendee):
		question = self.meeting.current_question()
		# TODO : bleach
		word_cleaned = word
		try:
			existing_word = question.choice_set.get(choice_text=word_cleaned)
			vote=Vote(user=attendee,choice=existing_word)
			vote.save()
		except:
			added_word = Choice(question=question, choice_text=word_cleaned)
			added_word.save()
			vote=Vote(user=attendee,choice=added_word) # the vote is a model to keep traces of the votes
			vote.save()


	def send_current_question(self,question):
		message_out = {
			'message' : "current-question",
			'question':{
				'id': question.id,
			},
		}
		self.send(text_data=json.dumps(message_out))

	# send question to group
	def send_group_question(self,question):
		message_out = {
			'message' : "question-go",
			'question':{
				'title': question.title,
				'desc': question.desc_rendered,
				'type': question.question_type,
				'id': question.id,
				'choices':[]
			},
		}
		if(question.question_type == 'WC'):
			for choice in question.choice_set.all():
				choice_obj = {
					'x':choice.choice_text,
					'value':choice.votes(),
				}
				message_out['question']['choices'].append(choice_obj)
		else:
			for choice in question.choice_set.all():
				choice_obj = {
					'id':choice.id,
					'text':choice.choice_text,
				}
				message_out['question']['choices'].append(choice_obj)
		async_to_sync(self.channel_layer.group_send)(
			self.meeting_group_name,
			{
				'type': 'meeting_message',
				'message':message_out,
			}
		)

	def send_group_results(self,question):
		message_out = {
			'message' : "results",
			'results': [],
			'question_type':question.question_type,
			'total':question.participants(), #shamelessly reuse this function
		}
		for choice in question.choice_set.all():
			choice_obj = {
				'id':choice.id,
				'text':choice.choice_text,
				'votes':choice.votes(),
				'isTrue':choice.isTrue,
			}
			message_out['results'].append(choice_obj)
		async_to_sync(self.channel_layer.group_send)(
			self.meeting_group_name,
			{
				'type': 'meeting_message',
				'message': message_out,
			}
		)


	def send_group_scoreboard(self):
		message_out = {
			'message' : "update-scoreboard",
			'scores': [],
		}
		for user in self.meeting.attendee_set.all().order_by('-score'):
			score_obj = {
				'id':user.id,
				'name':user.name,
				'score':user.score,
			}
			message_out['scores'].append(score_obj)
		async_to_sync(self.channel_layer.group_send)(
			self.meeting_group_name,
			{
				'type': 'meeting_message',
				'message': message_out,
			}
		)
		# self.send(text_data=json.dumps(message_out))

	def send_results(self,question):
		message_out = {
			'message' : "results",
			'results': [],
			'question_type':question.question_type,
			'total':question.participants(), #shamelessly reuse this function
		}
		for choice in question.choice_set.all():
			choice_obj = {
				'id':choice.id,
				'text':choice.choice_text,
				'votes':choice.votes(),
				'isTrue':choice.isTrue,
			}
			message_out['results'].append(choice_obj)
		self.send(text_data=json.dumps(message_out))


	def notify_add_word(self,word):
		async_to_sync(self.channel_layer.group_send)(
			self.meeting_group_name,
			{
				'type': 'meeting_message',
				'message': {
					'message':'notify-update-cloud',
					'vote': word,
				}
			}
		)


	# sync method
	def send_scoreboard(self):
		message_out = {
			'message' : "update-scoreboard",
			'scores': [],
		}
		for user in self.meeting.attendee_set.all().order_by('-score'):
			score_obj = {
				'id':user.id,
				'name':user.name,
				'score':user.score,
				'is_sub':user.is_subscriber,
				'yt':user.is_youtube,
				'tw':user.is_twitch,
			}
			message_out['scores'].append(score_obj)
		self.send(text_data=json.dumps(message_out))


	# TODO remove question 
	def notify_update_PL(self,question,choice):
		async_to_sync(self.channel_layer.group_send)(
			self.meeting_group_name,
			{
				'type': 'meeting_message',
				'message': {
					'message':'notify-update-poll',
					'vote': choice.id,
					# 'text': choice.choice_text,
				}
			}
		)

	def notify_admin_vote(self,choice,question):
		res = []
		for choice in question.choice_set.all():
			choice_obj = {
				'id':choice.id,
				'text':choice.choice_text,
				'votes':choice.votes(),
				'isTrue':choice.isTrue,
			}
			res.append(choice_obj)
		async_to_sync(self.channel_layer.group_send)(
			self.meeting_group_name+'_admin',
			{
				'type': 'admin_message', # is it though ?
				'message': {
					'message':'notify-update-poll',
					'vote':choice.id,
					'results': res
				}
			}
		)

	def notify_chat(self,message):
		async_to_sync(self.channel_layer.group_send)(
			self.meeting_group_name+'_chat',
			{
				'type': 'admin_message', # is it though ?
				'message': {
					'message':'notify-chat',
					'chat':message,
				}
			}
		)

	def subscribe_to_chat(self):
		if(self.meeting.platform != 'IRL'):
			if(settings.DEBUG):
				print('debug : socket subscribing to live chat')
			async_to_sync(self.channel_layer.group_add)(
				self.meeting_group_name+'_chat',
				self.channel_name
			)


### LIVE STREAMS
# the polling process is defined in another class for clarity of threading
# but it calls the methods from this class receive_vote() and add_word() for each message


# Youtube Live compatibility
	def init_yt_polling(self):
		if(not self.meeting.stream_id):
			self.send(text_data=json.dumps({'message':'admin-error','text' : 'there is no video ID specified in the Meeting settings'}))
			raise KeyError('There should be a Youtube live/video ID defined')
		self.ytHandler = None
		self.ytHandler = YoutubeHandler(self.meeting.youtube_api,self.meeting.stream_id) 
		self.ytHandler.meetingConsumer = self
		self.ytHandler.start()

	def start_yt_polling(self,question):
		if(not hasattr(self,'ytHandler')):
			raise KeyError('There should be a YoutubeHandler object')
		self.ytHandler._polling = True

	def stop_yt_polling(self,question):
		if(not hasattr(self,'ytHandler')):
			raise KeyError('There should be a YoutubeHandler object')
		self.ytHandler._polling = False

	def terminate_yt_polling(self):
		if(hasattr(self,'ytHandler')):
			self.ytHandler.terminate()
			self.ytHandler = None



# Twitch Streams compatibility
	def init_tw_polling(self):
		if(not self.meeting.channel_id):
			self.send(text_data=json.dumps({'message':'admin-error','text' : 'there is no channel ID specified in the Meeting settings'}))
			raise KeyError('There should be a Twitch channel ID defined')
		if(not self.meeting.twitch_api):
			self.send(text_data=json.dumps({'message':'admin-error','text' : 'there is no Twitch API specified in the Meeting settings'}))
			raise KeyError('There should be a Twitch API defined')
		self.twHandler = TwitchHandler(self.meeting.channel_id,self.meeting.twitch_api)
		self.twHandler.meetingConsumer = self

	def start_tw_polling(self,question):
		if(not hasattr(self,'twHandler')):
			raise KeyError('There should be a TwitchHandler object')
		self.twHandler.run()

	def stop_tw_polling(self,question):
		if(not hasattr(self,'twHandler')):
			raise KeyError('There should be a TwitchHandler object')
		self.twHandler.stop()

	def terminate_tw_polling(self):
		if(hasattr(self,'twHandler')):
			self.twHandler.terminate()
			self.twHandler = None

