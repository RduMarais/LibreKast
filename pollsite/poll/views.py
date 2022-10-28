from django.http import HttpResponseRedirect,HttpResponse, request
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.core.files.storage import get_storage_class
from django.core.files import File

import datetime
import qrcode
from io import BytesIO

from .models import Choice,Question,Meeting,Attendee,Vote,Flag,FlagAttempt
from .forms import WordForm,LoginForm
from .utils import validate_flag_attempt

def get_previous_user_answers(attendee,question):
	query = Q(user=attendee)
	query.add(Q(choice__question__title__contains=question.title),Q.AND)
	return Vote.objects.filter(query)


# Index view with all current meetings
def index(request):
	# Gets all meetings happening now (defined with Start time and End Time)
	meetings_list = Meeting.objects.filter(Q(date_start__lte=timezone.now()) & Q(date_end__gte=timezone.now()))
	context = {'meetings':meetings_list }
	return render(request, 'poll/index.html', context)

# custom view to manage current meetings
@staff_member_required
def dashboard(request,meeting_id):
	meeting = get_object_or_404(Meeting, pk=meeting_id)
	attendees = meeting.attendee_set.all().order_by('-score')
	return render(request,'poll/dashboard.html',{'meeting':meeting,'attendees':attendees})

# Standalone view with chat log for streaming software such as OBS
# this page is not protected, for simplicity (the data shown here are actually public on YT and Twitch)
def chat(request,meeting_id):
	meeting = get_object_or_404(Meeting, pk=meeting_id)
	return render(request,'poll/chatlog.html',{'meeting':meeting})

# Standalone view for QRcode flag
# TODO : make this add points to the participant
def flag(request,meeting_id,flag_code):
	meeting = get_object_or_404(Meeting, pk=meeting_id)
	if(not 'attendee_id' in request.session):
		form = LoginForm()
		# TODO : redirect after
		return render(request,'poll/login.html',{'meeting':meeting,'form':form})

	flag_attempt = None
	error = None
	try:
		attendee = meeting.attendee_set.get(pk=request.session['attendee_id'])
	except Attendee.DoesNotExist:
		error = 'other meeting'
	else:
		(flag_attempt,error) = validate_flag_attempt(meeting,attendee,flag_code)
	return render(request,'poll/flag.html',{'meeting':meeting,'flagAttempt':flag_attempt,'error':error})

# Standalone view with chat alerts for streaming software such as OBS
def alerts(request,meeting_id):
	meeting = get_object_or_404(Meeting, pk=meeting_id)
	return render(request,'poll/alerts.html',{'meeting':meeting})

# Standalone view with chat alerts for teleprompt tablets (with text inverted)
def prompt(request,meeting_id):
	meeting = get_object_or_404(Meeting, pk=meeting_id)
	return render(request,'poll/chatlog.html',{'meeting':meeting})

# Create a QR code picture for a specific meeting
def qr_meeting(request,meeting_id):
	meeting = get_object_or_404(Meeting, pk=meeting_id)
	if(not meeting.qrcode):
		# 'make' creates the code from a string
		# 'reverse' returns the relative url for the view poll with meeting 1
		img = qrcode.make(request.build_absolute_uri(reverse('poll:meeting',args=(meeting.id,))))
		blob = BytesIO()
		img.save(blob, 'JPEG') # because we dont want to handle folder existence/creation so we dont save it on disk
		meeting.qrcode.save(f'meeting_{meeting_id}_qrcode.png', File(blob), save=True)
	return HttpResponseRedirect(meeting.qrcode.url)

# Create a QR code picture for a specific flag
def qr_flag(request,meeting_id,flag_code):
	meeting = get_object_or_404(Meeting, pk=meeting_id)
	try:
		flag = meeting.flag_set.get(code=flag_code)
		if(not flag.qrcode):
			# 'make' creates the code from a string
			# 'reverse' returns the relative url for the view poll with meeting 1
			img = qrcode.make(request.build_absolute_uri(reverse('poll:flag',args=(meeting_id,flag.code))))
			blob = BytesIO()
			# because we dont want to handle folder existence/creation so we dont save it on disk
			img.save(blob, 'JPEG') 
			flag.qrcode.save(f'meeting_{meeting_id}_flag_{flag.code}_qrcode.png', File(blob), save=True)
		return HttpResponseRedirect(flag.qrcode.url)
	except:
		return HttpResponse("not ok")


# Once you enter a meeting, this is the page displaying the current question and previous results
def meeting(request, meeting_id):
	meeting = get_object_or_404(Meeting, pk=meeting_id)
	if(request.user.is_authenticated):
		if(not 'attendee_id' in request.session): # if staff member is not logged in yet
			try:
				# a user already exists, just link this user to the session
				attendee = Attendee.objects.get(name=request.user.username)
				request.session['attendee_id'] = attendee.id
			except Attendee.DoesNotExist:
				# create user if user is from staff 
				new_attendee = Attendee(name=request.user.username,meeting=meeting,score=0)
				new_attendee.save()
				request.session['attendee_id'] = new_attendee.id
	if(not 'attendee_id' in request.session): # if attendee is not logged in yet
		form = LoginForm()
		return render(request,'poll/login.html',{'meeting':meeting,'form':form})
	else:
		try:
			attendee = Attendee.objects.get(pk=request.session['attendee_id'])
		# TODO : need better error messages
		except Attendee.DoesNotExist:
			form = LoginForm()
			return render(request,'poll/login.html',{'meeting':meeting,'form':form,'error':_("User not found. Staff user need to join meeting")})
		context = {
			'meeting':meeting,
			'attendee':attendee,
			'current_question': meeting.current_question(),
			'previous_question_list': meeting.question_set.filter(is_done=True).order_by('question_order'),
		}
		return render(request, 'poll/meeting.html', context)

def login(request,meeting_id):
	meeting = get_object_or_404(Meeting, pk=meeting_id)
	if(not 'attendee_id' in request.session): # if attendee is not logged in yet
		if(request.method=='POST'):
			form = LoginForm(request.POST)
			if(form.is_valid()):
				if(form.cleaned_data['meeting_code'] == meeting.code):
					new_attendee = Attendee(name=form.cleaned_data['username'],meeting=meeting,score=0)
					new_attendee.save()
					request.session['attendee_id'] = new_attendee.id
					return HttpResponseRedirect(reverse('poll:meeting', args=(meeting.id,)))
				else:
					context = {'meeting':meeting,'error':_("The meeting code is not valid"),'form':LoginForm()}
					return render(request,'poll/login.html',context)
			else:
				context = {'meeting':meeting,'error':_("Something went wrong"),'form':LoginForm()}
				return render(request,'poll/login.html',context)
		else:
			return render(request,'poll/login.html',{'meeting':meeting})
	else:
		return HttpResponseRedirect(reverse('poll:meeting', args=(meeting.id,)))



# return view for Polls and Quizz
def results(request, question_id):
	if(not 'attendee_id' in request.session):
		form = LoginForm()
		return render(request,'poll/login.html',{'meeting':meeting,'form':form})
	else:
		question = get_object_or_404(Question, pk=question_id)
		attendee = Attendee.objects.get(pk=request.session['attendee_id'])
		return render(request, 'poll/results.html', {'question': question})


