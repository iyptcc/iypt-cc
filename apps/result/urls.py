from django.urls import path, re_path

from apps.virtual.views.views import HallInviteView, RoomInviteView

from .views import (
    PdfPartialView,
    PublicRoomInviteView,
    SinglePartialView,
    SlidesView,
    clock,
    fight,
    fight_table,
    gradedump,
    jurystats,
    listTournaments,
    memberrank,
    plan,
    rank,
    resultdump,
    schedule,
    slides,
    team,
    teams,
)

app_name = "result"

urlpatterns = [
    # url(r'^', include('django.contrib.auth.urls')),
    # url(r'^(?P<t_slug>[^/]+)$', plan ,name="plan" ),
    re_path(r"^(?P<t_slug>[-\w]+)/jurystats/$", jurystats, name="jurystats"),
    re_path(r"^(?P<t_slug>[-\w]+)/gradedump/$", gradedump, name="gradedump"),
    re_path(r"^(?P<t_slug>[-\w]+)/resultdump/$", resultdump, name="resultdump"),
    re_path(r"^(?P<t_slug>[-\w]+)/memberrank/$", memberrank, name="memberrank"),
    re_path(r"^(?P<t_slug>[-\w]+)/$", plan, name="plan"),
    re_path(r"^(?P<t_slug>[-\w]+)/plan/$", schedule, name="schedule"),
    re_path(r"^(?P<t_slug>[-\w]+)/teams/$", teams, name="teams"),
    re_path(r"^(?P<t_slug>[-\w]+)/slides/$", slides, name="slides"),
    re_path(
        r"^table/(?P<t_slug>[-\w]+)/(?P<round_nr>[\d]+)/(?P<room_slug>[-\w]+)/$",
        fight_table,
        name="fight_table",
    ),
    re_path(
        r"^(?P<t_slug>[-\w]+)/(?P<round_nr>[\d]+)/(?P<room_slug>[-\w]+)/$",
        fight,
        name="fight",
    ),
    re_path(
        r"^(?P<t_slug>[-\w]+)/(?P<round_nr>[\d]+)/(?P<room_slug>[-\w]+)/virtual$",
        PublicRoomInviteView.as_view(),
        name="virtual",
    ),
    re_path(
        r"^(?P<t_slug>[-\w]+)/(?P<round_nr>[\d]+)/(?P<room_slug>[-\w]+)/clock/(?P<stage_nr>[\d]+)$",
        clock,
        name="clock",
    ),
    re_path(
        r"^(?P<t_slug>[-\w]+)/(?P<round_nr>[\d]+)/(?P<room_slug>[-\w]+)/partials.pdf$",
        PdfPartialView.as_view(),
        name="pdfpartial",
    ),
    re_path(
        r"^(?P<t_slug>[-\w]+)/partial_sheet/(?P<sheet_id>[\d]+).jpg$",
        SinglePartialView.as_view(),
        name="singlepartial",
    ),
    re_path(
        r"^(?P<t_slug>[-\w]+)/presentation_slides/(?P<stage_id>[\d]+)_(?P<round>[\d]+)_(?P<country>[-\w]+).pdf$",
        SlidesView.as_view(),
        name="slidesdownload",
    ),
    re_path(r"^(?P<t_slug>[-\w]+)/team/(?P<origin_slug>[-\w]+)/$", team, name="team"),
    re_path(r"^(?P<t_slug>[-\w]+)/rank/$", rank, name="rank"),
    re_path(
        r"^(?P<t_slug>[-\w]+)/hall/(?P<hall_id>\d+)/(?P<role>[\w]+)/(?P<sig>.+)$",
        HallInviteView.as_view(),
        name="hall",
    ),
    re_path(
        r"^(?P<t_slug>[-\w]+)/room/(?P<fight_id>\d+)/(?P<role>[\w]+)/(?P<sig>.+)$",
        RoomInviteView.as_view(),
        name="room",
    ),
    path("", listTournaments, name="index"),
]
