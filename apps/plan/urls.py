from django import forms
from django.urls import path, re_path

from .forms import CuriieForm
from .preview import (
    CuriiePreview,
    FinalPreview,
    PersonsPreview,
    RoundPreview,
    TeamsPreview,
    TemplatePreview,
)
from .views import events
from .views.views import (
    FinalDelete,
    PdfProblemSelect,
    PdfTeamView,
    PhPlanDelete,
    Placeholder,
    PlaceholderTeams,
    drawdelTeam,
    drawTeam,
    genpdfproblemselect,
    genpdfteamround,
    jurydatadump,
    phbeamer,
    phbeamercontrol,
    phplanapply,
    phteamsdel,
    phteamsgen,
    plan,
)

app_name = "plan"

urlpatterns = [
    # url(r'^', include('django.contrib.auth.urls')),
    path("", plan, name="plan"),
    re_path(r"^jury/dump.yml$", jurydatadump, name="jurydata"),
    re_path(
        r"^plan/genpdf/(?P<round_nr>[\d]+)$", genpdfteamround, name="teamround_pdf"
    ),
    re_path(
        r"^plan/(?P<round>[\d]+)/plan.pdf$", PdfTeamView.as_view(), name="pdfteamplan"
    ),
    re_path(
        r"^plan/genselect/(?P<round_nr>[\d]+)$",
        genpdfproblemselect,
        name="problemselect_pdf",
    ),
    re_path(
        r"^plan/(?P<round>[\d]+)/select.pdf$",
        PdfProblemSelect.as_view(),
        name="pdfproblemselect",
    ),
    path("placeholder/plan", Placeholder.as_view(), name="placeholder"),
    path("placeholder/plan/delete", PhPlanDelete.as_view(), name="phplandel"),
    path(
        "placeholder/plan/load/<int:template_id>",
        TemplatePreview(forms.Form),
        name="loadtemplate",
    ),
    path(
        "placeholder/plan/edit/<int:round_nr>",
        RoundPreview(forms.Form),
        name="editround",
    ),
    re_path(r"^placeholder/plan/apply", phplanapply, name="phapply"),
    path("placeholder/teams", PlaceholderTeams.as_view(), name="phteams"),
    path("placeholder/teams/generate", phteamsgen, name="phteamsgen"),
    path("placeholder/teams/delete", phteamsdel, name="phteamsdel"),
    path(
        "placeholder/teams/draw/<int:team_id>/for/<int:placeholder_nr>",
        drawTeam,
        name="drawteam",
    ),
    path(
        "placeholder/teams/draw/<int:team_id>/for/---", drawdelTeam, name="drawdelteam"
    ),
    path("placeholder/beamer", phbeamer, name="phbeamer"),
    path("placeholder/control", phbeamercontrol, name="phbeamercontrol"),
    path("events/", events.View.as_view(), name="events"),
    path("events/edit/<int:id>/", events.Change.as_view(), name="change_event"),
    path("events/delete/<int:id>/", events.Delete.as_view(), name="delete_event"),
    path("events/create/", events.Create.as_view(), name="create_event"),
    path("teams", TeamsPreview(forms.Form), name="teams"),
    path("persons", PersonsPreview(forms.Form), name="persons"),
    path("curiie", CuriiePreview(CuriieForm), name="curiie"),
    path("final", FinalPreview(forms.Form), name="final"),
    path("final/delete", FinalDelete.as_view(), name="finaldel"),
]
