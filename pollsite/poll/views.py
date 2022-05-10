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

from .models import Choice, Question, Meeting,Attendee,Vote
from .forms import WordForm,LoginForm

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
	# wss=settings.SOCKET_ENCRYPTION
	return render(request,'poll/dashboard.html',{'meeting':meeting,'attendees':attendees})

# TODO this page is not protected, for simplicity. But the data shown here are actually public on YT and Twitch
def chat(request,meeting_id):
	meeting = get_object_or_404(Meeting, pk=meeting_id)
	# wss=settings.SOCKET_ENCRYPTION
	return render(request,'poll/chatlog.html',{'meeting':meeting})

def alerts(request,meeting_id):
	meeting = get_object_or_404(Meeting, pk=meeting_id)
	# wss=settings.SOCKET_ENCRYPTION
	return render(request,'poll/alerts.html',{'meeting':meeting})

def qr(request,meeting_id):
	meeting = get_object_or_404(Meeting, pk=meeting_id)
	if(not meeting.qrcode):
		print('debug : creating qr code')
		img = qrcode.make(request.build_absolute_uri(reverse('poll:meeting',args=('1',))))
		blob = BytesIO()
		img.save(blob, 'JPEG') # because we dont want to handle folder existence/creation so we dont save it on disk
		meeting.qrcode.save(f'meeting_{meeting_id}_qrcode.png', File(blob), save=True)
		print('debug : file created')
	return HttpResponse(meeting.qrcode.url)


# Once you enter a meeting, this is the page displaying the current question and previous results
def meeting(request, meeting_id):
	meeting = get_object_or_404(Meeting, pk=meeting_id)
	if(not 'attendee_id' in request.session): # if attendee is not logged in yet
		form = LoginForm()
		return render(request,'poll/login.html',{'meeting':meeting,'form':form})
	else:
		attendee = Attendee.objects.get(pk=request.session['attendee_id'])
		context = {
			'meeting':meeting,
			'attendee':attendee,
			'current_question': meeting.current_question(),
			'previous_question_list': meeting.question_set.filter(is_done=True).order_by('question_order'),
			# 'wss':settings.SOCKET_ENCRYPTION 
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


