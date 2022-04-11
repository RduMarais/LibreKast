import threading
import twitch
from django.conf import settings
from .models import Choice, Question, Meeting,Attendee,Vote


INTERACTION_CHAR = '#' 
PRINT_MESSAGES = False

class TwitchHandler(threading.Thread):
	meetingConsumer = None

	def __init__(self,channel):
		helix = twitch.Helix(settings.TWITCH_CLIENT_ID, settings.TWITCH_CLIENT_SECRET)
		self.chat = twitch.Chat(channel='#'+channel,nickname='bot',oauth='oauth:'+settings.TWITCH_OAUTH_TOKEN,helix=helix)
		print('twitch object initiated')


	def print_message(self,chatlog):
		self.meetingConsumer.notify_chat(chatlog)

	def show_message(self,message: twitch.chat.Message) -> None:
		 print(f'author {message.sender}, text: {message.text}')
		 self.print_message({'author':message.sender,'text':message.text,'source':'t'})

	def handle_question(message: twitch.chat.Message) -> None:
		 if message.text.startswith('!test'):
				 message.chat.send('test bot')


	def terminate(self):
		chat.irc.active = False
		chat.irc.socket.close()	
		chat.dispose()

	def run(self):
		print('twitch object started')
		self.chat.subscribe(self.show_message)