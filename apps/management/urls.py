from django import forms
from django.conf.urls import url

from .preview import UserPreview
from .views import (FeedbackDeleteView, FeedbackView, ProfileDataView, ScreenshotView, SetPassword, SystemInfo,
                    TournamentCreate, TournamentDelete, TournamentView, UDChange, UDCreate, UDDelete, UDMove,
                    UserCreate, UserUpdate)

app_name='management'

urlpatterns = [
    url(r'^list/$', TournamentView.as_view() ,name="list" ),
    url(r'^create/$', TournamentCreate.as_view() ,name="create" ),
    url(r'^delete/(?P<id>[0-9]+)$', TournamentDelete.as_view() ,name="delete" ),
    url(r'^users/create$', UserCreate.as_view() ,name="user_create" ),
    url(r'^users/(?P<id>[0-9]+)/password$', SetPassword.as_view() ,name="user_password" ),
    url(r'^users/(?P<id>[0-9]+)/edit$', UserUpdate.as_view() ,name="user_edit" ),
    url(r'^users/$', UserPreview(forms.Form), name="users"),
    url(r'^system$', SystemInfo.as_view(), name="system_info"),
    url(r'^profile/$', ProfileDataView.as_view(), name="properties"),
    url(r'^profile/edit/(?P<id>\d+)/$', UDChange.as_view(), name="change_property"),
    url(r'^profile/delete/(?P<id>\d+)/$', UDDelete.as_view(), name="delete_property"),
    url(r'^profile/create/$', UDCreate.as_view(), name="create_property"),
    url(r'^profile/move/(?P<id>\d+)/(?P<direction>\w+)/$', UDMove.as_view(), name="move_property"),
    url(r'^feedback/image/(?P<id>[0-9]+)$', ScreenshotView.as_view(), name="screenshot"),
    url(r'^feedback/$', FeedbackView.as_view(), name="feedback"),
    url(r'^feedback/(?P<id>\d+)/delete/$', FeedbackDeleteView.as_view(), name="feedback_delete"),
]
