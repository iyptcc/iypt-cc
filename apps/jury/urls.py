from django import forms
from django.urls import path, re_path

from .preview import JurorsPreview, PossibleJurorPreview, RoundPreview
from .views import (
    AcceptPossibleJuror,
    DisplayAssign,
    FightView,
    JurorChange,
    JuryClean,
    JuryPlan,
    ListAssignments,
    PdfJuryFeedback,
    PdfJuryOverview,
    PdfJurySheet,
    PdfJuryView,
    ViewPossibleJuror,
    assignJurors,
    cost_graph,
    genallpdfjuryfeedback,
    genallpdfjurysheets,
    genpdfjuryfeedback,
    genpdfjuryround,
    genpdfjurysheets,
    jurorplan,
)

app_name = "jury"

urlpatterns = [
    # url(r'^', include('django.contrib.auth.urls')),
    path("list", JurorsPreview(forms.Form), name="jurors"),
    path("possible", PossibleJurorPreview(forms.Form), name="possiblejurors"),
    path(
        "possible/accept/<int:id>/",
        AcceptPossibleJuror.as_view(),
        name="accept_possiblejuror",
    ),
    path("possible/<int:id>/", ViewPossibleJuror.as_view(), name="possiblejuror"),
    path("plan", JuryPlan.as_view(), name="plan"),
    path("juror/<int:juror_id>", jurorplan, name="personal"),
    path("juror/<int:juror_id>/edit", JurorChange.as_view(), name="edit_juror"),
    path("fight/<int:fight_id>", FightView.as_view(), name="fight"),
    path("fight/<int:fight_id>/genfeedback", genpdfjuryfeedback, name="jury_feedback"),
    path("fight/<int:fight_id>/gengrading", genpdfjurysheets, name="jury_grading"),
    re_path(
        r"^fight/(?P<fight_id>[0-9]+)/feedback.pdf$",
        PdfJuryFeedback.as_view(),
        name="pdf_jury_feedback",
    ),
    re_path(
        r"^fight/(?P<fight_id>[0-9]+)/overview.pdf$",
        PdfJuryOverview.as_view(),
        name="pdf_jury_overview",
    ),
    re_path(
        r"^fight/(?P<fight_id>[0-9]+)/(?P<stage_order>[0-9]+)/sheet.pdf$",
        PdfJurySheet.as_view(),
        name="pdf_jury_sheet",
    ),
    path("clean/<int:fix_rounds>", JuryClean.as_view(), name="clean"),
    path("assign/", ListAssignments.as_view(), name="assign"),
    path("assign/new", assignJurors, name="assign_new"),
    path("assign/<uuid:id>", DisplayAssign.as_view(), name="assign_preview"),
    path("assign/costs/<uuid:id>", cost_graph, name="cost_graph"),
    re_path(r"^plan/(?P<round>[\d]+)$", RoundPreview(forms.Form), name="edit_round"),
    re_path(
        r"^plan/genpdf/(?P<round_nr>[\d]+)$", genpdfjuryround, name="juryround_pdf"
    ),
    re_path(
        r"^plan/genfeedback/(?P<round_nr>[\d]+)$",
        genallpdfjuryfeedback,
        name="roundallfeedback_pdf",
    ),
    re_path(
        r"^plan/gensheets/(?P<round_nr>[\d]+)$",
        genallpdfjurysheets,
        name="roundallgrading_pdf",
    ),
    re_path(
        r"^plan/(?P<round>[\d]+)/plan.pdf$", PdfJuryView.as_view(), name="pdfjuryplan"
    ),
]
