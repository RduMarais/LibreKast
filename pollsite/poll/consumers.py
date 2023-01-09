# chat/consumers.py
import json
import threading
import datetime
import atexit


from django.utils import timezone
from django.utils.translation import gettext as _
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.generic.websocket import WebsocketConsumer
from bleach import clean

from google.auth.exceptions import RefreshError

from .models import Choice, Question, Meeting,Attendee,Vote
from .views import get_previous_user_answers
from .youtube_handler import YoutubeHandler,YoutubeOAuthError,YoutubeChatError
from .twitch_handler import TwitchHandler, TwitchChatError
from .utils import validate_flag_attempt


class MEETING_STATUS:
	WAITING ='W'
	ONGOING ='O'
	AFTER ='A'
	BEFORE ='B'
	SCOREBOARD ='S'
	RESULTS ='R'
	UNDEFINED ='U'


##############################################
#######       CHAT RO CONSUMER       #########
##############################################

class ChatConsumer(WebsocketConsumer):

	def connect(self):
		meeting_id = self.scope['url_route']['kwargs']['meeting_id']  
		self.meeting = Meeting.objects.get(pk=meeting_id)
		self.meeting_group_name = 'meeting_'+str(self.meeting.id)+'_chat'

		# # Join group
		# async_to_sync(self.channel_layer.group_add)(
		# 	self.meeting_group_name,
		# 	self.channel_name
		# )

		# join chat group
		async_to_sync(self.channel_layer.group_add)(
			self.meeting_group_name,
			self.channel_name
		)

		if(settings.DEBUG): print(f'debug : read-only chat instance listening')
		self.accept()
		
	# leave group
	def disconnect(self, close_code):
		async_to_sync(self.channel_layer.group_discard)(
			self.meeting_group_name,
			self.channel_name
		)
		# if(self.meeting.platform == 'YT' or self.meeting.platform == 'MX'):
			# self.terminate_yt_polling()
		# if(self.meeting.platform == 'TW' or self.meeting.platform == 'MX'):
			# self.terminate_tw_polling()

	# handle message received from the client
	def receive(self, text_data):
		text_data_json = json.loads(text_data)
		message_in = text_data_json['message']  # this is the format that should be modified
		
		if(settings.DEBUG): print('RECV (RO) : '+message_in)

		if(message_in == "chat-subscribe"):
			if(settings.DEBUG): print('debug : socket subscribing to live chat')
			self.subscribe_to_chat()
		else:
			message_out = {'message':'error','error':_('Something went wrong. Please report this to an admin.')}
			self.send(text_data=json.dumps(message_out))

	def subscribe_to_chat(self):
		if(self.meeting.platform != 'IRL'):
			if(settings.DEBUG): print('debug : socket subscribing to live chat')
			async_to_sync(self.channel_layer.group_add)(
				self.meeting_group_name+'_chat',
				self.channel_name
			)

	# Receive message from meeting group
	def admin_message(self,event):
		print('debug (RO) : chat message')
		message = event['message']
		self.send(text_data=json.dumps(message))


##############################################
##########       MAIN CLASS       ############
##############################################

# there are 3 group channels joined if needed : 
# * meeting_group_name = evryone on the meeting (used for word cloud, results, and the questions content)
# * _admin : admins only (used for live results)
# * _chat : anyone that wants to get the live chat (used for live chat, obviously)
class MeetingConsumer(WebsocketConsumer):
	isAdmin = False


##############################################
#########       INITIALIZATION       #########
##############################################

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
			# check if 

		self.accept()

		# setup user session : admin dashboard is build over the mechanism (the websocket 'api') for regular users
		# therefore, the admin should have a session
		# thus we have to handle a few edge case if the admin has not registered as a participant
		if('attendee_id' in self.scope['session']):
			attendee_id = self.scope['session']['attendee_id']
			try:
				self.attendee = Attendee.objects.get(pk=attendee_id)
			except Attendee.DoesNotExist:
				self.send(text_data=json.dumps({'message':'error','error':_('Warning : no login (no attendee found)')}))
		elif(self.is_user_authenticated()):
			try:
				new_attendee = Attendee.objects.get(name=self.scope['user'].username)
				self.scope['session']['attendee_id'] = new_attendee.id
				self.send(text_data=json.dumps({'message':'error','error':_('Warning : user is staff -> previous login with staff username used')}))
				if(settings.DEBUG): print('debug : use staff user as dashboard user.')
				self.attendee = new_attendee
			except Attendee.DoesNotExist:
				# if the user checks the meeting afterwards, a new user will be created
				self.send(text_data=json.dumps({'message':'error','error':_('Warning : no login (user is staff) -> user created')}))
				new_attendee = Attendee(name=self.scope['user'].username,meeting=self.meeting,score=0)
				new_attendee.save()
				self.scope['session']['attendee_id'] = new_attendee.id
				self.attendee = new_attendee
		else:
			# there is a conflict bc read-only clients such as chat embeddings do not have a session
			self.send(text_data=json.dumps({'message':'error','error':_('no login (no id in session)')}))

		
		# if(settings.DEBUG):
		# 	print(f'debug : is user is_authenticated ? {self.is_user_authenticated()}')
		# 	print(f'debug : is meeting running ? {self.meeting._is_running}')
		# 	print(f'debug : is user the admin ? {self.isAdmin}') ## c'est ça qui plante
		# 	print(f'debug : what is meeting status ? {self.get_current_meeting_status()}')

		# ADMIN settings : this should be executed ONLY ONCE PER MEETING
		# these status indicates that no one is handling the meeting
		if(self.is_user_authenticated() and not self.meeting._is_running): 
			if(settings.DEBUG): print('debug : admin init : should be executed only once')
			self.meeting._is_running = True
			self.meeting.save()
			self.set_meeting_status(MEETING_STATUS.WAITING)
			self.isAdmin = True # to keep track of who is the first to start the meeting
		
			if(self.meeting.platform == 'YT' or self.meeting.platform == 'MX'):
				if(settings.DEBUG): print('debug : admin init : check for YT handler')
				if(not hasattr(self,'ytHandler')):
					self.time_iterator = 0
					self.periodic_bot_iterator = 0
					self.init_yt_polling()
					if(settings.DEBUG): print('debug : admin init : starting YT handler')
				else:
					if(settings.DEBUG): print('debug : meeting has already a YT handler')
			if(self.meeting.platform == 'TW' or self.meeting.platform == 'MX'):
				if(settings.DEBUG): print('debug : admin init : check for TW handler')
				if(not hasattr(self,'twHandler')):
					self.init_tw_polling()
					if(settings.DEBUG): print('debug : admin init : starting TW handler')
				else:
					if(settings.DEBUG): print('debug : meeting has already a TW handler')


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
		if(self.isAdmin):
			self.set_meeting_status(MEETING_STATUS.AFTER)
			self.meeting._is_running = False
			self.meeting.save()



	# Receive message from meeting group
	def meeting_message(self, event):
		message = event['message']
		print('debug : meeting message')
		# Send message to WebSocket
		self.send(text_data=json.dumps(message))

	def admin_message(self,event):
		print('debug : admin message')
		message = event['message']
		self.send(text_data=json.dumps(message))




##############################################
#########       RECEIVE method       #########
##############################################

	# handle message received from the client
	def receive(self, text_data):
		text_data_json = json.loads(text_data)
		message_in = text_data_json['message']  # this is the format that should be modified
		
		if(settings.DEBUG): print('RECV : '+message_in)

		####################################
		#### THE MAIN APP LOGIC is here ####
		####################################
		# for debug purposes : starts the current question
		if(message_in == "debug-question-start"):
			if(settings.DEBUG):
				question = self.meeting.current_question()
				self.send_group_question(question) # _status = O
		# user joins the meeting : send the current question if a question is ongoing
		elif(message_in == "question-start"):
			self.send_current_question_on_join()
		# participant sends a vote
		elif(message_in == "vote"):
			if(settings.DEBUG): print('debug : json data : '+str(text_data_json))
			async_to_sync(self.receive_vote(text_data_json,self.attendee))
		# participant is asking for its score
		elif(message_in == "get-score"):
			self.send(text_data=json.dumps({
				'message':'update-score',
				'score':self.attendee.score,
				}))
		# participant has added a word
		elif(message_in == "word-cloud-add"):
			word = clean(text_data_json['word'])
			async_to_sync(self.add_word(word,self.attendee))
			async_to_sync(self.notify_add_word(word))
		# admin is asking for scoreboard update
		elif(message_in == "get-scoreboard"):
			self.send_scoreboard()
		# admin is sending everyone the scoreboard
		elif(message_in == "admin-send-scoreboard"):
			if(self.is_user_authenticated()):
				self.send_group_scoreboard() # _status = S
		# admin is asking for current question id
		elif(message_in == "admin-get-current-question"):
				question = self.meeting.current_question()
				self.send_current_question(question)
				self.set_meeting_status(MEETING_STATUS.WAITING) # _status = W
		# admin is sending everyone the current question
		elif(message_in == "admin-question-start"):
			if(self.is_user_authenticated()):
				question = self.meeting.current_question()
				self.send_group_question(question) # _status = O
				if((self.meeting.platform == 'YT' or self.meeting.platform == 'MX') and question.question_type != 'TX'):
					self.start_yt_polling(question)
				if((self.meeting.platform == 'TW' or self.meeting.platform == 'MX') and question.question_type != 'TX'):
					self.start_tw_polling(question)
		elif(message_in == "admin-question-results"):
			if(self.is_user_authenticated()):
				question = self.meeting.current_question()
				self.send_group_results(question) # _status = R
				if((self.meeting.platform == 'YT' or self.meeting.platform == 'MX') and question.question_type != 'TX'):
					self.stop_yt_polling(question)
				if((self.meeting.platform == 'TW' or self.meeting.platform == 'MX') and question.question_type != 'TX'):
					self.stop_tw_polling(question)
		# admin is resetting everyone's question screen for next question
		elif(message_in == "admin-question-next"):
			if(self.is_user_authenticated()):
				self.next_question()
				self.notify_next_question() # _status = W
		# admin asks for chat log
		elif(message_in == "chat-subscribe"):
			self.subscribe_to_chat()
		# participant sends flag submission
		elif(message_in == "submit-flag"):
			if(settings.DEBUG): print('starting flag submission')
			self.submit_flag(text_data_json,self.attendee)
		elif(message_in == "new-oauth-token"):
			self.setup_youtube_oauth_token(text_data_json['token'])
		else:
			message_out = {'message':'error','error':_('Something went wrong. Please report this to an admin.')}
			self.send(text_data=json.dumps(message_out))




##############################################
#########      Functional logic      #########
##############################################


	# wrapper for basic access control with django built-in functions
	def is_user_authenticated(self):
		if(self.scope['user'].is_anonymous):
			return False
		elif(self.scope['user'].is_authenticated):
			return True
		else:
			return False

	# atomic function to set meeting status
	def set_meeting_status(self,status):
		self.meeting._question_status = status
		if(settings.DEBUG): print(f'debug : meeting status set to {status}')
		self.meeting.save()

	# this function has to perform a "database read" bc the meetging object 
	#   is queried on join, is user-specific and does not update with the admin's
	#   meeting object
	def get_current_meeting_status(self):
		meet = Meeting.objects.get(pk=self.meeting.id)
		return meet._question_status

	# sync method
	def next_question(self):
		# marks question as done
		question = self.meeting.current_question()
		question.is_done = True
		question.save()


	def notify_next_question(self):
		# sends new question id
		self.set_meeting_status(MEETING_STATUS.WAITING)
		question = self.meeting.current_question()
		if(not question):
			# this should not happen as the previous function returns a new 'End' Activity
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
			# the question has no 'id' because it is not saved in the database
			self.notify_end()


	def prepare_question(self,question):
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
		return message_out

	def prepare_results(self,question):
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
		return message_out

	def notify_end(self):
		self.set_meeting_status(MEETING_STATUS.AFTER)
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

	def send_current_question_on_join(self):
		stat = self.get_current_meeting_status()
		if(stat =='O'): #Activity ongoing
			question = self.meeting.current_question()
			message_out = self.prepare_question(question)
			self.send(text_data=json.dumps(message_out))
		elif(stat =='A'): #Meeting finished
			self.notify_end()
		elif(stat =='S'): #Scoreboard display
			self.send_scoreboard()
		elif(stat =='R'): #Activity results display
			question = self.meeting.current_question()
			show_question_message_out = self.prepare_question(question)
			self.send(text_data=json.dumps(show_question_message_out))
			show_results_message_out = self.prepare_results(question)
			self.send(text_data=json.dumps(show_results_message_out))
		else: #Waiting for next activity / Meeting To be started / undefined
			self.send(text_data=json.dumps({'message':'question-ready'}))


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
		self.set_meeting_status(MEETING_STATUS.ONGOING)
		
		message_out = self.prepare_question(question)
		
		async_to_sync(self.channel_layer.group_send)(
			self.meeting_group_name,
			{
				'type': 'meeting_message',
				'message':message_out,
			}
		)

	def send_group_results(self,question):
		self.set_meeting_status(MEETING_STATUS.RESULTS)

		message_out = self.prepare_results(question)

		async_to_sync(self.channel_layer.group_send)(
			self.meeting_group_name,
			{
				'type': 'meeting_message',
				'message': message_out,
			}
		)


	def send_group_scoreboard(self):
		self.set_meeting_status(MEETING_STATUS.SCOREBOARD)
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
			if(settings.DEBUG): print('debug : socket subscribing to live chat')
			async_to_sync(self.channel_layer.group_add)(
				self.meeting_group_name+'_chat',
				self.channel_name
			)

	def send_bot_alert(self,revolutionbot):
		print('debug : sent bot alert')
		if(self.meeting.platform != 'IRL'):
			if(settings.DEBUG): print('debug : sending revolution alert')
			# message_out = {
			# }
			# notify the group admin so the alerts in OBS can have it
			async_to_sync(self.channel_layer.group_send)(
				self.meeting_group_name+'_chat',
				{
					'type': 'admin_message', # is it though ?
					'message': {
						'message':'revolution-alert',
						'alert':{'url':revolutionbot.alert.url,'text':revolutionbot.message},
					}
				}
			)

	def submit_flag(self,text_data_json,attendee):
		flag_attempt_text = text_data_json['flag']
		if(settings.DEBUG): print(f'user {attendee.name} submitted flag : {flag_attempt_text}')
		(flag_attempt,error) = validate_flag_attempt(self.meeting,attendee,flag_attempt_text)
		message_out = {}
		is_correct = False
		if(flag_attempt.correct_flag):
			is_correct = True
			message_out = {
				'message' : "flag-success",
				'result':{
					'name':flag_attempt.correct_flag.name,
					'points':flag_attempt.correct_flag.points,
					'desc-rendered':flag_attempt.correct_flag.desc_rendered,
					'desc-img-url':flag_attempt.correct_flag.desc_img.url if flag_attempt.correct_flag.desc_img else None,
					'first-blood':flag_attempt.is_first_blood,
					'current-score': attendee.score,
				},
			}
		else:
			message_out = {
				'message' : "flag-error",
				'results':{
					'error':error,
					'flag-attempt-code':flag_attempt.code,
				},
			}
		self.send(text_data=json.dumps(message_out))

		# notify the group admin
		async_to_sync(self.channel_layer.group_send)(
			self.meeting_group_name+'_admin',
			{
				'type': 'admin_message', # is it though ?
				'message': {
					'message':'notify-flag',
					'flag-attempt':{
						'code':flag_attempt_text,
						'user':attendee.name,
						'correct':is_correct,
					},
				}
			}
		)




##############################################
#########     Live Streams Bots      #########
##############################################

# the polling process is defined in another class for clarity of threading
# but it calls the methods from this class receive_vote() and add_word() for each message

# Threshold/Revolution Bots logic
	def listen_revolution_bot(self,command, sender):
		revolution = self.meeting.revolutionbot_set.filter(command=command).filter(is_active=True)
		if(revolution):
			print('debug : revolution bot +1 '+revolution[0].command)
			print('debug : buffer :'+str(revolution[0].buffer))
			now = timezone.now()
			spam = False
			for t in revolution[0].buffer['triggers']:
				# remove older messages
				if((now - datetime.datetime.fromisoformat(t['time'])).seconds >= revolution[0].threshold_delay):
					revolution[0].buffer['triggers'].remove(t)
					if(settings.DEBUG): print('debug : removed old msg from buffer')
				elif(t['name']==sender):
					spam=True 		# the reason this is not a break is bc I want to still browse the array to remove the older triggers
					if(settings.DEBUG): print('debug : spam identified')
			if(not spam):
				revolution[0].buffer['triggers'].append({'name':sender,'time':now.isoformat()})
				if(len(revolution[0].buffer['triggers']) > revolution[0].threshold_number):
					if(settings.DEBUG): print('debug : is it a revolution ?')
					# prevent a revolution to be re-triggered instantly previous revolution
					if((revolution[0].buffer['last_revolution']=='') or ((now - datetime.datetime.fromisoformat(revolution[0].buffer['last_revolution'])).seconds >= revolution[0].threshold_delay)):

						# ITS HAPPENING HERE
						if(settings.DEBUG): print('debug : revolution started ! '+revolution[0].message)
						# send on youtube and twitch and show them in the librekast chat 
						if(hasattr(self,'ytHandler') and (self.meeting.platform == 'YT' or self.meeting.platform == 'MX')):
							self.ytHandler.send_message(settings.BOT_MSG_PREFIX+revolution[0].message)
						if(hasattr(self,'twHandler') and (self.meeting.platform == 'TW' or self.meeting.platform == 'MX')):
							self.twHandler.send_message(settings.BOT_MSG_PREFIX+revolution[0].message)
							if(self.meeting.platform == 'TW'):
								# print the revolution message in librekast chat if youtube handler has not already done it
								self.twHandler.print_message({'sender':settings.TWITCH_NICKNAME,'text':settings.BOT_MSG_PREFIX+revolution[0].message,'source':'t'})
						# reset revolution state
						revolution[0].buffer['last_revolution'] = now.isoformat()
						revolution[0].buffer['triggers'] = []
						print('debug : reset buffer')
						if(revolution[0].alert):
							self.send_bot_alert(revolution[0])
				if(settings.DEBUG): print('debug : added last to buffer')
			revolution[0].save()

	def periodic_bot(self):
		if(settings.DEBUG):print(f"debug : periodic bot ping {self.time_iterator}")
		self.time_iterator = (self.time_iterator + 1) % 3600
		if(self.time_iterator % settings.PERIODIC_BOT_DELAY == 0 and self.meeting.periodicbot_set.filter(is_active=True)):
			if(settings.DEBUG):print("debug : periodic bot iterator : "+self.periodicbot_iterator)
			if(settings.DEBUG):print("debug : periodic bot pong")
			# On Youtube send bot message number *periodic_bot_iterator*
			self.ytHandler.send_message(settings.BOT_MSG_PREFIX+self.meeting.periodicbot_set.filter(is_active=True)[self.periodic_bot_iterator].message)
			if(self.meeting.platform == 'MX' and hasattr(self,'twHandler')):
				# On Twitch send bot message number *periodic_bot_iterator*
				self.twHandler.send_message(settings.BOT_MSG_PREFIX+self.meeting.periodicbot_set.filter(is_active=True)[self.periodic_bot_iterator].message)
				# no need to print the message in librekast chat as youtube bot already prints it 
			# iterate over periodic_bot_iterator
			if(settings.DEBUG):print("debug : periodic bot : "+self.meeting.periodicbot_set.filter(is_active=True)[self.periodic_bot_iterator].message)
			self.periodic_bot_iterator = (self.periodic_bot_iterator + 1) % len(self.meeting.periodicbot_set.filter(is_active=True))
			if(settings.DEBUG):print("debug : periodic bot iterator : "+self.periodicbot_iterator)




##############################################
#########       Youtube Streams      #########
##############################################

	def init_yt_polling(self):
		if(not self.meeting.stream_id):
			self.send(text_data=json.dumps({'message':'admin-error','text' : 'there is no video ID specified in the Meeting settings'}))
			raise KeyError('There should be a Youtube live/video ID defined')
		self.ytHandler = None
		try:
			self.ytHandler = YoutubeHandler(self.meeting.youtube_api,self.meeting.stream_id) 
			self.ytHandler.meetingConsumer = self
			self.ytHandler.start()
		except RefreshError:
			self.send(text_data=json.dumps({'message':'admin-error','text':'You need another YT API credential'}))
			self.ytHandler = 'RefreshError'
		if(hasattr(self.ytHandler,'oauth_error')):
			if(settings.DEBUG):print('debug : '+str(self.ytHandler.oauth_error))
			self.send(text_data=json.dumps({'message':'oauth-error','text':str(self.ytHandler.oauth_error) + self.ytHandler.oauth_error.url}))


	def setup_youtube_oauth_token(self,token):
		if(settings.DEBUG): print('debug : receive token '+token)
		if(not self.meeting.stream_id):
			self.send(text_data=json.dumps({'message':'admin-error','text' : 'there is no video ID specified in the Meeting settings'}))
			raise KeyError('There should be a Youtube live/video ID defined')
		if(not hasattr(self,'ytHandler')):
			raise YoutubeChatError('somethiong went wrong')
		self.ytHandler.fetch_oauth_token(self.meeting.youtube_api,self.meeting.stream_id,token)
		self.ytHandler.meetingConsumer = self


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



##############################################
#########       Twitch Streams       #########
##############################################

	def init_tw_polling(self):
		if(not self.meeting.channel_id):
			self.send(text_data=json.dumps({'message':'admin-error','text' : 'there is no channel ID specified in the Meeting settings'}))
			raise KeyError('There should be a Twitch channel ID defined')
		if(not self.meeting.twitch_api):
			self.send(text_data=json.dumps({'message':'admin-error','text' : 'there is no Twitch API specified in the Meeting settings'}))
			raise KeyError('There should be a Twitch API defined')
		try:
			self.twHandler = TwitchHandler(self.meeting.channel_id,self.meeting.twitch_api,self)
		except TwitchChatError as e:
			self.send(text_data=json.dumps({'message':'admin-error','text':_('Error connecting to Twitch API : ')+e.message}))

	def start_tw_polling(self,question):
		if(not hasattr(self,'twHandler')):
			self.send(text_data=json.dumps({'message':'admin-error','text':_('Error connecting to Twitch API : ')+_('Twitch chat is not initiated')}))
		else:
			if(settings.DEBUG):print('debug : start polling on twitch')
			self.twHandler.run()

	def stop_tw_polling(self,question):
		if(not hasattr(self,'twHandler')):
			self.send(text_data=json.dumps({'message':'error','error':_('Error connecting to Twitch API : ')+_('Twitch chat is not initiated')}))
		else:
			self.twHandler.stop()

	def terminate_tw_polling(self):
		if(hasattr(self,'twHandler')):
			self.twHandler.terminate()
			self.twHandler = None

