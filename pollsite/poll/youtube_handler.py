import threading
import time
import json
import os

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from django.conf import settings
from .models import Choice, Question, Meeting,Attendee,Vote,YoutubeAPI,PeriodicBot


# This class is designed to create a simple handler for managing Youtube live stream chat message with an API key
# I put this class in a separate file to show the difference : YoutubeHandler is the thread to bot and interact with the API,
# YoutubeLIstener is the thread to use public data (public or non-referenced lives) in read-only mode
# all application logic lies in the consumers.py file

PRINT_MESSAGES = True

class YoutubeHandler(threading.Thread):
	meetingConsumer = None
	time_iterator = 0
	periodic_bot_iterator = 0
	  
	def __init__(self,youtube_api,yt_id):
		threading.Thread.__init__(self)
		self._running = True
		self._polling = False
		if(settings.OAUTHLIB_INSECURE_TRANSPORT):
			os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

		self.youtube_api_client = self.get_youtube_api_client(youtube_api)
		
		self.liveChatID = self.get_chat_id(yt_id)
		self.nextPageToken = None
		print('debug : YT API INIT DONE')



	def get_youtube_api_client(self,youtube_api):
		creds = None
		# case : the user has already connected once
		if(youtube_api.authorized_credentials):
			creds = Credentials.from_authorized_user_info(
				json.loads(youtube_api.authorized_credentials))
		# If there are no (valid) credentials available, let the user log in.
		if not creds or not creds.valid:
			if creds and creds.expired and creds.refresh_token:
				creds.refresh(Request())
			else:
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
				print('debug : OAUTH Authorization : go to this URL :')
				# self.meetingConsumer.send(text_data=json.dumps({'message':'error test API'}))
				print(authorization_url)
				# i kinda need to make the redirection myself for now ?
				oauth_code = input('INPUT : Press any key when authorized\n') 
				flow.fetch_token(code=oauth_code)
				creds = flow.credentials

			# Save the credentials for the next run
			youtube_api.authorized_credentials=creds.to_json()
			youtube_api.save()

		return googleapiclient.discovery.build("youtube", "v3", credentials=creds)


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


	def fetch_chat_message(self):
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

	def parse_message(self,msg):
		attendee = self.meetingConsumer.check_attendee(msg['author'],is_subscriber=False,is_youtube=True)

		question_type = self.meetingConsumer.meeting.current_question().question_type

		if(question_type == 'WC'):
			self.meetingConsumer.add_word(msg['text'][1:],attendee) # TODO add attendee
			self.meetingConsumer.notify_add_word(msg['text'][1:])
			if(settings.DEBUG):
				print('debug : WordCloud added message '+msg['text'][1:])
		elif(question_type == 'PL' or question_type == 'QZ'):
			if(settings.DEBUG):
				print('debug : Poll/Quizz adding vote '+msg['text'][1:]+ ' from user '+msg['author'])
			choiceset = self.meetingConsumer.meeting.current_question().choice_set.filter(slug=msg['text'][1:])
			if(choiceset):
				poll_choice = {'choice': choiceset[0].id} # this gets choice ID
				self.meetingConsumer.receive_vote(poll_choice,attendee)
			else : 
				if(settings.DEBUG):
					print('debug : no poll choice for vote '+msg['text'][1:]+ ' from user '+msg['author'])


	def print_message(self,msg):
		self.meetingConsumer.notify_chat({'author':msg['author'],'text':msg['text'],'source':'y'})

	def bot_listen(self,msg):
		command = self.meetingConsumer.meeting.messagebot_set.filter(command=msg['text'].split()[0][1:]).filter(is_active=True)
		if(command):
			print('debug : command activated : '+command[0].message)
			self.send_message(settings.BOT_MSG_PREFIX+command[0].message)

	def send_message(self,message):
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
		if(settings.DEBUG):
			print(response)

	def send_periodic_bots(self):
		if(self.time_iterator % settings.PERIODIC_BOT_DELAY == 0 and self.meetingConsumer.meeting.periodicbot_set.all()):
			# send jth bot message
			self.send_message(settings.BOT_MSG_PREFIX+self.meetingConsumer.meeting.periodicbot_set.all()[self.periodic_bot_iterator].message)
			# iterate over periodic_bot_iterator
			self.periodic_bot_iterator = (self.periodic_bot_iterator + 1) % len(self.meetingConsumer.meeting.periodicbot_set.all())
		self.time_iterator = self.time_iterator + 2 % 3600

	def run(self):
		print('debug : YT chat listening')
		# self._running = True # else it will not allow 2 starts in a meeting
		print('##### polling....')
		i = 0
		while(self._running):
			for c in self.fetch_chat_message():
				if(c['text'].startswith(settings.INTERACTION_CHAR) and self._polling):
					self.parse_message(c)
				if(PRINT_MESSAGES):
					self.print_message(c)
				if(c['text'].startswith('!')):
					self.bot_listen(c)
			self.send_periodic_bots()
			time.sleep(2)

