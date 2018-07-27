from django import forms
from django.conf.urls import include, url

from .views import help, info, tos

app_name='about'

urlpatterns = [
    #url(r'^', include('django.contrib.auth.urls')),
    url(r'^info$', info ,name="info" ),
    url(r'^tos$', tos ,name="tos" ),
    url(r'^', help, name="help")
]
