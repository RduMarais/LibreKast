import threading
import twitch
import datetime
import json
import time

from django.utils import timezone
from django.conf import settings
from .models import Choice, Question, Meeting,Attendee,Vote
from django.utils.translation import gettext as _

from .utils import TwitchBotPoller

PRINT_MESSAGES = False
TWITCH_MSG_PERIOD = 5

## Uses : https://github.com/PetterKraabol/Twitch-Python

class TwitchChatError(Exception):
	def __init__(self,message):
		self.message = message
		super().__init__(message)

class TwitchHandler(threading.Thread):
	meetingConsumer = None

	def __init__(self,channel,twitch_api,meetingConsumer):
		self.meetingConsumer = meetingConsumer
		try:
			self.helix = twitch.Helix(twitch_api.client_id, twitch_api.client_secret)
		except KeyError as e:
			raise TwitchChatError(_('Client secret needs to be renewed'))

		self.channel = '#'+channel
		self.chat = twitch.Chat(channel=self.channel,nickname=settings.TWITCH_NICKNAME,oauth='oauth:'+twitch_api.oauth,helix=self.helix)
		time.sleep(3) # wait to see if the connexion has been made
		if(self.chat.irc.exception):
			raise TwitchChatError(_('OAuth token needs to be renewed'))
		if(settings.DEBUG): print('debug : twitch object initiated')
		self.chat.subscribe(self.show_message)
		self.chat.subscribe(self.bot_listen)

		if(settings.DEBUG): print('debug : twitch chat listening')

		if(self.meetingConsumer.meeting.platform == 'TW' or self.meetingConsumer.meeting.platform == 'MX'):
			self.twitchBotPoller = TwitchBotPoller(self,is_daemon=True) # does this work ??
			print('debug : init done, running')
			self.twitchBotPoller.start() # using 'run' does not return, it keeps the focus
			print('debug : is daemon : '+str(self.twitchBotPoller.isDaemon( )))
		print('debug : successfully initiated Twitch handler')


	def send_message(self,message):
		self.chat.send(message)


	def print_message(self,chatlog):
		self.meetingConsumer.notify_chat(chatlog)

	def show_message(self,message: twitch.chat.Message) -> None:
		if(settings.DEBUG):
			print(f'debug : TW MSG : {message.sender} says : {message.text}')
		self.print_message({'author':message.sender,'text':message.text,'source':'t'})

	def handle_question(self,message: twitch.chat.Message) -> None:
		if message.text.startswith(settings.INTERACTION_CHAR):
			# TODO : is subscriber
			attendee = self.meetingConsumer.check_attendee(message.sender,is_subscriber=False,
				is_twitch=True)
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



	# Main function here
	def bot_listen(self,message: twitch.chat.Message) -> None:
		if message.text.startswith(settings.BOT_CHAR): # by default this is '!'
			# is this a command bot
			command = message.text.split()[0][1:]
			commands = self.meetingConsumer.meeting.messagebot_set.filter(command=command).filter(is_active=True)
			if(commands):
				print('debug : command activated : '+commands[0].message)
				self.send_message(settings.BOT_MSG_PREFIX+commands[0].message)
				self.print_message({'author':settings.TWITCH_NICKNAME,'text':settings.BOT_MSG_PREFIX+commands[0].message,'source':'t'})
			
			# is this a revolution bot
			self.meetingConsumer.listen_revolution_bot(command,message.sender)
			

	def terminate(self):
		if(settings.DEBUG): print('debug : twitch terminating (i.e thread closing)')

		if(self.meetingConsumer.meeting.platform == 'TW' or self.meetingConsumer.meeting.platform == 'MX'):
			self.twitchBotPoller.terminate()

		self.chat.irc.active = False
		self.chat.irc.socket.close()	
		self.chat.dispose()

	def run(self):
		if(settings.DEBUG): print('debug : twitch poll start')
		self.chat.subscribe(self.handle_question) # todo in fact, all the terminate is bc i dont know how to unsubscribe
		if(settings.DEBUG): print('debug : twitch poll running')

	def stop(self):
		if(settings.DEBUG): print('debug : twitch stopping (i.e polling the question stops)')
		self.terminate()
		self.chat = twitch.Chat(channel=self.channel,nickname=settings.TWITCH_NICKNAME,oauth='oauth:'+self.meetingConsumer.meeting.twitch_api.oauth,helix=self.helix)
		self.chat.subscribe(self.show_message)
		self.chat.subscribe(self.bot_listen)
		if(settings.DEBUG):
			print('debug : twitch chat polling stopped, messages listening restarted')
