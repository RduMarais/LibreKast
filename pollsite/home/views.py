from django.shortcuts import render, get_object_or_404
from .models import TeamMember

import yaml
from django.utils import timezone
from django.conf import settings
import os

from .models import HomePage

# In a cloned deployment, you should use these views to customize the home page
# In an app deployment, on the poll app is installed to your preexisting main view

def index(request):
    team = TeamMember.objects.order_by('title')
    # i know some of you wll delete the homepage so i keep it permissive
    context = {'hpe': HomePage.objects.all()[0], 'team': team} 
    return render(request, 'home/index', context)
