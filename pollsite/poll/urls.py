from django.urls import path

from . import views

app_name = 'poll'  # NOTE registering the namespace

urlpatterns = [
    # ex: /poll/
    path('', views.index, name='index'),
    path('<int:meeting_id>/meeting/', views.meeting, name='meeting'),
    path('<int:meeting_id>/meeting/create_qr/', views.qr_meeting, name='qr_meeting'),
    path('<int:meeting_id>/login/', views.login, name='login'),
    path('<int:meeting_id>/dashboard/', views.dashboard, name='dashboard'),
    path('<int:meeting_id>/chat/', views.chat, name='chatlog'),
    path('<int:meeting_id>/prompt/', views.prompt, name='prompt'),
    path('<int:meeting_id>/flag/<slug:flag_code>/', views.flag, name='flag'),
    path('<int:meeting_id>/flag_create_qr/<slug:flag_code>/', views.qr_flag, name='qr_flag'),
    path('<int:meeting_id>/alerts/', views.alerts, name='alerts'),
    path('<int:question_id>/results/', views.results, name='results'),
    path('twitch_auth/<int:twitch_api_id>/', views.twitch_auth, name='twitch_auth'),
    # path('webhook/<int:webhook_id>/', views.twitch_webhook, name='twitch_webhook'), # spécifier l'id du webhook dans l'URL
]
