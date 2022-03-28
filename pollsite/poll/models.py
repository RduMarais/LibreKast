from django.db import models
import datetime
from django.utils import timezone
from django.core.exceptions import ValidationError

from adminsortable.models import SortableMixin
from adminsortable.fields import SortableForeignKey

from markdownfield.models import MarkdownField, RenderedMarkdownField
from markdownfield.validators import VALIDATOR_CLASSY

QUESTION_TYPES = (
		('PL', 'Poll'),           # For questions to get the attendees' POV
		('TX', 'Text Only'),      # For text display before and after a question 
		('QZ', 'Quizz'),          # For questions that do have a correct answer
		('WC', 'Word Cloud'),     # For requesting inputs from attendees to make a word cloud diagram
	)
LIVE_TYPE = (
		('IRL','Physical Meeting'), 	# beekast-like meeting type
		('YT','Youtube Live Stream'), 	# Work in progress
		('TW','Twitch live'),			# TODO
	)


# represents an occurence of a presentation. 
class Meeting(models.Model):
	title = models.CharField('Title of Meeting', max_length=50)
	platform = models.CharField('Type of Meeting : IRL or live stream',max_length=3,choices=LIVE_TYPE,default='IRL')
	desc = MarkdownField('Description', max_length=200,rendered_field='desc_rendered', validator=VALIDATOR_CLASSY,blank=True)
	desc_rendered = RenderedMarkdownField()
	code = models.CharField('Security Code for joining the Meeting', default='Pour1nf0', max_length=50)
	has_started = models.BooleanField('Meeting has started',default=False)
	reward_fastest = models.BooleanField('Reward the fastest answers',default=False)
	date_start = models.DateTimeField('Start time of the meeting',default=timezone.now)
	date_end = models.DateTimeField('End time of the meeting',default=timezone.now)
	image = models.ImageField('Image for your meeting',null = True,blank=True)
	stream_url = models.URLField('URL for Youtube live stream (only if platform is Youtube)',null=True,blank=True)

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
			MeetingEnd = Question(title='This meeting is over',desc="Thanks for using LibreKast. Please feel free to check ![the author's website](https://www.pour-info.tech/)",
				question_type='TX',is_done=False,meeting=self)
			return MeetingEnd


# model to hold the attendee's name 
#   (which allows to create a top and them to give themselves cool names)
# 	the model name is attendee in order not to confuse with django users 
class Attendee(models.Model):
	name = models.CharField('Your Name', max_length=50, default='Anonymous')
	score = models.IntegerField('Score',default=0)
	meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE)
	
# model for all questions, whether they are Word Cloud, Polls, Quizzes or ony text.
# The different question types are defined as an attribute (question_type), and the relevant attributes are optional.
class Question(SortableMixin):
	title = models.CharField('Question', max_length=50)
	desc = MarkdownField('Description', max_length=800,rendered_field='desc_rendered', validator=VALIDATOR_CLASSY)
	# this attribute is generated automatically as markdown render of previous field
	desc_rendered = RenderedMarkdownField()
	pub_date = models.DateTimeField('Date Published',default=timezone.now)
	is_done = models.BooleanField('Question already completed',default=False)
	question_type = models.CharField('Type of Question', max_length=2,choices=QUESTION_TYPES, default='PL')
	meeting = SortableForeignKey(Meeting, on_delete=models.CASCADE)
	question_order = models.PositiveIntegerField(default=0, editable=False, db_index=True)

	# for quizzes
	first_correct_answer = models.BooleanField('True if no one gave the correct answer already',default=True)

	class Meta:
		ordering = ['question_order'] 

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
		# if(len(choices)==0):
		# 	self.question_type = "WC"
		for choice in choices:
			if(choice.isTrue):
				is_quizz = True
		if(is_quizz):
			self.question_type = "QZ"
		super(Question, self).save(*args, **kwargs)

	# def clean(self):
	# 	self.clean_fields()
	# 	choices = self.choice_set.all()
	# 	print(choices)
	# 	# if(self.question_type=='TX' and len(choices)!=0):
	# 	# 	raise ValidationError('Question type is `Text Only` but there are choices defined')
	# 	# if(self.question_type=='PL' and len(choices)<=0):
	# 	# 	raise ValidationError('Question type is `Poll` but there are no choices defined')
	# 	# if(self.question_type=='QZ' and len(choices)<=0):
	# 	# 	raise ValidationError('Question type is `Quizz` but there are no choices defined')
	# 	if(self.question_type=='QZ' and len(self.choice_set.filter(isTrue=True))==0):
	# 		raise ValidationError('Question type is `Quizz` but there is no correct answer defined')
	# 	if(self.question_type=='PL' and len(self.choice_set.filter(isTrue=True))!=0):
	# 		raise ValidationError('Question type is `Poll` but there are correct answers defined')

	recent.admin_order_field = 'pub_date'
	recent.boolean = True

# for Polls & Quizzes, choices are written by the admin.
#   for Word clouds, choices are user input
class Choice(models.Model):
	question = models.ForeignKey(Question, on_delete=models.CASCADE)
	choice_text = models.CharField(max_length=100)
	# votes = models.IntegerField(default=0)
	isTrue = models.BooleanField(default=False)

	def __str__(self):
		return self.choice_text

	def votes(self):
		return len(self.vote_set.all())


# model to define many-to-many relationship between choices and Attendees
class Vote(models.Model):
	choice = models.ForeignKey(Choice,on_delete=models.CASCADE)
	user = models.ForeignKey(Attendee,on_delete=models.CASCADE)
