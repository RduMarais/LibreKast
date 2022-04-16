from django.urls import path

from . import views

app_name = 'poll'  # NOTE registering the namespace

urlpatterns = [
    # ex: /poll/
    path('', views.index, name='index'),
    path('<int:meeting_id>/meeting/', views.meeting, name='meeting'),
    path('<int:meeting_id>/login/', views.login, name='login'),
    path('<int:meeting_id>/dashboard/', views.dashboard, name='dashboard'),
    path('<int:meeting_id>/chat/', views.chat, name='chatlog'),
    path('<int:question_id>/results/', views.results, name='results'),
]
