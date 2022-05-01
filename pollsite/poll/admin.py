from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db import models
from django.utils import timezone
from django.conf import settings

from adminsortable.admin import NonSortableParentAdmin, SortableStackedInline

from .models import Question,Choice,Meeting,Attendee
from .models import Vote,TwitchAPI,MessageBot,YoutubeAPI,PeriodicBot

# administration of choices once in Question admin panel
class ChoiceInline(admin.TabularInline):
	model = Choice
	extra = 1
	readonly_fields = ['votes']

# Question admin panel
class QuestionAdmin(admin.ModelAdmin):
	fieldsets = [
		(None, {'fields': ['question_type','is_done','meeting']}),
		('Question Information', {'fields': ['title', 'desc']}),
		('Date Information', {'fields': ['pub_date']}),
	]
	inlines = [ChoiceInline]
	list_display = ('title', 'question_type','is_done', 'get_meeting', 'participants') 
	list_editable = ('is_done',)
	search_fields = ['title','description']

	def get_meeting(self,obj):
		link=reverse("admin:poll_meeting_change", args=[obj.meeting.id])
		return format_html('<a href="%s">%s</a>' % (link,obj.meeting.title))

# Question choices once in the meeting admin panel
#   this view extends the SortableStackedLine type to have the questions sortable
class QuestionsOrder(SortableStackedInline):
	model = Question
	extra = 0
	fields = (('is_done','question_type'))
	readonly_fields = ['question_type']
	show_change_link = True
	classes = ['collapse']


# Meeting admin panel
class MeetingAdmin(NonSortableParentAdmin):
	fieldsets = [
		(None, {'fields': ['participants','date_start','date_end','platform']}),
		('Meeting informations', {'fields': ['title','desc','image']}),
		('Parameters',{'fields':['code','reward_fastest']}),
		('Live Stream only',{'fields':['chat_log_size','obs_chat_log_size','stream_id',
			'channel_id','twitch_api','youtube_api']})
	]
	# if(obj.platform == 'YT'):
	# 	fieldsets[2][1]['fields'].append('stream_url')
	readonly_fields =['participants','is_ongoing']
	inlines = [QuestionsOrder]
	list_display = ('title', 'activities','participants','is_ongoing','platform')
	search_fields = ['title','description']

	def is_ongoing(self,obj):
		if(obj.date_start <= timezone.now() and obj.date_end >= timezone.now()):
			link=reverse("poll:dashboard", args=[obj.id])
			return format_html('Ongoing | <button type="submit" formaction="%s">MEETING DASHBOARD</button>' % link)
		elif(obj.date_end <= timezone.now()):
			return 'Past Meeting'
		elif(obj.date_start >= timezone.now()):
			return 'Future Meeting'
		else:
			return 'Schedule Error'

# Attendee score table
class ScoreBoard(admin.ModelAdmin):
	# name = 'Leader Board'
	# verbose_name = 'Score Table'
	list_display = ('name', 'score','get_meeting','is_subscriber') 
	fields = ['name','score']
	readonly_fields =['name', 'score','meeting','is_subscriber']
	list_filter=('meeting','is_subscriber')
	ordering = ('-score',)

	def __str__(self):
		 return "Leader Board"

	def get_meeting(self,obj):
		link=reverse("admin:poll_meeting_change", args=[obj.meeting.id])
		return format_html('<a href="%s">%s</a>' % (link,obj.meeting.title))

class VoteAdmin(admin.ModelAdmin):
	readonly_fields =['choice', 'user']
	list_display =('choice', 'get_user','get_question')

	def get_question(self,obj):
		return obj.choice.question

	def get_user(self,obj):
		if(obj.user.is_twitch):
			return 'T: '+obj.user.name
		if(obj.user.is_youtube):
			return 'Y: '+obj.user.name
		else:
			return obj.user.name

class TwitchAPIAdmin(admin.ModelAdmin):
	list_display = ('name','description')

class YTAPIAdmin(admin.ModelAdmin):
	# readonly_fields =['authorized_credentials']
	exclude = ('authorized_credentials',)
	list_display = ('name','description')

class MsgBotAdmin(admin.ModelAdmin):
	list_display =('command','is_active','meeting')
	list_editable = ('is_active',)

class PeriodBotAdmin(admin.ModelAdmin):
	list_display =('name','is_active','meeting')
	list_editable = ('is_active',)

admin.site.register(Question, QuestionAdmin)
admin.site.register(Meeting, MeetingAdmin)
admin.site.register(Attendee, ScoreBoard)
admin.site.register(Vote, VoteAdmin) # for debug
admin.site.register(TwitchAPI,TwitchAPIAdmin)
admin.site.register(YoutubeAPI,YTAPIAdmin)
admin.site.register(MessageBot,MsgBotAdmin)
admin.site.register(PeriodicBot,PeriodBotAdmin)
