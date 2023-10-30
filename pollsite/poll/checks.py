import requests
from .models import Meeting

# preliminary check performed on site start to clean all meetings in case of a failure
def check_meetings_clean_stop():
	for m in Meeting.objects.all():
		if(m._is_running):
			m._is_running = False
			m.save()


