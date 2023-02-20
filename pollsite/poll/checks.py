import requests
from .models import Meeting,TwitchWebhook


def check_meetings_clean_stop():
	for m in Meeting.objects.all():
		if(m._is_running):
			m._is_running = False
			m.save()


def unsubscribe_webhook(self,tw_webhook):
	print(f'unsub : webhook name : {tw_webhook.name}')
	webhook_url = f"https://api.twitch.tv/helix/eventsub/subscriptions?id={tw_webhook.helix_id}"
	headers = {
		"Authorization" : self.helix.api.bearer_token,
		"Client-Id" :self.helix.api.client_id,
		"Content-Type" :"application/json",
	}
	response = requests.request(method='DELETE', url=webhook_url,headers=headers) 
	if(response.status_code >=200 and response.status_code <300):
		tw_webhook.helix_id = ""
		tw_webhook.save()

def check_twitch_webhook_subscriptions():
	for tw_webhook in TwitchWebhook.objects.filter(helix_id__exact=''):
		print(f'debug : subscription {tw_webhook.name} to be cleared')
	pass