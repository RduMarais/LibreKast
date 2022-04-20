import threading
import time
import pytchat

from django.conf import settings
from .models import Choice, Question, Meeting,Attendee,Vote


# This class is designed to create a simple handler for managing Youtube live stream chat message without API keys
# I put this class in a separate file to show the difference : YoutubeHandler is the thread to bot and interact with the API,
# YoutubeLIstener is the thread to use public data (public or non-referenced lives) in read-only mode
# all application logic lies in the consumers.py file

PRINT_MESSAGES = True

class YoutubeListener(threading.Thread):
	meetingConsumer = None
	  
	def __init__(self,yt_id):
		threading.Thread.__init__(self)
		self._running = True
		self._polling = False
		self.chat = pytchat.create(video_id=yt_id,interruptable=False)
	
	def terminate(self):
		self._running = False

	def parse_message(self,chat):
		attendee = self.meetingConsumer.check_attendee(chat.author.name,is_subscriber=chat.author.isChatSponsor,is_youtube=True)

		question_type = self.meetingConsumer.meeting.current_question().question_type

		if(question_type == 'WC'):
			self.meetingConsumer.add_word(chat.message[1:],attendee) # TODO add attendee
			self.meetingConsumer.notify_add_word(chat.message[1:])
			if(settings.DEBUG):
				print('debug : WordCloud added message '+chat.message[1:])
		elif(question_type == 'PL' or question_type == 'QZ'):
			if(settings.DEBUG):
				print('debug : Poll/Quizz adding vote '+chat.message[1:]+ ' from user '+chat.author.name)
			choiceset = self.meetingConsumer.meeting.current_question().choice_set.filter(slug=chat.message[1:])
			if(choiceset):
				poll_choice = {'choice': choiceset[0].id} # this gets choice ID
				self.meetingConsumer.receive_vote(poll_choice,attendee)
			else : 
				if(settings.DEBUG):
					print('debug : no poll choice for vote '+chat.message[1:]+ ' from user '+chat.author.name)


	def print_message(self,chat):
		if(chat.author.isChatSponsor):
			self.meetingConsumer.notify_chat({'author':chat.author.name,'text':chat.message,'source':'ys'})
		else:
			self.meetingConsumer.notify_chat({'author':chat.author.name,'text':chat.message,'source':'y'})



	def run(self):
		print('debug : YT chat listening')
		# self._running = True # else it will not allow 2 starts in a meeting
		while(self._running and self.chat.is_alive()):
			for c in self.chat.get().sync_items():
				if(c.message.startswith(settings.INTERACTION_CHAR) and self._polling):
					self.parse_message(c)
				if(PRINT_MESSAGES):
					self.print_message(c)
