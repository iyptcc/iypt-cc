from django import forms
from django.urls import path, re_path

from .preview import PdfListPreview
from .views import (
    AddTemplate,
    EditTemplate,
    FileView,
    ListTemplates,
    ListTemplateVersions,
    PdfImport,
    PdfUpload,
    TagChange,
    TagCreate,
    TagDelete,
    TagView,
    view_error,
    view_render_error,
)

app_name = "printer"

urlpatterns = [
    # url(r'^', include('django.contrib.auth.urls')),
    path("list", PdfListPreview(forms.Form), name="list"),
    path("file/<path:name>", FileView.as_view(), name="file"),
    path("error/<uuid:id>", view_error, name="tex_error"),
    path("render_error/<uuid:id>", view_render_error, name="tex_render_error"),
    re_path(r"^upload", PdfUpload.as_view(), name="upload"),
    re_path(r"^templates", ListTemplates.as_view(), name="templates"),
    path("template/add", AddTemplate.as_view(), name="template_add"),
    path(
        "template/<path:id>/versions",
        ListTemplateVersions.as_view(),
        name="template_versions",
    ),
    path("template/<path:id>", EditTemplate.as_view(), name="template_edit"),
    path("fileserver/<int:id>", PdfImport.as_view(), name="fileserver_list"),
    path("tag/", TagView.as_view(), name="tags"),
    path("tag/edit/<int:id>/", TagChange.as_view(), name="change_tag"),
    path("tag/delete/<int:id>/", TagDelete.as_view(), name="delete_tag"),
    path("tag/create/", TagCreate.as_view(), name="create_tag"),
]
