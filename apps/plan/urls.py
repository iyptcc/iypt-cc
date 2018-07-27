from django import forms
from django.conf.urls import include, url

from .forms import CuriieForm
from .preview import CuriiePreview, FinalPreview, PersonsPreview, RoundPreview, TeamsPreview, TemplatePreview
from .views import (FinalDelete, PdfProblemSelect, PdfTeamView, PhPlanDelete, Placeholder, PlaceholderTeams,
                    drawdelTeam, drawTeam, genpdfproblemselect, genpdfteamround, phbeamer, phbeamercontrol, phplanapply,
                    phteamsdel, phteamsgen, plan)

app_name='plan'

urlpatterns = [
    #url(r'^', include('django.contrib.auth.urls')),
    url(r'^$', plan ,name="plan" ),
    url(r'^plan/genpdf/(?P<round_nr>[\d]+)$', genpdfteamround , name="teamround_pdf" ),
    url(r'^plan/(?P<round>[\d]+)/plan.pdf$', PdfTeamView.as_view() ,name="pdfteamplan" ),
    url(r'^plan/genselect/(?P<round_nr>[\d]+)$', genpdfproblemselect , name="problemselect_pdf" ),
    url(r'^plan/(?P<round>[\d]+)/select.pdf$', PdfProblemSelect.as_view() ,name="pdfproblemselect" ),
    url(r'^placeholder/plan$', Placeholder.as_view() ,name="placeholder" ),
    url(r'^placeholder/plan/delete$', PhPlanDelete.as_view() ,name="phplandel" ),
    url(r'^placeholder/plan/load/(?P<template_id>[0-9]+)$', TemplatePreview(forms.Form) ,name="loadtemplate" ),
    url(r'^placeholder/plan/edit/(?P<round_nr>[0-9]+)$', RoundPreview(forms.Form) ,name="editround" ),
    url(r'^placeholder/plan/apply', phplanapply ,name="phapply" ),
    url(r'^placeholder/teams$', PlaceholderTeams.as_view() ,name="phteams" ),
    url(r'^placeholder/teams/generate$', phteamsgen ,name="phteamsgen" ),
    url(r'^placeholder/teams/delete$', phteamsdel ,name="phteamsdel" ),
    url(r'^placeholder/teams/draw/(?P<team_id>[0-9]+)/for/(?P<placeholder_nr>[0-9]+)$', drawTeam ,name="drawteam" ),
    url(r'^placeholder/teams/draw/(?P<team_id>[0-9]+)/for/---$', drawdelTeam ,name="drawdelteam" ),
    url(r'^placeholder/beamer$', phbeamer ,name="phbeamer" ),
    url(r'^placeholder/control$', phbeamercontrol ,name="phbeamercontrol" ),
    url(r'^teams$', TeamsPreview(forms.Form) ,name="teams" ),
    url(r'^persons$', PersonsPreview(forms.Form) ,name="persons" ),
    url(r'^curiie$', CuriiePreview(CuriieForm) ,name="curiie" ),
    url(r'^final$', FinalPreview(forms.Form) ,name="final" ),
    url(r'^final/delete$', FinalDelete.as_view() ,name="finaldel" ),
]
