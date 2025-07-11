from django import forms
from django.urls import path

from .views import GenerateView, ImportView, show, view

app_name = "schedule"

urlpatterns = [
    # url(r'^', include('django.contrib.auth.urls')),
    path("", view, name="list"),
    path("view/<int:id>", show, name="show"),
    path("import", ImportView.as_view(), name="import"),
    path("generate/", GenerateView.as_view(), name="generate"),
]
