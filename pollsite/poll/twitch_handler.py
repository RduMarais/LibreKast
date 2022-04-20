import threading
import twitch
from django.conf import settings
from .models import Choice, Question, Meeting,Attendee,Vote


PRINT_MESSAGES = False

class TwitchHandler(threading.Thread):
	meetingConsumer = None

	def __init__(self,channel,twitch_api):
		self.helix = twitch.Helix(twitch_api.client_id, twitch_api.client_secret)
		self.channel = '#'+channel
		self.chat = twitch.Chat(channel=self.channel,nickname=settings.TWITCH_NICKNAME,oauth='oauth:'+twitch_api.oauth,helix=self.helix)
		if(settings.DEBUG):
			print('debug : twitch object initiated')
		self.chat.subscribe(self.show_message)
		self.chat.subscribe(self.bot_listen)
		if(settings.DEBUG):
			print('debug : twitch chat listening')


	def print_message(self,chatlog):
		self.meetingConsumer.notify_chat(chatlog)

	def show_message(self,message: twitch.chat.Message) -> None:
		 # print(f'author {message.sender}, text: {message.text}')
		 self.print_message({'author':message.sender,'text':message.text,'source':'t'})

	def handle_question(self,message: twitch.chat.Message) -> None:
		if message.text.startswith(settings.INTERACTION_CHAR):
			# TODO : is subscriber
			attendee = self.meetingConsumer.check_attendee(message.sender,is_subscriber=False,is_twitch=True)
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


	def bot_listen(self,message: twitch.chat.Message) -> None:
		if message.text.startswith('!'):
			command = self.meetingConsumer.meeting.messagebot_set.filter(command=message.text.split()[0][1:])
			if(command):
				print('debug : command activated : '+command[0].message)
				self.chat.send(command[0].message)



	def terminate(self):
		self.chat.irc.active = False
		self.chat.irc.socket.close()	
		self.chat.dispose()

	def run(self):
		if(settings.DEBUG):
			print('debug : twitch poll start')
		self.chat.subscribe(self.handle_question)
		if(settings.DEBUG):
			print('debug : twitch poll running')

	def stop(self):
		self.terminate()
		self.chat = twitch.Chat(channel=self.channel,nickname=settings.TWITCH_NICKNAME,oauth='oauth:'+self.meetingConsumer.meeting.twitch_api.oauth,helix=self.helix)
		self.chat.subscribe(self.show_message)
		self.chat.subscribe(self.bot_listen)
		if(settings.DEBUG):
			print('debug : twitch chat polling stopped, messages listening restarted')
