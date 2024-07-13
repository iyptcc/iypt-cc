from django import forms
from django.urls import path, re_path

from .preview import UserPreview
from .views import (
    FeedbackDeleteView,
    FeedbackView,
    ProfileDataView,
    ScreenshotView,
    SetPassword,
    SystemInfo,
    TournamentChange,
    TournamentCreate,
    TournamentDelete,
    TournamentView,
    UDChange,
    UDCreate,
    UDDelete,
    UDMove,
    UserCreate,
    UserUpdate,
    mm_create_team,
    trigger_error,
)

app_name = "management"

urlpatterns = [
    path("list/", TournamentView.as_view(), name="list"),
    path("create/", TournamentCreate.as_view(), name="create"),
    path("mm-team/<int:trn_id>", mm_create_team, name="mm_create_team"),
    path("change/<int:id>", TournamentChange.as_view(), name="change"),
    path("delete/<int:id>", TournamentDelete.as_view(), name="delete"),
    path("users/create", UserCreate.as_view(), name="user_create"),
    path("users/<int:id>/password", SetPassword.as_view(), name="user_password"),
    path("users/<int:id>/edit", UserUpdate.as_view(), name="user_edit"),
    path("users/", UserPreview(forms.Form), name="users"),
    path("system", SystemInfo.as_view(), name="system_info"),
    path("error/", trigger_error, name="error_debug"),
    path("profile/", ProfileDataView.as_view(), name="properties"),
    path("profile/edit/<int:id>/", UDChange.as_view(), name="change_property"),
    path("profile/delete/<int:id>/", UDDelete.as_view(), name="delete_property"),
    path("profile/create/", UDCreate.as_view(), name="create_property"),
    re_path(
        r"^profile/move/(?P<id>\d+)/(?P<direction>\w+)/$",
        UDMove.as_view(),
        name="move_property",
    ),
    path("feedback/image/<int:id>", ScreenshotView.as_view(), name="screenshot"),
    path("feedback/", FeedbackView.as_view(), name="feedback"),
    path(
        "feedback/<int:id>/delete/",
        FeedbackDeleteView.as_view(),
        name="feedback_delete",
    ),
]
