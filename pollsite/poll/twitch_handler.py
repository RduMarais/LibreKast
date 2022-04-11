import threading
import twitch
from django.conf import settings
from .models import Choice, Question, Meeting,Attendee,Vote


INTERACTION_CHAR = '#' 
PRINT_MESSAGES = False

class TwitchHandler(threading.Thread):
	meetingConsumer = None

	def __init__(self,channel):
		self.helix = twitch.Helix(settings.TWITCH_CLIENT_ID, settings.TWITCH_CLIENT_SECRET)
		self.channel = '#'+channel
		self.chat = twitch.Chat(channel=self.channel,nickname=settings.TWITCH_NICKNAME,oauth='oauth:'+settings.TWITCH_OAUTH_TOKEN,helix=self.helix)
		print('debug : twitch object initiated')
		self.chat.subscribe(self.show_message)
		print('debug : twitch chat listening')


	def print_message(self,chatlog):
		self.meetingConsumer.notify_chat(chatlog)

	def show_message(self,message: twitch.chat.Message) -> None:
		 print(f'author {message.sender}, text: {message.text}')
		 self.print_message({'author':message.sender,'text':message.text,'source':'t'})

	# similar to youtube_handler.check_attendee
	# TODO : is subscriber
	def check_attendee(self,name):
		attendee = None
		attendee_queryset = self.meetingConsumer.meeting.attendee_set.all().filter(name=name)
		if(attendee_queryset): # is this secure ?
			attendee = attendee_queryset[0]
		else:
			# TODO : is subscriber
			attendee = Attendee(name=name,meeting=self.meetingConsumer.meeting,score=0,is_subscriber=False,is_twitch=True) # is this secure ? 
			attendee.save()
		return attendee

	def handle_question(self,message: twitch.chat.Message) -> None:
		if message.text.startswith(INTERACTION_CHAR):
			if(settings.DEBUG):
				print('debug: twitch intraction : '+message.text)
			attendee = self.check_attendee(message.sender)
			question_type = self.meetingConsumer.meeting.current_question().question_type


			if(question_type == 'WC'):
				self.meetingConsumer.add_word(message.text[1:],attendee) # TODO add attendee
				self.meetingConsumer.notify_add_word(message.text[1:])
				if(settings.DEBUG):
					print('debug : WordCloud added message '+message.text[1:])
			elif(question_type == 'PL' or question_type == 'QZ'):
				if(settings.DEBUG):
					print('debug : Poll/Quizz adding vote '+message.text[1:]+ ' from user '+message.sender)
				choiceset = self.meetingConsumer.meeting.current_question().choice_set.filter(slug=message.text[1:])
				if(choiceset):
					poll_choice = {'choice': choiceset[0].id} # this gets choice ID
					self.meetingConsumer.receive_vote(poll_choice,attendee)
				else : 
					if(settings.DEBUG):
						print('debug : no poll choice for vote '+message.text[1:]+ ' from user '+message.sender)



	def terminate(self):
		self.chat.irc.active = False
		self.chat.irc.socket.close()	
		self.chat.dispose()

	def run(self):
		print('debug : twitch poll start')
		self.chat.subscribe(self.handle_question)
		print('debug : twitch poll running')

	def stop(self):
		self.terminate()
		self.chat = twitch.Chat(channel=self.channel,nickname=settings.TWITCH_NICKNAME,oauth='oauth:'+settings.TWITCH_OAUTH_TOKEN,helix=self.helix)
		self.chat.subscribe(self.show_message)
		print('debug : twitch chat polling stopped, messages listening restarted')
