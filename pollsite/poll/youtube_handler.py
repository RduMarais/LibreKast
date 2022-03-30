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
			attendee = Attendee(name=chat.author.name,meeting=self.questionConsumer.meeting,score=0) # is this secure ? 
			attendee.save()
		# attendee = chat.author.name

		if(self.question_type == 'WC'):
			self.questionConsumer.add_word(chat.message[1:],attendee) # TODO add attendee
			self.questionConsumer.notify_add_word(chat.message[1:])
			print('debug : WordCloud added message '+chat.message[1:])
		elif(self.question_type == 'PL'):
			self.questionConsumer.receive_vote("{'choice':'c.message'}")
		# elif(self.question_type == 'QZ'):



	def run(self):
		# self._running = True # else it will not allow 2 starts in a meeting
		while(self._running and self.chat.is_alive()):
			# print(f'debug : chat is running')
			# time.sleep(2)
			for c in self.chat.get().sync_items():
				if(c.message.startswith(INTERACTION_CHAR)):
					self.parse_message(c)
					# print(f"debug : parse message [{c.author.name}]- {c.message}")

