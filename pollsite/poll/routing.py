# chat/routing.py
from django.urls import re_path, path

from . import consumers

websocket_urlpatterns = [
    # path('ws/<int:question_id>', consumers.QuestionConsumer.as_asgi()),
    re_path(r'ws/(?P<meeting_id>\d+)/$', consumers.MeetingConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<meeting_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
]