from django.conf.urls import include, url

from .views import PdfPartialView, fight, fight_table, gradedump, jurystats, listTournaments, plan, rank, schedule, team

app_name='result'

urlpatterns = [
    #url(r'^', include('django.contrib.auth.urls')),
    #url(r'^(?P<t_slug>[^/]+)$', plan ,name="plan" ),
    url(r'^(?P<t_slug>[-\w]+)/jurystats/$', jurystats, name="jurystats"),
    url(r'^(?P<t_slug>[-\w]+)/gradedump/$', gradedump, name="gradedump"),
    url(r'^(?P<t_slug>[-\w]+)/$', plan ,name="plan" ),
    url(r'^(?P<t_slug>[-\w]+)/plan/$', schedule ,name="schedule" ),
    url(r'^table/(?P<t_slug>[-\w]+)/(?P<round_nr>[\d]+)/(?P<room_slug>[-\w]+)/$', fight_table, name="fight_table"),
    url(r'^(?P<t_slug>[-\w]+)/(?P<round_nr>[\d]+)/(?P<room_slug>[-\w]+)/$', fight, name="fight"),
    url(r'^(?P<t_slug>[-\w]+)/(?P<round_nr>[\d]+)/(?P<room_slug>[-\w]+)/partials.pdf$', PdfPartialView.as_view() ,name="pdfpartial" ),
    url(r'^(?P<t_slug>[-\w]+)/team/(?P<origin_slug>[-\w]+)/$', team, name="team"),
    url(r'^(?P<t_slug>[-\w]+)/rank/$', rank, name="rank"),
    url(r'^$', listTournaments, name="index"),
]
