from django import forms
from django.conf.urls import include, url

from .preview import JurorsPreview, PossibleJurorPreview, RoundPreview
from .views import (AcceptPossibleJuror, DisplayAssign, FightView, JurorChange, JuryClean, JuryPlan, ListAssignments,
                    PdfJuryFeedback, PdfJuryView, assignJurors, cost_graph, genpdfjuryfeedback, genpdfjuryround,
                    jurorplan)

app_name='jury'

urlpatterns = [
    #url(r'^', include('django.contrib.auth.urls')),
    url(r'^list$', JurorsPreview(forms.Form),name="jurors" ),
    url(r'^possible$', PossibleJurorPreview(forms.Form),name="possiblejurors" ),
    url(r'^possible/accept/(?P<id>[0-9]+)/$', AcceptPossibleJuror.as_view(),name="accept_possiblejuror" ),
    url(r'^plan$', JuryPlan.as_view(),name="plan" ),
    url(r'^juror/(?P<juror_id>[0-9]+)$', jurorplan,name="personal" ),
    url(r'^juror/(?P<juror_id>[0-9]+)/edit$', JurorChange.as_view(),name="edit_juror" ),
    url(r'^fight/(?P<fight_id>[0-9]+)$', FightView.as_view() ,name="fight" ),
    url(r'^fight/(?P<fight_id>[0-9]+)/genfeedback$', genpdfjuryfeedback ,name="jury_feedback" ),
    url(r'^fight/(?P<fight_id>[0-9]+)/feedback.pdf$', PdfJuryFeedback.as_view() ,name="pdf_jury_feedback" ),
    url(r'^clean/(?P<fix_rounds>[0-9]+)$', JuryClean.as_view() ,name="clean" ),
    url(r'^assign/$', ListAssignments.as_view() ,name="assign" ),
    url(r'^assign/new$', assignJurors ,name="assign_new" ),
    url(r'^assign/(?P<id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$', DisplayAssign.as_view() ,name="assign_preview" ),
    url(r'^assign/costs/(?P<id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$', cost_graph ,name="cost_graph" ),
    url(r'^plan/(?P<round>[\d]+)$',RoundPreview(forms.Form), name="edit_round" ),
    url(r'^plan/genpdf/(?P<round_nr>[\d]+)$', genpdfjuryround , name="juryround_pdf" ),
    url(r'^plan/(?P<round>[\d]+)/plan.pdf$', PdfJuryView.as_view() ,name="pdfjuryplan" ),
]
