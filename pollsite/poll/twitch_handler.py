import threading
import twitch
import datetime
import json
import time
import requests
import pprint

# For testing
import asyncio

from twitchAPI import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.types import AuthScope, ChatEvent, TwitchAPIException
from twitchAPI.helper import first
from twitchAPI.chat import Chat, EventData, ChatMessage, ChatSub, ChatCommand
from twitchAPI.eventsub import EventSub

from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext as _
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync, sync_to_async

from .models import Choice, Question, Meeting,Attendee,Vote
from .utils import TwitchBotPoller

PRINT_MESSAGES = False
TWITCH_MSG_PERIOD = 5
USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]
TEST_URL = 'http://localhost:8000/poll/twitch_auth/'
TEST_URL = 'http://localhost:8000/poll/twitch_auth/1/?error=redirect_mismatch\u0026error_description=Parameter\u002bredirect_uri\u002bdoes\u002bnot\u002bmatch\u002bregistered\u002bURI\u0026state=385e7193-b84e-49dd-8740-e9fe885b8ea3";'

## Uses : https://github.com/PetterKraabol/Twitch-Python

# no need for run start and stop bc the lib Twtich class itselfs extends the Thread class
class NewTwitchHandler(threading.Thread):
	meetingConsumer = None
	TARGET_SCOPES = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT,AuthScope.MODERATOR_READ_FOLLOWERS]


#### GENERAL METHODS #####

	async def authenticate_client(self,code):
		token, refresh_token = await self.auth.authenticate(user_token=code)
		if(settings.DEBUG) : print(f'[3] authenticate : {token} and refresh : {refresh_token}')
		await self.twitch_new.set_user_authentication(token,self.TARGET_SCOPES,refresh_token)
		if(settings.DEBUG) : print(f'[3] scopes {self.twitch_new.get_user_auth_scope()}')


	# get called by a request and updates user codes
	async def authenticate_callback(self,callback: dict):
		if(callback['state'] == self.auth.state):
			if(settings.DEBUG): print(f'[2] : CALLBACKED')

			# get access tokens
			await self.authenticate_client(callback['code'])
			
			# Discard django channel used to callback
			await self.meetingConsumer.channel_layer.group_discard(
				f'callback_{self.twitch_api.id}',
				self.meetingConsumer.channel_name
			)
			if(settings.DEBUG): print('[2] Channel discarded and user authenticated')

			await self.start_chat() # -> calls method down there that starts everything
		else:
			if(settings.DEBUG) : print('error : bad state (oauth request replay)')

	# not sure why this is needed
	def app_refresh(self,token: str):
		print(f'my new app token is: {token}')

	# print in dashboard and all chat subscriber sessions
	async def print_message(self,message):
		await self.meetingConsumer.channel_layer.group_send(
			self.meetingConsumer.meeting_group_name+'_chat',
			{
				'type': 'admin_message', # is it though ?
				'message': {
					'message':'notify-chat',
					'chat':message,
				}
			}
		)


#### BOTS, ANIMATION AND METHODS #####

	# this will be called when the event READY is triggered, which will be on bot start
	async def on_ready(self,ready_event: EventData):
		if(settings.DEBUG) : print('debug new : Bot is ready for work, joining channels')
		# join our target channel, if you want to join multiple, either call join for each individually
		# or even better pass a list of channels as the argument
		await ready_event.chat.join_room(self.channel)
		# you can do other bot initialization things in here

	# this will be called whenever a message in a channel was send by either the bot OR another user
	async def on_message(self, msg: ChatMessage):
		print(f'debug new : {msg.user.name} dit "{msg.text}" ({msg.room.name})')
		# user is ChatUser -> msg.user.vip, msg.user.subscriber, msg.user.mod, msg.user.badge_info aussi msg.bits
		await self.print_message({'author':msg.user.name,'text':msg.text,'source':'t','sub':msg.user.subscriber, 'badges':msg.user.badge_info})

	# this will be called whenever someone subscribes to a channel
	async def on_sub(self, sub: ChatSub):
		print(f'New subscription in {sub.room.name}: Type={sub.sub_plan} Message={sub.sub_message}')
		await self.print_message({'author':settings.TWITCH_NICKNAME,'text':sub.sub_message,'source':'t','sub':True})
		# sub_type: str, sub_message: str, sub_plan: str, sub_plan_name: str, system_message: str
		# TODO Alert

	async def on_follow(self, data: dict):
		if(settings.DEBUG) : print('DEBUG new : FOLLOW data = '+str(data))
		# TODO Alert`
		animation_set = self.twitch_api.animation_set.filter(event_type='F') #await ? 
		l =  await sync_to_async(len)(animation_set)
		if(l > 0): # cant be async need to be in a sync to async or 
			animation = await animation_set[0]
			if(animation.alert):
				await self.meetingConsumer.send_bot_alert(animation) # await


	# this will be called whenever the !reply command is issued
	async def msg_command(self, cmd: ChatCommand):
		print(f'[4] REPLY {cmd.user.name}')
		msgBot = next(mb for mb in self.bots if mb.command == cmd.name)
		if(msgBot):
			print(f'[4] command {msgBot.command}')
			await cmd.reply(f'{settings.BOT_MSG_PREFIX}{msgBot.message}')
			await self.print_message({'author':settings.TWITCH_NICKNAME,'text':f'{settings.BOT_MSG_PREFIX} {msgBot.message}','source':'b'})
			# TODO : cmd with params 
			# TODO : check bot type and act depending on type
			# if len(cmd.parameter) == 0:
			# else:
			# 	await cmd.reply(f'debug new : {cmd.user.name}: {cmd.parameter}')



#### INIT AND AUTHENT ####

	# is not async
	def __init__(self,channel,twitch_api,meetingConsumer):
		self.meetingConsumer = meetingConsumer
		self.twitch_api = twitch_api
		self.channel = channel
		# TODO : problème : je peux pas update le bot ?
		self.bots = [] 
		for bot in self.meetingConsumer.meeting.messagebot_set.filter(is_active=True): # because this is sync
			self.bots.append(bot)
		if(settings.DEBUG) : print('debug : message bots list = '+str(self.bots))
		asyncio.run(self.configure_ntwhandler(channel)) # ASYNC STARTS HERE for testing
		# asyncio. wait for authentication
		# asyncio.run(self.wait_for_connection()) # ASYNC STARTS HERE for testing

	
	async def configure_ntwhandler(self,channel):
		self.twitch_new = await Twitch(self.twitch_api.client_id, self.twitch_api.client_secret)
		self.twitch_new.app_auth_refresh_callback = self.app_refresh # not sure why this is needed but i guess its part of the app registration

		# for testing --> TDO remove
		self.user = await first(self.twitch_new.get_users(logins=channel)) 
		if(settings.DEBUG) : print(f"[1] user : {self.user.display_name} ({self.user.description})")
		
		# setup userauth
		self.auth = UserAuthenticator(self.twitch_new, self.TARGET_SCOPES, force_verify=False, url=self.twitch_api.api_callback_url) # with callback
		try: # TODO : for some reason this never executes without error
			# try to connect using known value of code
			if(settings.DEBUG): print(f'[1] secret code : {self.twitch_api.auth_code}')
			res = await self.authenticate_client(self.twitch_api.auth_code)
			if(settings.DEBUG) : print(f'[1] connection : {res}')
		except TwitchAPIException :
			# if the code is not valid anymore, request a new one
			# authenticate with following
			auth_url = self.auth.return_auth_url()
			if(settings.DEBUG) : print('[1] url to connect to : '+self.auth.return_auth_url())

			# Send URL for oAuth
			await self.meetingConsumer.channel_layer.group_send(
				self.meetingConsumer.meeting_group_name+'_admin',
				{'type':"meeting_message",
				'message': {'message':'twitch-oauth-error','text':f'You need another Twitch API credential :','url':auth_url },
				},
				)
			if(settings.DEBUG) : print('[1] debug new : before channel name listening')
			# await self.meetingConsumer.channel_layer.group_discard(
			await self.meetingConsumer.channel_layer.group_add(
				f'callback_{self.twitch_api.id}',
				self.meetingConsumer.channel_name
			)
		else:
			# if the code is valid, start chat
			await self.start_chat()
			if(settings.DEBUG) : print('[1]debug new : twitch chat started')


	# Thread 3
	#  is this in use ?
	# async def wait_for_connection(self):
	# 	# wait for callback to authenticate
	# 	while(not self.twitch_new.get_user_auth_scope()):
	# 		if(settings.DEBUG): print(f'[3] waiting for auth callback with scope : {self.twitch_new.get_user_auth_scope()}')
	# 		await asyncio.sleep(10)

	# 	if(settings.DEBUG) : print('[3] : USER AUTHENTICATED FROM OTHER THREAD')
	# 	await self.start_chat()
	# 	if(settings.DEBUG) : print('[3] : twitch chat started')


	# MAIN START AND METHOD REGISTRATIONS
	async def start_chat(self):
		self.chat = await Chat(self.twitch_new) # miss user auth
		
		# register a bunch of stuff

		self.chat.start()
		print('INFO : new twitch chat started')

		self.chat.register_event(ChatEvent.READY, self.on_ready)
		# https://github.com/Teekeks/pyTwitchAPI

		# listen to channel subscriptions
		self.chat.register_event(ChatEvent.SUB, self.on_sub)
		# there are more events, you can view them all in this documentation
		# await event_sub.listen_channel_follow_v2(user.id, user.id, on_follow)

		# you can directly register commands and their handlers, this will register the !reply command
		for msg_bot in self.bots:
			self.chat.register_command(msg_bot.command, self.msg_command)

		# listen to chat messages
		self.chat.register_event(ChatEvent.MESSAGE, self.on_message)
		await self.meetingConsumer.channel_layer.group_send(
			self.meetingConsumer.meeting_group_name+'_admin',
			{'type':"meeting_message",'message': {'message':'twitch-oauth-ok','text': 'OAUTH done'}},
			)
		
		### Event Sub (à init dans une aute méthode)
		if(self.twitch_api.eventsub_callback_url):
			# est ce que ça lance un serveur ou ça écoute ? -> ça lance un serveur -> à déplacer dans l'API django
			if(settings.DEBUG) : print('DEBUG NEW : startinng creation of event sub')
			self.event_sub = EventSub(self.twitch_api.eventsub_callback_url, self.twitch_api.client_id, self.twitch_api.eventsub_callback_port, self.twitch_new) # test webhook
			self.event_sub._host = '127.0.0.1' # not listening on every host, only on localhost:8081
			if(settings.DEBUG) : print('DEBUG NEW : created event sub')
			self.event_sub.logger.propagate = True
			await self.event_sub.unsubscribe_all()
			if(settings.DEBUG) : print('DEBUG NEW : unsub')
			self.event_sub.start()
			if(settings.DEBUG) : print('DEBUG NEW : started event sub')
			follow_animation_set = sync_to_async(self.twitch_api.animation_set.filter)(event_type='F')
			if(follow_animation_set):
				# listen_channel_follow_v2(broadcaster_user_id, moderator_user_id, callback)
				#  has to be user id -> use dedicated class
				me_user = await first(self.twitch_new.get_users(logins='rom___101'))
				await self.event_sub.listen_channel_follow_v2(me_user.id, me_user.id, self.on_follow) #timesout
				if(settings.DEBUG) : print('DEBUG NEW : subbed for follows')


#### FINISH ####

	def terminate(self):
		if(hasattr(self,'chat')):
			self.chat.stop()
		if(hasattr(self,'event_sub')):
			self.event_sub.stop()
		print('NTW : stopped')















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
			# self.new_twitch = await Twitch(twitch_api.client_id, twitch_api.client_secret)
			# ,scopes=['channel:read:subscriptions','chat:read','chat:edit']
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
			self.subscribe_webhooks()
		print('debug : successfully initiated Twitch handler')

		# INIT Webhook


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


	def get_twitch_user(self,username):
		if(settings.DEBUG): print(f'debug : get info on user : {username}')
		endpoint_url = f"https://api.twitch.tv/helix/users?login={username}"
		headers = {
			"Authorization" : self.helix.api.bearer_token,
			"Client-Id" :self.helix.api.client_id,
			"Content-Type" :"application/json",
			}
		if(settings.DEBUG): print(f'debug : request headers {headers}')
		response = requests.get(endpoint_url,headers=headers)
		if(settings.DEBUG): print(f'debug : return response code {response.status_code}')
		resp_json = response.json()
		if(settings.DEBUG): print(f'debug : return response body : {resp_json}')
		if('data' in resp_json):
			return resp_json['data']

	def subscribe_webhooks(self):
		webhooks_set = self.meetingConsumer.meeting.twitchwebhook_set.filter(event_type='F').filter(helix_id__exact='')
		if(webhooks_set):
			broadcaster_user = self.get_twitch_user(self.meetingConsumer.meeting.channel_id)
			broadcaster_user_id = broadcaster_user[0]['id']
			for tw_webhook in self.meetingConsumer.meeting.twitchwebhook_set.filter(event_type='F').filter(helix_id__exact=''):
				print(f'setup : webhook name : {tw_webhook.name}')
				webhook_url = 'https://api.twitch.tv/helix/eventsub/subscriptions'
				data_json = {
					"type":"channel.follow", 
					"version":"1",
					"condition":{"broadcaster_user_id":broadcaster_user_id},
					"transport":{
						"method":"webhook",
						"callback":"https://"+settings.ALLOWED_HOSTS[-1]+"/poll/webhook/"+str(tw_webhook.id)+"/",
						"secret":tw_webhook.secret
						}
					}
				headers = {
					"Authorization" : self.helix.api.bearer_token,
					"Client-Id" :self.helix.api.client_id,
					"Content-Type" :"application/json",
				}
				print(f'setup : headers : {headers}')
				print(f'setup : data : {data_json}')
				response = requests.post(webhook_url, json=data_json,headers=headers) 
				print(f'setup : response : {response.text}')
				print(f'setup : response : {response.status_code}')
				if('data' in response.json()):
					print(response.json()['data'][0]['id'])
					tw_webhook.helix_id = response.json()['data'][0]['id']
					tw_webhook.save()
				# TODO : i should put this in an error
				if('error' in response.json()):
					channel_layer = get_channel_layer()
					async_to_sync(channel_layer.group_send)(
						self.meetingConsumer.meeting_group_name+'_admin',
						{
							'type': 'admin_message',
							'message': {
								'message':'admin-error',
								'text':response.json()['message'] + ' (-> Your API key probably doesnt have permissions to read events on the broadcaster channel)'
							}
						}
					)

	def unsubscribe_webhook(self,tw_webhook):
		print(f'unsub : webhook name : {tw_webhook.name}')
		webhook_url = f"https://api.twitch.tv/helix/eventsub/subscriptions?id={tw_webhook.helix_id}"
		headers = {
			"Authorization" : self.helix.api.bearer_token,
			"Client-Id" :self.helix.api.client_id,
			"Content-Type" :"application/json",
		}
		response = requests.request(method='DELETE', url=webhook_url,headers=headers) 
		if(response.status_code >=200 and response.status_code <300):
			tw_webhook.helix_id = ""
			tw_webhook.save()

	def unsubscribe_webhooks(self):
		for tw_webhook in self.meetingConsumer.meeting.twitchwebhook_set.filter(event_type='F'):
			self.unsubscribe_webhook(tw_webhook)


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

		if(self.meetingConsumer.meeting.platform == 'TW' or self.meetingConsumer.meeting.platform == 'MX' and self.meetingConsumer.meeting.periodicbot_set.filter(is_active=True)):
			self.twitchBotPoller.terminate()
			self.unsubscribe_webhooks()

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
