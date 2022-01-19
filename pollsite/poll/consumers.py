# chat/consumers.py
import json
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.generic.websocket import WebsocketConsumer
from bleach import clean

from .models import Choice, Question, Meeting,Attendee,Vote
from .views import get_previous_user_answers

class QuestionConsumer(WebsocketConsumer):
	def connect(self):
		meeting_id = self.scope['url_route']['kwargs']['meeting_id']  
		self.meeting = Meeting.objects.get(pk=meeting_id)
		self.meeting_group_name = 'meeting_'+str(self.meeting.id)

		attendee_id = self.scope['session']['attendee_id']
		self.attendee = Attendee.objects.get(pk=attendee_id)

		# Join group
		async_to_sync(self.channel_layer.group_add)(
			self.meeting_group_name,
			self.channel_name
		)


		self.accept()

	# leave group
	def disconnect(self, close_code):
		async_to_sync(self.channel_layer.group_discard)(
			self.meeting_group_name,
			self.channel_name
		)

	# Receive message from meeting group
	def meeting_message(self, event):
		message = event['message']
		# Send message to WebSocket
		self.send(text_data=json.dumps(message))


	# receive message from client
	def receive(self, text_data):
		text_data_json = json.loads(text_data)
		message_in = text_data_json['message']  # this is the format that should be modified

		if(message_in == "debug-question-start"):
			question = self.meeting.current_question()
			self.send_group_question(question)
		elif(message_in == "vote"):
			print('WS received vote '+str(text_data_json))
			async_to_sync(self.receive_vote(text_data_json))
		elif(message_in == "get-score"):
			print('WS received get score')
			self.send(text_data=json.dumps({
				'message':'update-score',
				'score':self.attendee.score,
				}))
			print('WS done get score '+str(self.attendee.score))
		elif(message_in == "debug-results"):
			question = self.meeting.current_question()
			self.send_results(question)
		elif(message_in == "word-cloud-add"):
			word = clean(text_data_json['word'])
			async_to_sync(self.add_word(word))
			async_to_sync(self.notify_add_word(word))
		elif(message_in == "get-scoreboard"):
			async_to_sync(self.send_scoreboard())
		elif(message_in == "admin-get-current-question"):
			if(self.is_user_authenticated()):
				question = self.meeting.current_question()
				self.send_current_question(question)
		elif(message_in == "admin-question-start"):
			if(self.is_user_authenticated()):
				question = self.meeting.current_question()
				async_to_sync(self.send_group_question(question))
		elif(message_in == "admin-question-results"):
			if(self.is_user_authenticated()):
				question = self.meeting.current_question()
				async_to_sync(self.send_group_results(question))
		elif(message_in == "admin-question-next"):
			if(self.is_user_authenticated()):
				async_to_sync(self.next_question())
				async_to_sync(self.notify_next_question())
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
	def receive_vote(self,text_data_json):
		try:
			question = self.meeting.current_question()
			choice = question.choice_set.get(pk=text_data_json['choice'])
			# I volontarily set the question based on user input to prevent async to sync
			# question = Question.objects.get(pk=text_data_json['question'])
			if(len(get_previous_user_answers(self.attendee,question))==0):
				vote=Vote(user=self.attendee,choice=choice)
				vote.save()

				if(choice.isTrue and question.question_type =='QZ'):
					if(question.first_correct_answer):
						question.first_correct_answer = False
						question.save()
						self.attendee.score +=1
					self.attendee.score +=1
					self.attendee.save()

				
				if(question.question_type =='QZ'):
					message_out = {'message':'voted'}
					self.send(text_data=json.dumps(message_out)) #
				elif(question.question_type =='PL'):
					self.send_results(question)
					self.notify_update_PL(question,choice)
			else:
				message_out = {'message':'error : already voted'}
				self.send(text_data=json.dumps(message_out)) #
		except:
			message_out = {'message':'error : something happened'}
			self.send(text_data=json.dumps(message_out)) #

	# sync method
	def add_word(self,word):
		question = self.meeting.current_question()
		# TODO : bleach
		word_cleaned = word
		try:
			existing_word = question.choice_set.get(choice_text=word_cleaned)
			vote=Vote(user=self.attendee,choice=existing_word)
			vote.save()
		except:
			added_word = Choice(question=question, choice_text=word_cleaned)
			added_word.save()
			vote=Vote(user=self.attendee,choice=added_word) # the vote is a model to keep traces of the votes
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
				}
			}
		)


