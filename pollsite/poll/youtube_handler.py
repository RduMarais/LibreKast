import threading
import time
import json
import os

import pytchat

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

from django.conf import settings
from .models import Choice, Question, Meeting,Attendee,Vote,YoutubeAPI,PeriodicBot


# This class is designed to create a simple handler for managing Youtube live stream chat message with an API key
# this uses both pytchat to fetch chat (read-only) and youtube API to post messages
# all application logic lies in the consumers.py file

class YoutubeChatError(Exception): # not used yet
	pass

class YoutubeOAuthError(Exception):

	def __init__(self,message,url,flow):
		self.url = url
		self.flow = flow
		super().__init__(message)

PRINT_MESSAGES = True

class YoutubeHandler(threading.Thread):
	meetingConsumer = None
	youtube_api_client = None
	
	def __init__(self,youtube_api,yt_id):
		threading.Thread.__init__(self)
		self._running = True  # is the handler running and fetching chat message
		self._polling = False # is the handler listening for answers to LibreKast questions
		self.listener = pytchat.create(video_id=yt_id,interruptable=False)
		# for bots 
		self.time_iterator = 0
		self.periodic_bot_iterator = 0

		if(youtube_api):
			if(settings.OAUTHLIB_INSECURE_TRANSPORT):
				os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
			# try:
			(success,creds) = self.get_youtube_api_creds(youtube_api) # this may raise errors
			# except YoutubeOAuthError as e:
			if success: # creds contains a creds object and we continue
				self.youtube_api_client = self.get_youtube_api_client_from_creds(youtube_api,creds)
				self.liveChatID = self.get_chat_id(yt_id)
				self.nextPageToken = None
			else: # creds contains an oauth error object and we wait for fetch_oauth_token
				self.oauth_error = creds

			print('debug : YT API INIT DONE')
		else:
			print('debug : no YT API : only listening')



	def get_youtube_oauth(self,youtube_api):
		api_config = {
			"installed": {
				"client_id": youtube_api.client_id,
				"client_secret":youtube_api.client_secret,
				"redirect_uris": settings.YOUTUBE_REDIRECT_URIS,
				"auth_uri": settings.YOUTUBE_AUTH_URI,
				"token_uri": settings.YOUTUBE_TOKEN_URI
			}
		}
		flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_config(
			api_config,settings.YTAPI_SCOPES)
		flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob' # this shows the user the code
		authorization_url, state = flow.authorization_url(
			access_type='offline',
			include_granted_scopes='true')
		return YoutubeOAuthError('OAUTH Authorization Error : go to this URL :  ',authorization_url,flow)


	def fetch_oauth_token(self,youtube_api,yt_id,oauth_code):
		flow = self.oauth_error.flow
		flow.fetch_token(code=oauth_code)
		creds = flow.credentials
		youtube_api.authorized_credentials=creds.to_json()
		youtube_api.save()
		self.youtube_api_client = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
		self.liveChatID = self.get_chat_id(yt_id)
		self.nextPageToken = None
		print('debug : YT API INIT DONE with code fetching')


	# Setup OAuth API
	def get_youtube_api_creds(self,youtube_api):
		creds = None
		# case : the user has already connected once
		if(youtube_api.authorized_credentials):
			creds = Credentials.from_authorized_user_info(
				json.loads(youtube_api.authorized_credentials))
		# If there are no (valid) credentials available, let the user log in.
		if not creds or not creds.valid:
			if creds and creds.expired and creds.refresh_token:
				try:
					creds.refresh(Request())
				except RefreshError:
					oauth_error = self.get_youtube_oauth(youtube_api) # may raise error
					return (False,oauth_error)
			else:
				oauth_error = self.get_youtube_oauth(youtube_api) # may raise error
				return (False,oauth_error)
		return (True,creds)



	def get_youtube_api_client_from_creds(self,youtube_api,creds):
		# Save the credentials for the next run
		youtube_api.authorized_credentials=creds.to_json()
		youtube_api.save()

		return googleapiclient.discovery.build("youtube", "v3", credentials=creds)

	# use OAuth API
	def get_chat_id(self,liveID):
		print('debug : fetch chat ID')
		request_chat_id = self.youtube_api_client.liveBroadcasts().list(
			part="snippet,contentDetails,status",
			id=liveID
		)
		response = request_chat_id.execute()

		livechatID = response['items'][0]['snippet']['liveChatId']
		print('debug : live chat ID : '+livechatID)
		return livechatID


	# TODO to be removed
	# Uses OAuth API
	def fetch_chat_message(self):
		if(settings.DEBUG): print('debug : fetch messages')
		request_chatlog = None
		if(self.nextPageToken):
			request_chatlog = self.youtube_api_client.liveChatMessages().list(
				liveChatId=self.liveChatID,
				part="snippet,authorDetails",
				pageToken=self.nextPageToken
			)
		else:
			request_chatlog = self.youtube_api_client.liveChatMessages().list(
				liveChatId=self.liveChatID,
				part="snippet,authorDetails"
			)
		response = request_chatlog.execute()
		self.nextPageToken = response['nextPageToken']
		incoming_messages = []
		if(response['pageInfo']['totalResults']>0):
			res_size = str(response['pageInfo']['totalResults'])
			if(settings.DEBUG):
				print(f'{res_size} chat messages already')
			for item in response['items']:
				msg = {
					'text':item['snippet']['displayMessage'],
					'author':item['authorDetails']['displayName'],
					'isChatOwner':item['authorDetails']['isChatOwner'],
					'isChatSponsor':item['authorDetails']['isChatSponsor'],
					'isChatModerator':item['authorDetails']['isChatModerator']
				}
				incoming_messages.append(msg)
		return incoming_messages


	def terminate(self):
		self._running = False

	# Uses PytChat listener
	def parse_message(self,chat_msg):
		attendee = self.meetingConsumer.check_attendee(chat_msg.author.name,is_subscriber=chat_msg.author.isChatSponsor,is_youtube=True)

		question_type = self.meetingConsumer.meeting.current_question().question_type

		if(question_type == 'WC'):
			self.meetingConsumer.add_word(chat_msg.message[1:],attendee) # TODO add attendee
			self.meetingConsumer.notify_add_word(chat_msg.message[1:])
			if(settings.DEBUG):
				print('debug : WordCloud added message '+chat_msg.message[1:])
		elif(question_type == 'PL' or question_type == 'QZ'):
			if(settings.DEBUG):
				print('debug : Poll/Quizz adding vote '+chat_msg.message[1:]+ ' from user '+chat_msg.author.name)
			choiceset = self.meetingConsumer.meeting.current_question().choice_set.filter(slug=chat_msg.message[1:])
			if(choiceset):
				poll_choice = {'choice': choiceset[0].id} # this gets choice ID
				self.meetingConsumer.receive_vote(poll_choice,attendee)
			else : 
				if(settings.DEBUG):
					print('debug : no poll choice for vote '+chat_msg.message[1:]+ ' from user '+chat_msg.author.name)

	# Uses PytChat listener
	def print_message(self,chat_msg):
		if(chat_msg.author.isChatSponsor):
			self.meetingConsumer.notify_chat({'author':chat_msg.author.name,'text':chat_msg.message,'source':'ys'})
		elif(chat_msg.message.startswith(settings.BOT_MSG_PREFIX) or chat_msg.message.startswith(settings.BOT_MSG_PREFIX_YOUTUBE_ENCODED)):
			print('debug : message sent by a bot, so not re-showing it in the librekast chat')
			print(str(chat_msg.message) +' : '+ str(chat_msg.author))
			# self.meetingConsumer.notify_chat({'author':chat_msg.author.name,'text':chat_msg.message,'source':'y'})
		else:
			self.meetingConsumer.notify_chat({'author':chat_msg.author.name,'text':chat_msg.message,'source':'y'})

	# Uses PytChat listener
	def bot_listen(self,chat_msg):
		command = chat_msg.message.split()[0][1:]
		commands = self.meetingConsumer.meeting.messagebot_set.filter(command=command).filter(is_active=True)
		if(commands):
			print('debug : command activated : '+commands[0].message)
			self.send_message(settings.BOT_MSG_PREFIX+commands[0].message)
		self.meetingConsumer.listen_revolution_bot(command,chat_msg.author.name)

	# Uses OAuth API
	def send_message(self,message):
		try:
			request = self.youtube_api_client.liveChatMessages().insert(
				part="snippet",
				body={
				  "snippet": {
					"liveChatId": self.liveChatID,
					"type": "textMessageEvent",
					"textMessageDetails": {
					  "messageText": message
					}
				  }
				}
			)
			response = request.execute()
		except:
			print("Error posting message on youtube live chat")

	def regulary_send_periodic_bot(self):
		self.time_iterator = (self.time_iterator + 1) % 3600 # this is a counter
		if(self.time_iterator % self.meetingConsumer.meeting.periodic_bot_delay == 0): # every periodic_bot_delay seconds, do 
			self.send_message(self.meetingConsumer.get_periodic_bot(self.periodic_bot_iterator))
			# iterate over the periodic bots
			self.periodic_bot_iterator = (self.periodic_bot_iterator + 1) % len(self.meetingConsumer.meeting.periodicbot_set.filter(is_active=True))


	# Main function runningand syncrhonizing both PytChat Listener and OAuth messages
	def run(self):
		print('debug : YT chat : listening')
		# this is basically one iteration per second
		while(self._running and self.listener.is_alive()):
			# code below fetches the outube api
			for c in self.listener.get().sync_items():
				# listen for answers to activities
				if(c.message.startswith(settings.INTERACTION_CHAR) and self._polling):
					self.parse_message(c)
				# show mesages in dashboard
				if(PRINT_MESSAGES):
					self.print_message(c)
				# send bot command (requires OAuth)
				if(c.message.startswith('!') and self.youtube_api_client):
					self.bot_listen(c)
			# regularly sends a message in a set of predefined messages (requires OAuth)
			if(self.youtube_api_client):
				self.regulary_send_periodic_bot()
			print('+',end='')
		if(settings.DEBUG): print('debug : YT handler stopped')


