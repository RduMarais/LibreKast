from . import views
from django.urls import path

urlpatterns = [
    path('', views.index, name='index'),
    path('dark', views.darkmode, name='darkmode'),
    path('home/<slug:slug>/', views.page, name='page'),
]
