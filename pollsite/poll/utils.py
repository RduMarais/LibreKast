import time
import threading
import openai
import pyttsx3

from django.conf import settings
from .models import Meeting,Attendee,Flag,FlagAttempt


def validate_flag_attempt(meeting,attendee,attempted_code):
	error = None
	flag_attempt = None
	if(attempted_code.startswith(meeting.flags_prefix+'{') and attempted_code.endswith('}')):
		prefix_length = len(meeting.flags_prefix)
		attempted_code = attempted_code[prefix_length+1:-1]
	if(settings.DEBUG) : print(f'debug : flag searched : {attempted_code}')
	try:
		flag_attempt = FlagAttempt(code=attempted_code,user=attendee)
		flag = meeting.flag_set.get(code=attempted_code)
		# check if user has already flagged
		if( attendee.flagattempt_set.filter(correct_flag=flag)):
			error = 'already flagged'
		else:
			flag_attempt.correct_flag = flag
			attendee.score = attendee.score + flag.points
			# check if someone flagged before
			if(not flag.flagattempt_set.all()):
				attendee.score = attendee.score + flag.first_blood_reward
				flag_attempt.is_first_blood = True
			attendee.save()
		flag_attempt.save()
	except Flag.DoesNotExist:
		error = 'not found'
	return (flag_attempt,error)


# This class only serves the purpose of having a different threading class for polling to send bot messages
class TwitchBotPoller(threading.Thread):
	twitchHandler = None

	def __init__(self,twitchHandler,is_daemon: bool):
		super(TwitchBotPoller, self).__init__(daemon=is_daemon)
		self.twitchHandler = twitchHandler
		self.time_iterator = 0
		self.periodic_bot_iterator = 0
		self._is_polling_for_bots = True
		if(settings.DEBUG): print('debug : twitch bot polling set up')


	# start a thread who regularly sends messages based on self.meetingConsumer.
	def poll_for_periodic_bots(self):
		self.time_iterator = (self.time_iterator + 1) % 3600 # this is a counter
		if(self.time_iterator % self.twitchHandler.meetingConsumer.meeting.periodic_bot_delay == 0): # every periodic_bot_delay seconds, do 
			bot_message = self.twitchHandler.meetingConsumer.get_periodic_bot(self.periodic_bot_iterator)
			if(settings.DEBUG): print(f'debug : twitch sending message {bot_message}')
			self.twitchHandler.send_message(bot_message)
			# twitch api is overall more stable than Youtube so if meeting is mixed we print twitch messages, not Youtubes
			self.twitchHandler.print_message({'author':settings.TWITCH_NICKNAME,'text':bot_message,'source':'b'})
			# iterate over the periodic bots
			self.periodic_bot_iterator = (self.periodic_bot_iterator + 1) % len(self.twitchHandler.meetingConsumer.meeting.periodicbot_set.filter(is_active=True))
			if(settings.DEBUG): print('debug : twitch bot sent')


	def run(self):
		if(settings.DEBUG): print('debug : twitch bot polling started')
		while(self._is_polling_for_bots):
			self.poll_for_periodic_bots()
			time.sleep(1)
			# if(settings.DEBUG): print('debug : twitch bot polling')
		if(settings.DEBUG): print('debug : twitch bot polling stopped')


	def terminate(self):
		self._is_polling_for_bots = False
		if(settings.DEBUG): print('debug : twitch bot polling stopping')


''' Est ce que j'essaie de faire un truc compliant avec l'API des Revolution bots ?
	* soit je regènère une conversation à chaque fois avec le init et je garde un statut ici
	* soit je génère une seule fois le bot et il suit les différents messages
	* soit je crée une classe à part de buffer de bot révolution et je la réutilise ici
		 * un object buffer = {
			triggers : []
			last_revolution : ''
		 }
		 et j'aurais un array de revolution_buffers ? 
'''

class ChatGPTHandler():
	command = 'chatgpt'
	MODEL_ENGINE = "text-davinci-003"

	def __init__(self,meeting):
		openai.api_key = meeting.chatgptprofile.key
		self.engine = pyttsx3.init()
		self.buffer = {'triggers':[],'last_revolution':''}
		self.conversation_history = meeting.chatgptprofile.initial_prompt+'\n'
		engine.setProperty('voice','com.apple.speech.synthesis.voice.amelie.premium')

	def get_text_to_file(self,text,filename):
		engine.save_to_file(text , f'{filename}.mp3')
		engine.runAndWait()

	"""Returns the response for the given prompt using the OpenAI API."""
	def get_response(prompt):
		completions = openai.Completion.create(
				engine = MODEL_ENGINE,
				prompt = prompt,
			 max_tokens = 1024,
			temperature = 0.7,
		)
		return completions.choices[0].text

	"""Updates the conversation history and generates a response using GPT-3."""
	def handle_input(input_str : str, conversation_history : str, USERNAME : str, AI_NAME : str):
		# Update the conversation history
		conversation_history += f"{USERNAME}: {input_str}\n"
	   
		# Generate a response using GPT-3
		message = self.get_response(conversation_history)[1:]

		# Update the conversation history
		conversation_history += f"{AI_NAME}: {message}\n"

		# Print the response
		print(f'debug : ChatGPT{AI_NAME}: {message}')

		try:
			self.get_text_to_file(message,'test.mp3')
		except:
			print('error')

		return conversation_history

