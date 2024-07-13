from django import forms
from django.urls import path, re_path

from .views import AddTemplate, EditTemplate, ListTemplates, ListTemplateVersions

app_name = "postoffice"

urlpatterns = [
    # url(r'^', include('django.contrib.auth.urls')),
    re_path(r"^templates", ListTemplates.as_view(), name="templates"),
    path("template/add", AddTemplate.as_view(), name="template_add"),
    path(
        "template/<path:id>/versions",
        ListTemplateVersions.as_view(),
        name="template_versions",
    ),
    path("template/<path:id>", EditTemplate.as_view(), name="template_edit"),
]
