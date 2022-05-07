from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse

import yaml
from django.utils import timezone
from django.conf import settings
import os

from .models import HomePage, TeamMember

# In a cloned deployment, you should use these views to customize the home page
# In an app deployment, on the poll app is installed to your preexisting main view

def index(request):
    team = TeamMember.objects.order_by('title')
    # i know some of you wll delete the homepage so i keep it permissive
    context = {'hpe': HomePage.objects.all()[0], 'team': team} 
    return render(request, 'home/index.html', context)

def darkmode(request):
    if(request.session.get('dark')):
        request.session['dark']= not request.session['dark']
    else:
        request.session['dark']=True
    return HttpResponse('welcome to the dark side')

def page(request,slug):
    page_obj = get_object_or_404(HomePage, name=slug)
    context = {'page': page_obj}
    return render(request, 'home/page.html', context)
