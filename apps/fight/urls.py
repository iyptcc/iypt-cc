from django.conf.urls import include, url

from .views import (FightJuryView, FightPreView, FightView, ManageFightsView, PdfPreviewView, PdfRankingView,
                    PdfResultView, PublishView, clocks, fightclock, genpdfpreview, genpdfrank, genpdfresult, plan,
                    validate_plan)

app_name='fight'

urlpatterns = [
    #url(r'^', include('django.contrib.auth.urls')),
    url(r'^plan/$', plan ,name="plan" ),
    url(r'^validate/$', validate_plan ,name="validate" ),
    url(r'^publish/$', PublishView.as_view() ,name="publish" ),
    url(r'^manage/$', ManageFightsView.as_view() ,name="manage" ),
    url(r'^fight/(?P<fight_id>[0-9]+)/$', FightJuryView.as_view() ,name="fightjury" ),
    url(r'^fight/(?P<fight_id>[0-9]+)/preview.pdf$', PdfPreviewView.as_view() ,name="pdfpreview" ),
    url(r'^fight/(?P<fight_id>[0-9]+)/result.pdf$', PdfResultView.as_view() ,name="pdfresult" ),
    url(r'^fight/(?P<fight_id>[0-9]+)/genpreview/$', genpdfpreview ,name="genpdfpreview" ),
    url(r'^fight/(?P<fight_id>[0-9]+)/genresult/$', genpdfresult ,name="genpdfresult" ),
    url(r'^round/(?P<round_nr>[0-9]+)/genrank/$', genpdfrank ,name="genpdfrank" ),
    url(r'^round/(?P<round_nr>[0-9]+)/ranking.pdf$', PdfRankingView.as_view() ,name="pdfrank" ),
    url(r'^round/(?P<round_nr>[0-9]+)/clocks/$', clocks ,name="clocks" ),
    url(r'^fight/(?P<fight_id>[0-9]+)/check/$', FightPreView.as_view() ,name="fightpre" ),
    url(r'^fight/(?P<fight_id>[0-9]+)/(?P<stage>[1-9])/clock/$', fightclock ,name="fightclock" ),
    url(r'^fight/(?P<fight_id>[0-9]+)/(?P<stage>[1-9])/$', FightView.as_view() ,name="fight" ),
]
