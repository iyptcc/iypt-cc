from django import forms
from django.conf.urls import include, url

from .views import GenerateView, show, view

app_name='schedule'

urlpatterns = [
    #url(r'^', include('django.contrib.auth.urls')),
    url(r'^$', view ,name="list" ),
    url(r'^view/(?P<id>\d+)$', show ,name="show" ),
    url(r'^generate/$', GenerateView.as_view() ,name="generate" ),
]
