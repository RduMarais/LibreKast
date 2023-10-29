import threading
# import twitch
import datetime
import json
import time
import requests
import pprint

# For testing
import asyncio

from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope, ChatEvent, TwitchAPIException
from twitchAPI.helper import first
from twitchAPI.object.eventsub import ChannelFollowEvent
from twitchAPI.chat import Chat, EventData, ChatMessage, ChatSub, ChatCommand
# from twitchAPI.eventsub import EventSub # à changer
from twitchAPI.eventsub.websocket import EventSubWebsocket

from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext as _
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync, sync_to_async

from .models import Choice, Question, Meeting,Attendee,Vote
from .utils import TwitchBotPoller

PRINT_MESSAGES = False
TWITCH_MSG_PERIOD = 5

## Uses : https://github.com/PetterKraabol/Twitch-Python

# no need for run start and stop bc the lib Twtich class itselfs extends the Thread class
class NewTwitchHandler(threading.Thread):
	meetingConsumer = None
	# 4th one is for follows, 5th one for subs
	TARGET_SCOPES = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT,AuthScope.MODERATOR_READ_FOLLOWERS, AuthScope.CHANNEL_READ_SUBSCRIPTIONS]


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

	async def send_animation(self,animation):
		if(settings.DEBUG): print(f'debug : sending alert {animation.name}')
		await self.meetingConsumer.channel_layer.group_send(
			self.meetingConsumer.meeting_group_name+'_chat',
			{
				'type': 'admin_message', # is it though ?
				'message': {
					'message':'revolution-alert',
					'alert':{'url':animation.alert.url,'text':animation.message},
				}
			}
		)

	async def send_error(self,message_dict):
		await self.meetingConsumer.channel_layer.group_send(
				self.meetingConsumer.meeting_group_name+'_admin',
				{'type':"meeting_message",
				'message': message_dict,
				},
			)

	async def stop_event_sub(self):
		try:
			await self.event_sub_new.unsubscribe_all()
			await self.event_sub_new.stop()
			if(settings.DEBUG) : print('debug : event sub stopped')
		except Exception as e:
			if(settings.DEBUG) : print('debug : error stopping event sub')

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
		# print(f'debug new : {self.event_sub}')
		# print(f'debug new : {self.event_sub_new}')
		# user is ChatUser -> msg.user.vip, msg.user.subscriber, msg.user.mod, msg.user.badge_info aussi msg.bits
		await self.print_message({'author':msg.user.name,'text':msg.text,'source':'t','sub':msg.user.subscriber, 'badges':msg.user.badge_info})

	# this will be called whenever someone subscribes to a channel
	async def on_chat_sub(self, sub: ChatSub):
		if(settings.DEBUG) : print(f'debug : CHATSUB New subscription in {sub.room.name}: Type={sub.sub_plan} Message={sub.sub_message}')
		await self.print_message({'author':settings.TWITCH_NICKNAME,'text':f'sub message : {sub.sub_message} // system message : {sub.system_message}','source':'t','sub':True})
		# sub_type: str, sub_message: str, sub_plan: str, sub_plan_name: str, system_message: str
		# TODO Alert
	
	async def on_eventsub_sub(self, data: dict):
		if(settings.DEBUG) : print(f'debug : EVENTSUB New subscription in {sub.room.name}: Type={sub.sub_plan} Message={sub.sub_message}')

	async def on_follow(self, data: ChannelFollowEvent):
		if(settings.DEBUG) : print('debug notifs : FOLLOW data = '+str(data))
		animation_set = self.twitch_api.animation_set.filter(event_type='F') #await ? 
		l =  await sync_to_async(len)(animation_set)
		if(l > 0): # cant be async need to be in a sync to async or 
			if(settings.DEBUG) : print('debug notifs : animation will start')
			animation = animation_set[0]
			if(animation.alert):
				await self.send_animation(animation) # await
			else:
				if(settings.DEBUG) : print('debug notifs : no animation file')
		else:
			if(settings.DEBUG) : print('debug notifs : no animation set')


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
		self.event_sub = None
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
			await self.send_error(message_dict={'message':'twitch-oauth-error','text':f'You need another Twitch API credential :','url':auth_url })

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


	# MAIN START AND METHOD REGISTRATIONS
	async def start_chat(self):
		self.chat = await Chat(self.twitch_new) # miss user auth
		
		# register a bunch of stuff

		self.chat.start()
		print('INFO : new twitch chat started')

		self.chat.register_event(ChatEvent.READY, self.on_ready)
		# https://github.com/Teekeks/pyTwitchAPI

		# listen to channel subscriptions
		self.chat.register_event(ChatEvent.SUB, self.on_chat_sub)
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
		if(self.twitch_api.eventsub_callback_url or True):
			# est ce que ça lance un serveur ou ça écoute ? -> ça lance un serveur -> à déplacer dans l'API django
			if(settings.DEBUG) : print('debug notifs : startinng creation of event sub')
			self.event_sub_new = EventSubWebsocket(self.twitch_new)
			# self.event_sub = EventSub(self.twitch_api.eventsub_callback_url, self.twitch_api.client_id, self.twitch_api.eventsub_callback_port, self.twitch_new) # test webhook
			# self.event_sub._host = '127.0.0.1' # not listening on every host, only on localhost:8081
			if(settings.DEBUG) : print('debug notifs: created event sub')
			# self.event_sub.logger.propagate = True
			self.event_sub_new.logger.propagate = True
			# await self.event_sub.unsubscribe_all()
			await self.event_sub_new.unsubscribe_all()
			if(settings.DEBUG) : print('debug notifs : unsub')
			# try : 
				# self.event_sub.start()
			self.event_sub_new.start()
			# print(self)
			# except Exception as e : 
			# 	raise e
				# await self.send_error(message_dict={'message':'error','text':f'The eventsub callback server could not start with URL {self.twitch_api.eventsub_callback_url} and port {self.twitch_api.eventsub_callback_port}'})
			if(settings.DEBUG) : print('debug notifs : started event sub')
			follow_animation_set = sync_to_async(self.twitch_api.animation_set.filter)(event_type='F')
			sub_animation_set = sync_to_async(self.twitch_api.animation_set.filter)(event_type='S')
			me_user = await first(self.twitch_new.get_users(logins=self.twitch_api.username))
			if(follow_animation_set):
				# listen_channel_follow_v2(broadcaster_user_id, moderator_user_id, callback)
				#  has to be user id -> use dedicated class
				if(settings.DEBUG): print(f'event sub follow with user {me_user.id}')
				# await self.event_sub.listen_channel_follow_v2(me_user.id, me_user.id, self.on_follow) # TODO : use API for different channel
				await self.event_sub_new.listen_channel_follow_v2(me_user.id, me_user.id, self.on_follow) # TODO : use API for different channel
				if(settings.DEBUG) : print('debug notifs : subbed for follows')
			if(sub_animation_set):
				if(settings.DEBUG): print(f'event sub subscribe')
				# await self.event_sub.listen_channel_subscribe(broadcaster_user_id=me_user.id, callback=self.on_eventsub_sub)
				await self.event_sub_new.listen_channel_subscribe(broadcaster_user_id=me_user.id, callback=self.on_eventsub_sub)
				if(settings.DEBUG) : print('debug notifs : subbed for subs')
				# print(self.event_sub)
				print(self.event_sub_new)


#### FINISH ####

	def terminate(self):
		if(hasattr(self,'event_sub_new') or hasattr(self,'event_sub')):
			async_to_sync(self.stop_event_sub)()
		if(hasattr(self,'chat')):
			self.chat.stop()
		if(settings.DEBUG) : print('NTW : stopped')


# # TODO not used anymore
# class TwitchChatError(Exception):
# 	def __init__(self,message):
# 		self.message = message
# 		super().__init__(message)
