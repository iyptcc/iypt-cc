from django import forms
from django.urls import path

from .views import GenerateView, show, view

app_name = "schedule"

urlpatterns = [
    # url(r'^', include('django.contrib.auth.urls')),
    path("", view, name="list"),
    path("view/<int:id>", show, name="show"),
    path("generate/", GenerateView.as_view(), name="generate"),
]
