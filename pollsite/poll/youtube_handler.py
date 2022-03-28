import threading
import time
import pytchat

from django.conf import settings
from .models import Choice, Question, Meeting,Attendee,Vote


# This class is designed to create a simple handler for managing Youtube live stream chat message
# I put this class in a separate file to show the difference : YoutubeHandler is the thread to poll YT messages.
# all application logic lies in the consumers.py file

class YoutubeHandler(threading.Thread):
	questionConsumer = None
	  
	def __init__(self,yt_id,question_type):
		threading.Thread.__init__(self)
		self._running = True
		self.question_type = question_type
		self.chat = pytchat.create(video_id=yt_id)
	
	def terminate(self):
		self._running = False


	# def startPolling(self):
	# 	print('debug : poll would start here')
	# 	self.run

	# def stopPolling(self):
	# 	print('debug : poll would stop here')

	def run(self):
		# self._running = True # else it will not allow 2 starts in a meeting
		while(self._running and self.chat.is_alive()):
			for c in self.chat.get().sync_items():
				print(f"{c.datetime} [{c.author.name}]- {c.message}")
