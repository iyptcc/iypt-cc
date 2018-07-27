from django import forms
from django.conf.urls import include, url

from .preview import PdfsPreview
from .views import (AddTemplate, EditTemplate, FileView, ListTemplates, ListTemplateVersions, PdfUpload, TagChange,
                    TagCreate, TagDelete, TagView, view_error, view_render_error)

app_name='printer'

urlpatterns = [
    #url(r'^', include('django.contrib.auth.urls')),
    url(r'^list', PdfsPreview(forms.Form), name="list"),
    url(r'^file/(?P<name>.+)$', FileView.as_view(), name="file"),
    url(r'^error/(?P<id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$', view_error ,name="tex_error" ),
    url(r'^render_error/(?P<id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$', view_render_error ,name="tex_render_error" ),
    url(r'^upload', PdfUpload.as_view(), name="upload"),
    url(r'^templates', ListTemplates.as_view(), name="templates"),
    url(r'^template/add$', AddTemplate.as_view(), name="template_add"),
    url(r'^template/(?P<id>.+)/versions$', ListTemplateVersions.as_view(), name="template_versions"),
    url(r'^template/(?P<id>.+)$', EditTemplate.as_view(), name="template_edit"),
    url(r'^tag/$', TagView.as_view() ,name="tags" ),
    url(r'^tag/edit/(?P<id>\d+)/$', TagChange.as_view(), name="change_tag"),
    url(r'^tag/delete/(?P<id>\d+)/$', TagDelete.as_view(), name="delete_tag"),
    url(r'^tag/create/$', TagCreate.as_view(), name="create_tag"),
]
