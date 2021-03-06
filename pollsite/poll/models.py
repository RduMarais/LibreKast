from django.db import models
import datetime
import magic
import json
from django.utils import timezone
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder

from adminsortable.models import SortableMixin
from adminsortable.fields import SortableForeignKey

from markdownfield.models import MarkdownField, RenderedMarkdownField
from markdownfield.validators import VALIDATOR_CLASSY

QUESTION_TYPES = (
		('PL', _('Poll')),           # For questions to get the attendees' POV
		('TX', _('Text Only')),      # For text display before and after a question 
		('QZ', _('Quizz')),          # For questions that do have a correct answer
		('WC', _('Word Cloud')),     # For requesting inputs from attendees to make a word cloud diagram
	)
LIVE_TYPE = (
		('IRL',_('Physical Meeting')), 	# beekast-like meeting type
		('YT',_('Youtube Live Stream')), 	# Work in progress
		('TW',_('Twitch live')),			# TODO
		('MX',_('Twitch AND Youtube')),		# TODO
	)

def get_meeting_directory(instance, filename):
	return 'meetings/meeting_{0}/{1}'.format(instance.id, filename)

def get_bot_directory(instance, filename):
	return 'bots/bot_revolution_{0}/{1}'.format(instance.command, filename)

#### APIs

# For security purposes, the twitch API is stored as an object
class TwitchAPI(models.Model):
	name = models.CharField(_('Name of the API key'),max_length=20)
	description = models.TextField(_('Description of the API key'),max_length=400)
	oauth = models.CharField(_('OAuth Token'),max_length=30)
	client_id = models.CharField(_('Client ID'),max_length=30)
	client_secret = models.CharField(_('Client Secret'),max_length=30)

class YoutubeAPI(models.Model):
	name = models.CharField(_('Name of the API key'),max_length=20)
	description = models.TextField(_('Description of the API key'),max_length=400)
	client_id = models.CharField(_('OAuth Client ID'),max_length=90)
	client_secret = models.CharField(_('OAuth Client Secret'),max_length=40)
	authorized_credentials = models.TextField('This should not be accessed manually',max_length=1000,blank=True,default='')

##### MAIN APP LOGIC MODEL

# represents an occurence of a presentation. 
class Meeting(models.Model):
	title = models.CharField(_('Title of Meeting'), max_length=50)
	platform = models.CharField(_('Type of Meeting : IRL or live stream'),max_length=3,choices=LIVE_TYPE,default='IRL')
	desc = MarkdownField(_('Description'), max_length=200,rendered_field='desc_rendered', validator=VALIDATOR_CLASSY,blank=True)
	desc_rendered = RenderedMarkdownField()
	code = models.CharField(_('Security Code for joining the Meeting'), default='Pour1nf0', max_length=50)
	has_started = models.BooleanField(_('Meeting has started'),default=False)
	reward_fastest = models.BooleanField(_('Reward the fastest answers'),default=False)
	date_start = models.DateTimeField(_('Start time of the meeting'),default=timezone.now)
	date_end = models.DateTimeField(_('End time of the meeting'),default=timezone.now)
	image = models.ImageField(_('Image for your meeting'),null = True,blank=True,upload_to=get_meeting_directory)
	chat_log_size = models.IntegerField(_('Max chat messages to show'),default=8)
	obs_chat_log_size = models.IntegerField(_('Max chat messages for OBS'),default=12)
	stream_id = models.CharField(_('video stream ID for Youtube'),max_length=15,blank=True,null=True)
	channel_id = models.CharField(_('channel ID for Twitch'),max_length=15,blank=True,null=True)
	twitch_api = models.ForeignKey(TwitchAPI,on_delete=models.SET_NULL,null=True,blank=True)
	youtube_api = models.ForeignKey(YoutubeAPI,on_delete=models.SET_NULL,null=True,blank=True)
	_is_running = models.BooleanField('internal state',default=False)
	qrcode = models.ImageField(_('internal QR code'),null = True,blank=True,upload_to=get_meeting_directory)

	class Meta:
		verbose_name = _('Meeting')
		verbose_name_plural = _('Meetings')

	def __str__(self):
		return self.title

	def activities(self):
		return len(self.question_set.all())

	def activities_done(self):
		return len(self.question_set.filter(is_done=True))

	def participants(self):
		return len(self.attendee_set.all())

	def current_question(self):
		if(self.question_set.order_by('question_order').filter(is_done=False)):
			return self.question_set.order_by('question_order').filter(is_done=False)[0]
		else:
			MeetingEnd = Question(title=_('This meeting is over'),desc=_("Thanks for using LibreKast. Please feel free to check ![the author's website](https://www.pour-info.tech/)"),
				question_type='TX',is_done=False,meeting=self)
			return MeetingEnd



##### BOTS

class MessageBot(models.Model):
	command = models.CharField(_('command to trigger the message'),max_length=10) 
	message = models.CharField(_('Message to send when the command is sent'),max_length=150)
	is_active = models.BooleanField(_('is this command activated'))
	meeting = models.ForeignKey(Meeting,on_delete=models.SET_NULL,null=True)

class PeriodicBot(models.Model):
	name = models.CharField(_('short name for the message'),max_length=15) 
	message = models.CharField(_('Message to send regularly'),max_length=150)
	is_active = models.BooleanField(_('is this message activated'))
	meeting = models.ForeignKey(Meeting,on_delete=models.SET_NULL,null=True)

class RevolutionBot(models.Model):
	command = models.CharField(_('command to trigger the message'),max_length=15) 
	message = models.CharField(_('Message to send when the threshold is reached'),max_length=150)
	threshold_delay = models.IntegerField(_('Time window in seconds to send the command'),default=200)
	threshold_number = models.IntegerField(_('Number of commands to be sent'),default=5)
	is_active = models.BooleanField(_('is this command activated'),default=False)
	meeting = models.ForeignKey(Meeting,on_delete=models.SET_NULL,null=True)
	buffer = models.JSONField(_('internal state of the bot'),default=dict({'triggers':[],'last_revolution':''}),encoder=DjangoJSONEncoder)
	# i'd like to add a FileField but I need to validate it
	alert = models.FileField(_('Alert video to be displayed'),null=True,blank=True,upload_to=get_bot_directory)

	def clean(self):
		if(self.alert):
			file_type = magic.from_buffer(self.alert.open("rb").read(2048),mime=True)
			authorized_formats = ['video/mp4','video/quicktime','video/webm']
			if(file_type not in authorized_formats):
				raise ValidationError({'alert': "This file format is not allowed"})



##### IRL Meetings models

# model to hold the attendee's name 
#   (which allows to create a top and them to give themselves cool names)
# 	the model name is attendee in order not to confuse with django users 
class Attendee(models.Model):
	name = models.CharField(_('Your Name'), max_length=50, default='Anonymous')
	score = models.IntegerField(_('Score'),default=0)
	meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE)
	is_subscriber = models.BooleanField(_('Subscriber/sponsor'),default=False)
	is_twitch = models.BooleanField(_('is Twitch user'),default=False)
	is_youtube = models.BooleanField(_('is Youtube user'),default=False)

	class Meta:
		verbose_name = _('Participant')
		verbose_name_plural = _('Participants')
	
# model for all questions, whether they are Word Cloud, Polls, Quizzes or ony text.
# The different question types are defined as an attribute (question_type), and the relevant attributes are optional.
class Question(SortableMixin):
	title = models.CharField(_('Question'), max_length=200)
	desc = MarkdownField(_('Description'), max_length=800,rendered_field='desc_rendered', validator=VALIDATOR_CLASSY,blank=True)
	# this attribute is generated automatically as markdown render of previous field
	desc_rendered = RenderedMarkdownField()
	pub_date = models.DateTimeField(_('Date Published'),default=timezone.now)
	is_done = models.BooleanField(_('Question already completed'),default=False)
	question_type = models.CharField(_('Type of Question'), max_length=2,choices=QUESTION_TYPES, default='PL')
	meeting = SortableForeignKey(Meeting, on_delete=models.CASCADE)
	question_order = models.PositiveIntegerField(default=0, editable=False, db_index=True)

	# for quizzes
	first_correct_answer = models.BooleanField(_('No correct answers yet'),default=True)

	class Meta:
		ordering = ['question_order'] 
		verbose_name = _('Question')
		verbose_name_plural = _('Questions')

	def __str__(self):
		return self.title

	def recent(self):
		now = timezone.now()
		return now - datetime.timedelta(days=1) <= self.pub_date <= now

	def participants(self):  
		participants = 0
		choices = self.choice_set.all()
		for choice in choices:
			participants += choice.votes()
		return participants

	# by default, a qustion with no correct choice is a poll, 
	#   a question without choices is a word cloud.
	def save(self, *args, **kwargs):
		choices = self.choice_set.all()
		is_quizz=False
		for choice in choices:
			if(choice.isTrue):
				is_quizz = True
		if(is_quizz):
			self.question_type = "QZ"
		super(Question, self).save(*args, **kwargs)

	recent.admin_order_field = 'pub_date'
	recent.boolean = True

# for Polls & Quizzes, choices are written by the admin.
#   for Word clouds, choices are user input
class Choice(models.Model):
	question = models.ForeignKey(Question, on_delete=models.CASCADE)
	choice_text = models.CharField(max_length=200)
	slug = models.CharField(_('(For Youtube live) shorter text the participants can type to vote'),max_length=20,blank=True)
	isTrue = models.BooleanField(default=False)

	class Meta:
		verbose_name = _('Choice')
		verbose_name_plural = _('Choices')

	def __str__(self):
		return self.choice_text

	def votes(self):
		return len(self.vote_set.all())


# model to define many-to-many relationship between choices and Attendees
class Vote(models.Model):
	choice = models.ForeignKey(Choice,on_delete=models.CASCADE)
	user = models.ForeignKey(Attendee,on_delete=models.CASCADE)



