import threading
import time
import pytchat

from django.conf import settings
from .models import Choice, Question, Meeting,Attendee,Vote


# This class is designed to create a simple handler for managing Youtube live stream chat message
# I put this class in a separate file to show the difference : YoutubeHandler is the thread to poll YT messages.
# all application logic lies in the consumers.py file

# This char is the one that will trigger the parsing
# I recommend using '#', @ is for testing purposes
# on Youtube, "@" is for tagging people and "!"" for bots
INTERACTION_CHAR = '#' 
PRINT_MESSAGES = True

class YoutubeHandler(threading.Thread):
	questionConsumer = None
	  
	def __init__(self,yt_id,question_type):
		threading.Thread.__init__(self)
		self._running = True
		self.question_type = question_type
		self.chat = pytchat.create(video_id=yt_id,interruptable=False)
	
	def terminate(self):
		self._running = False

	def parse_message(self,chat):
		# TODO add attendee
		attendee = None
		attendee_queryset = Attendee.objects.filter(name=chat.author.name)
		if(attendee_queryset): # is this secure ?
			attendee = attendee_queryset[0]
		else:
			attendee = Attendee(name=chat.author.name,meeting=self.questionConsumer.meeting,score=0,is_subscriber=chat.author.isChatSponsor) # is this secure ? 
			attendee.save()
		# attendee = chat.author.name

		if(self.question_type == 'WC'):
			self.questionConsumer.add_word(chat.message[1:],attendee) # TODO add attendee
			self.questionConsumer.notify_add_word(chat.message[1:])
			if(settings.DEBUG):
				print('debug : WordCloud added message '+chat.message[1:])
		elif(self.question_type == 'PL' or self.question_type == 'QZ'):
			if(settings.DEBUG):
				print('debug : Poll/Quizz adding vote '+chat.message[1:]+ ' from user '+chat.author.name)
			choiceset = self.questionConsumer.meeting.current_question().choice_set.filter(slug=chat.message[1:])
			if(settings.DEBUG):
				print('debug : Poll/Quizz adding vote '+chat.message[1:]+ ' from user '+chat.author.name)

			if(choiceset):
				message = {'choice': choiceset[0].id} # this gets choice ID
				self.questionConsumer.receive_vote(message,attendee)
			else : 
				if(settings.DEBUG):
					print('debug : no poll choice for vote '+chat.message[1:]+ ' from user '+chat.author.name)

		# elif(self.question_type == 'QZ'):

	def print_message(self,chat):
		self.questionConsumer.notify_chat({'author':chat.author.name,'text':chat.message,'source':'y'})


	def run(self):
		# self._running = True # else it will not allow 2 starts in a meeting
		while(self._running and self.chat.is_alive()):
			for c in self.chat.get().sync_items():
				if(c.message.startswith(INTERACTION_CHAR)):
					self.parse_message(c)
				if(PRINT_MESSAGES):
					self.print_message(c)

