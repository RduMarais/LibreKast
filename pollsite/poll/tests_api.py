import datetime

from unittest import TestCase
from django.utils import timezone
from channels.testing import WebsocketCommunicator

from .models import Question, Choice, Meeting, TwitchAPI, YoutubeAPI
from .consumers import MeetingConsumer
from .twitch_handler import TwitchHandler
from .youtube_handler import YoutubeHandler

class APITestCase(TestCase):

    def setup(self):
        tw_test_apis = TwitchAPI.objects.filter(name__contains="[test]")
        yt_test_apis = YoutubeAPI.objects.filter(name__contains="[test]")
        test_meetings = Meeting.objects.filter(title__contains="[test]")
        tw_api = tw_test_apis[0]
        yt_api = yt_test_apis[0]
        test_meeting = test_meetings[0]
        return (tw_api, yt_api, test_meeting)

    def start_meeting_consumer(self,meetingConsumer : MeetingConsumer):
        meetingConsumer.meeting._is_running = True
        meetingConsumer.meeting.save()

    def stop_meeting_consumer(self,meetingConsumer : MeetingConsumer):
        meetingConsumer.meeting._is_running = False
        meetingConsumer.meeting.save()

    def test_setUp(self):

        tw_test_apis = TwitchAPI.objects.filter(name__contains="[test]")
        yt_test_apis = YoutubeAPI.objects.filter(name__contains="[test]")
        test_meetings = Meeting.objects.filter(title__contains="[test]")
        self.assertEqual(len(tw_test_apis),1)
        self.assertEqual(len(yt_test_apis),1)
        self.assertEqual(len(test_meetings),1)
        self.assertEqual(test_meetings[0].platform,'MX')

    def test_connexion_Twitch(self):
        (tw_api, yt_api, test_meeting) = self.setup()

        testMeetingConsumer = MeetingConsumer()
        testMeetingConsumer.meeting = test_meeting
        testMeetingConsumer.meeting_group_name = 'meeting_'+str(test_meeting.id)
        
        self.start_meeting_consumer(testMeetingConsumer)

        testTwitchHandler = TwitchHandler(test_meeting.channel_id,tw_api,testMeetingConsumer)
        self.stop_meeting_consumer(testMeetingConsumer)
        # communicator = WebsocketCommunicator(AConsumer(), "/testws/")

        # DOESNT TERMINATE