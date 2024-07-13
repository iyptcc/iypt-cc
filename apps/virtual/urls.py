from django.urls import path, re_path

from .views import hallrole, halls, mattermost, streamedge, streams
from .views.views import (
    AvatarView,
    FightView,
    GradingSheetView,
    ManageRoomsView,
    RoomLinks,
    fightviewclock,
    joinhall,
    joinroom,
    overview,
    prelim_grades,
    watchstream,
)

app_name = "virtual"

urlpatterns = [
    # url(r'^', include('django.contrib.auth.urls')),
    path("overview/", overview, name="overview"),
    re_path(
        r"^clock/(?P<fight_id>[0-9]+)/(?P<stage>[1-9])/$", fightviewclock, name="clock"
    ),
    path("rooms/", ManageRoomsView.as_view(), name="rooms"),
    path("rooms/links/<int:id>/", RoomLinks.as_view(), name="room_links"),
    path("rooms/chat/<int:fight_id>/", mattermost.update_channel, name="chat"),
    path("rooms/join/<int:fight_id>/", joinroom, name="join"),
    path("avatar/<int:avatar_id>/", AvatarView.as_view(), name="avatar"),
    re_path(
        r"^grades/(?P<fight_id>[0-9]+)/(?P<stage>[1-9])/$",
        FightView.as_view(),
        name="fight",
    ),
    re_path(r"^grading_sheet.pdf$", GradingSheetView.as_view(), name="grading_sheet"),
    path("prelim_grades/<int:fight_id>/", prelim_grades, name="prelim"),
    path("halls/join/<int:hall_id>", joinhall, name="joinhall"),
    path("halls/", halls.View.as_view(), name="halls"),
    path("halls/edit/<int:id>/", halls.Change.as_view(), name="change_hall"),
    path("halls/delete/<int:id>/", halls.Delete.as_view(), name="delete_hall"),
    path("halls/links/<int:id>/", halls.Links.as_view(), name="link_hall"),
    path("halls/create/", halls.Create.as_view(), name="create_hall"),
    re_path(
        r"^halls/move/(?P<id>\d+)/(?P<direction>\w+)/$",
        halls.Move.as_view(),
        name="move_hall",
    ),
    path("hall_roles/<int:hall_id>/", hallrole.View.as_view(), name="hallroles"),
    path(
        "hall_roles/<int:hall_id>/edit/<int:id>/",
        hallrole.Change.as_view(),
        name="change_hallrole",
    ),
    path(
        "hall_roles/<int:hall_id>/delete/<int:id>/",
        hallrole.Delete.as_view(),
        name="delete_hallrole",
    ),
    path(
        "hall_roles/<int:hall_id>/create/",
        hallrole.Create.as_view(),
        name="create_hallrole",
    ),
    path("stream/<int:stream_id>/", watchstream, name="stream"),
    path("streams/", streams.View.as_view(), name="streams"),
    path("streams/edit/<int:id>/", streams.Change.as_view(), name="change_stream"),
    path("streams/delete/<int:id>/", streams.Delete.as_view(), name="delete_stream"),
    path("streams/create/", streams.Create.as_view(), name="create_stream"),
    path("stream_edge/<int:stream_id>/", streamedge.View.as_view(), name="streamedges"),
    path(
        "stream_edge/<int:stream_id>/edit/<int:id>/",
        streamedge.Change.as_view(),
        name="change_streamedge",
    ),
    path(
        "stream_edge/<int:stream_id>/delete/<int:id>/",
        streamedge.Delete.as_view(),
        name="delete_streamedge",
    ),
    path(
        "stream_edge/<int:stream_id>/create/",
        streamedge.Create.as_view(),
        name="create_streamedge",
    ),
]
