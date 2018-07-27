from django import forms
from django.conf.urls import include, url

from .views import AddTemplate, EditTemplate, ListTemplates, ListTemplateVersions

app_name = 'postoffice'

urlpatterns = [
    #url(r'^', include('django.contrib.auth.urls')),
    url(r'^templates', ListTemplates.as_view(), name="templates"),
    url(r'^template/add$', AddTemplate.as_view(), name="template_add"),
    url(r'^template/(?P<id>.+)/versions$', ListTemplateVersions.as_view(), name="template_versions"),
    url(r'^template/(?P<id>.+)$', EditTemplate.as_view(), name="template_edit"),
]
