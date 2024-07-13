import binascii
import os

from celery.result import AsyncResult
from django.contrib import messages
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import Group
from django.core import serializers
from django.core.cache import caches
from django.core.serializers import pyyaml as pyyamlserializer
from django.db import IntegrityError, transaction
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_list_or_404, get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.text import capfirst
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.account.models import ApiUser, ParticipationRole, Token
from apps.dashboard.delete import ConfirmedDeleteView
from apps.jury.models import JurorOccupation
from apps.postoffice.models import DefaultTemplate as DefaultMailTemplate
from apps.postoffice.models import Template as MailTemplate
from apps.printer.models import DefaultTemplate, Template
from apps.registration.models import ApplicationQuestion, AttendeeProperty
from apps.team.models import TeamRole

from ..forms import (
    ADEditForm,
    ApiUserEditForm,
    AQEditForm,
    BankSettingsForm,
    FeedbackSettingsForm,
    GroupEditForm,
    JurySettingsForm,
    MailTemplateSettingsForm,
    OriginForm,
    PropertyChoiceFormSet,
    RegistrationSettingsForm,
    RoleEditForm,
    ScrubExceptForm,
    TemplateSettingsForm,
    TournamentForm,
    TRoleEditForm,
)
from ..models import Origin, Phase, Problem, Tournament
from ..tasks import scrubPII, scrubpreparePII
from ..utils import _more_perm_than_group


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("tournament.change_tournament", raise_exception=False),
    name="dispatch",
)
class Overview(UpdateView):

    template_name = "tournament/overview.html"

    form_class = TournamentForm

    success_url = reverse_lazy("tournament:overview")

    def get_object(self, queryset=None):
        return self.request.user.profile.tournament


@method_decorator(
    permission_required("printer.change_defaulttemplate", raise_exception=False),
    name="dispatch",
)
class TemplateSettings(View):
    def get(self, request):
        form = TemplateSettingsForm(request.user.profile.tournament)

        return render(request, "tournament/overview.html", context={"form": form})

    def post(self, request):
        trn = request.user.profile.tournament
        form = TemplateSettingsForm(trn, request.POST)

        if form.is_valid():

            for type in Template.TYPE:
                if (
                    "default_template_%s" % type[0] in form.cleaned_data
                    and form.cleaned_data["default_template_%s" % type[0]]
                ):
                    try:
                        dt = DefaultTemplate.objects.get(tournament=trn, type=type[0])
                        dt.template = form.cleaned_data["default_template_%s" % type[0]]
                        dt.save()
                    except:
                        DefaultTemplate.objects.create(
                            tournament=trn,
                            template=form.cleaned_data["default_template_%s" % type[0]],
                            type=type[0],
                        )

            messages.add_message(request, messages.SUCCESS, "Settings updated")

        return render(request, "tournament/overview.html", context={"form": form})


@method_decorator(
    permission_required("postoffice.change_defaulttemplate", raise_exception=False),
    name="dispatch",
)
class MailTemplateSettings(View):
    def get(self, request):
        form = MailTemplateSettingsForm(request.user.profile.tournament)

        return render(request, "tournament/overview.html", context={"form": form})

    def post(self, request):
        trn = request.user.profile.tournament
        form = MailTemplateSettingsForm(trn, request.POST)

        if form.is_valid():

            for type in MailTemplate.TYPE:
                if (
                    "default_mail_template_%s" % type[0] in form.cleaned_data
                    and form.cleaned_data["default_mail_template_%s" % type[0]]
                ):
                    try:
                        dt = DefaultMailTemplate.objects.get(
                            tournament=trn, type=type[0]
                        )
                        dt.template = form.cleaned_data[
                            "default_mail_template_%s" % type[0]
                        ]
                        dt.save()
                    except:
                        DefaultMailTemplate.objects.create(
                            tournament=trn,
                            template=form.cleaned_data[
                                "default_mail_template_%s" % type[0]
                            ],
                            type=type[0],
                        )

            messages.add_message(request, messages.SUCCESS, "Settings updated")

        return render(request, "tournament/overview.html", context={"form": form})


class RegistrationSettings(UpdateView):

    template_name = "tournament/overview.html"

    form_class = RegistrationSettingsForm

    success_url = reverse_lazy("tournament:registration")

    def get_object(self, queryset=None):
        return self.request.user.profile.tournament


class FeedbackSettings(UpdateView):

    template_name = "tournament/overview.html"

    form_class = FeedbackSettingsForm

    success_url = reverse_lazy("tournament:feedback")

    def get_object(self, queryset=None):
        return self.request.user.profile.tournament


class JurySettings(UpdateView):

    template_name = "tournament/overview.html"

    form_class = JurySettingsForm

    success_url = reverse_lazy("tournament:jury")

    def get_object(self, queryset=None):
        return self.request.user.profile.tournament


class BankSettings(UpdateView):

    template_name = "tournament/overview.html"

    form_class = BankSettingsForm

    success_url = reverse_lazy("tournament:bank")

    def get_object(self, queryset=None):
        return self.request.user.profile.tournament


@method_decorator(login_required, name="dispatch")
class ProblemView(ListView):

    template_name = "tournament/problemList.html"

    def get_queryset(self):
        return Problem.objects.filter(
            tournament=self.request.user.profile.tournament
        ).order_by("number")


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("tournament.change_problem", raise_exception=False),
    name="dispatch",
)
class ProblemChange(UpdateView):

    model = Problem
    fields = ["number", "title", "description"]

    success_url = reverse_lazy("tournament:problems")

    def get_object(self, queryset=None):
        obj = Problem.objects.get(
            id=self.kwargs["id"], tournament=self.request.user.profile.tournament
        )
        return obj

    def post(self, request, *args, **kwargs):
        # clear all caches
        caches["results"].clear()

        return super().post(request, *args, **kwargs)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("tournament.add_problem", raise_exception=False),
    name="dispatch",
)
class ProblemCreate(CreateView):

    model = Problem
    fields = ["number", "title", "description"]

    success_url = reverse_lazy("tournament:problems")

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        try:
            validation = super(ProblemCreate, self).form_valid(form)
            # clear all caches
            caches["results"].clear()
            return validation
        except IntegrityError:
            messages.add_message(
                self.request,
                messages.ERROR,
                "Problem number %d already exists" % form.instance.number,
            )
            return redirect("tournament:problems")


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("tournament.delete_problem", raise_exception=False),
    name="dispatch",
)
class ProblemDelete(ConfirmedDeleteView):

    redirection = "tournament:problems"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            Problem, tournament=request.user.profile.tournament, id=kwargs["id"]
        )
        return obj


@method_decorator(login_required, name="dispatch")
class OriginView(ListView):

    template_name = "tournament/originList.html"

    def get_queryset(self):
        return Origin.objects.filter(tournament=self.request.user.profile.tournament)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("tournament.change_origin", raise_exception=False),
    name="dispatch",
)
class OriginChange(UpdateView):

    model = Origin

    def get_form(self, form_class=None):
        return OriginForm(self.request.user.profile, **self.get_form_kwargs())

    success_url = reverse_lazy("tournament:origins")

    def get_object(self, queryset=None):
        obj = Origin.objects.get(
            id=self.kwargs["id"], tournament=self.request.user.profile.tournament
        )
        return obj

    def post(self, request, *args, **kwargs):
        # clear all caches
        caches["results"].clear()

        return super().post(request, *args, **kwargs)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("tournament.add_origin", raise_exception=False), name="dispatch"
)
class OriginCreate(CreateView):

    model = Origin
    fields = ["name", "alpha2iso", "flag"]

    success_url = reverse_lazy("tournament:origins")

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        try:
            validation = super(OriginCreate, self).form_valid(form)
            # clear all caches
            caches["results"].clear()
            return validation
        except IntegrityError:
            messages.add_message(
                self.request,
                messages.ERROR,
                "Origin %s already exists" % form.instance.name,
            )
            return redirect("tournament:origins")


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("tournament.delete_origin", raise_exception=False),
    name="dispatch",
)
class OriginDelete(ConfirmedDeleteView):

    redirection = "tournament:origins"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            Origin, tournament=request.user.profile.tournament, id=kwargs["id"]
        )
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("jury.publish_fights", raise_exception=False), name="dispatch"
)
class CachesView(View):
    def get(self, request):
        print(caches["results"])

        fights = []
        for r in request.user.profile.tournament.round_set.all():
            for f in r.fight_set.all():
                fight = {}
                for k in ["preview", "points", "grades"]:
                    fight[k] = caches["results"].get("%s-%s" % (k, f.pk))
                fights.append(fight)

        return render(request, "tournament/caches.html", context={"cache": fights})

    def post(self, request):
        caches["results"].clear()

        return redirect("tournament:caches")


@method_decorator(login_required, name="dispatch")
class ApplicationQuestionView(ListView):

    template_name = "tournament/applicationQList.html"

    def get_queryset(self):
        return ApplicationQuestion.objects.filter(
            role__tournament=self.request.user.profile.tournament,
            role_id=self.kwargs["role_id"],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["role"] = ParticipationRole.objects.get(
            tournament=self.request.user.profile.tournament, id=self.kwargs["role_id"]
        )
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("registration.add_applicationquestion", raise_exception=False),
    name="dispatch",
)
class AQCreate(CreateView):

    model = ApplicationQuestion

    def get_success_url(self):
        return reverse_lazy(
            "tournament:applicationqs", kwargs={"role_id": self.kwargs["role_id"]}
        )

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return AQEditForm(
            self.request.user.profile.tournament, **self.get_form_kwargs()
        )

    def form_valid(self, form):

        form.instance.role = ParticipationRole.objects.get(
            tournament=self.request.user.profile.tournament, id=self.kwargs["role_id"]
        )
        try:
            validation = super(AQCreate, self).form_valid(form)
            # clear all caches
            return validation
        except IntegrityError:
            messages.add_message(
                self.request,
                messages.ERROR,
                "Attribute %s already exists" % form.instance.name,
            )
            return redirect("tournament:applicationqs", role_id=self.kwargs["role_id"])


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(
        "registration.change_applicationquestion", raise_exception=False
    ),
    name="dispatch",
)
class AQChange(UpdateView):

    model = ApplicationQuestion

    def get_success_url(self):
        return reverse_lazy(
            "tournament:applicationqs", kwargs={"role_id": self.kwargs["role_id"]}
        )

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return AQEditForm(
            self.request.user.profile.tournament, **self.get_form_kwargs()
        )

    def get_object(self, queryset=None):
        obj = ApplicationQuestion.objects.get(
            id=self.kwargs["id"],
            role__id=self.kwargs["role_id"],
            role__tournament=self.request.user.profile.tournament,
        )
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(
        "registration.change_applicationquestion", raise_exception=False
    ),
    name="dispatch",
)
class AQDelete(ConfirmedDeleteView):

    def get_redirection(self, request, *args, **kwargs):
        return redirect("tournament:applicationqs", role_id=kwargs["role_id"])

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            ApplicationQuestion,
            role__tournament=request.user.profile.tournament,
            role__id=kwargs["role_id"],
            id=kwargs["id"],
        )
        return obj


@method_decorator(
    permission_required(
        "registration.change_applicationquestion", raise_exception=False
    ),
    name="dispatch",
)
class AQMove(View):
    def post(self, request, role_id, id, direction):
        obj = get_object_or_404(
            ApplicationQuestion,
            id=self.kwargs["id"],
            role__id=self.kwargs["role_id"],
            role__tournament=self.request.user.profile.tournament,
        )
        if direction == "up":
            obj.up()
        if direction == "down":
            obj.down()

        return redirect("tournament:applicationqs", role_id=self.kwargs["role_id"])


@method_decorator(login_required, name="dispatch")
class AttendeeDataView(ListView):

    template_name = "tournament/dataList.html"

    def get_queryset(self):
        return AttendeeProperty.objects.filter(
            tournament=self.request.user.profile.tournament
        )

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        form = ScrubExceptForm(self.request.user.profile.tournament)
        context["form"] = form
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("tournament.change_attendee_data", raise_exception=False),
    name="dispatch",
)
class ADChange(UpdateView):

    model = AttendeeProperty

    # form_class = ADEditForm

    success_url = reverse_lazy("tournament:properties")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return ADEditForm(
            self.request.user.profile.tournament, **self.get_form_kwargs()
        )

    def get_context_data(self, **kwargs):
        context = super(ADChange, self).get_context_data(**kwargs)
        if self.request.POST:
            context["choices"] = PropertyChoiceFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context["choices"] = PropertyChoiceFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        choices = context["choices"]
        with transaction.atomic():
            self.object = form.save()
        if choices.is_valid():
            choices.instance = self.object
            choices.save()
        return super(ADChange, self).form_valid(form)

    def get_object(self, queryset=None):
        obj = AttendeeProperty.objects.get(
            id=self.kwargs["id"], tournament=self.request.user.profile.tournament
        )
        return obj

    def post(self, request, *args, **kwargs):
        # clear all caches
        # caches['results'].clear()

        return super().post(request, *args, **kwargs)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("tournament.change_attendee_data", raise_exception=False),
    name="dispatch",
)
class ADCreate(CreateView):

    model = AttendeeProperty

    # form_class = ADEditForm

    success_url = reverse_lazy("tournament:properties")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return ADEditForm(
            self.request.user.profile.tournament, **self.get_form_kwargs()
        )

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        try:
            validation = super(ADCreate, self).form_valid(form)
            # clear all caches
            return validation
        except IntegrityError:
            messages.add_message(
                self.request,
                messages.ERROR,
                "Attribute %s already exists" % form.instance.name,
            )
            return redirect("tournament:properties")


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("tournament.delete_attendee_data", raise_exception=False),
    name="dispatch",
)
class ADDelete(ConfirmedDeleteView):

    redirection = "tournament:properties"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            AttendeeProperty,
            tournament=request.user.profile.tournament,
            id=kwargs["id"],
        )
        return obj


@method_decorator(
    permission_required("tournament.change_attendee_data", raise_exception=False),
    name="dispatch",
)
class ADMove(View):
    def post(self, request, id, direction):
        obj = get_object_or_404(
            AttendeeProperty,
            id=self.kwargs["id"],
            tournament=self.request.user.profile.tournament,
        )
        if direction == "up":
            obj.up()
        if direction == "down":
            obj.down()

        return redirect("tournament:properties")


@method_decorator(login_required, name="dispatch")
class PhasesView(ListView):

    template_name = "tournament/phases.html"

    def get_queryset(self):
        return Phase.objects.filter(tournament=self.request.user.profile.tournament)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("tournament.add_phase", raise_exception=False), name="dispatch"
)
class PhaseCreate(CreateView):

    model = Phase
    fields = ["name", "duration", "linked"]

    success_url = reverse_lazy("tournament:phases")

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        try:
            return super(PhaseCreate, self).form_valid(form)
        except IntegrityError:
            messages.add_message(
                self.request,
                messages.ERROR,
                "Role of type %s already exists" % form.instance.get_type_display(),
            )
            return redirect("tournament:phases")


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("tournament.change_phase", raise_exception=False),
    name="dispatch",
)
class PhaseChange(UpdateView):

    model = Phase
    fields = ["name", "duration", "linked"]

    success_url = reverse_lazy("tournament:phases")

    def get_object(self, queryset=None):
        obj = Phase.objects.get(
            id=self.kwargs["id"], tournament=self.request.user.profile.tournament
        )
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("tournament.delete_phase", raise_exception=False),
    name="dispatch",
)
class PhaseDelete(ConfirmedDeleteView):

    redirection = "tournament:phases"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            Phase, tournament=request.user.profile.tournament, id=kwargs["id"]
        )
        return obj


@method_decorator(
    permission_required("tournament.change_phase", raise_exception=False),
    name="dispatch",
)
class PhaseMove(View):
    def post(self, request, id, direction):
        obj = get_object_or_404(
            Phase, id=self.kwargs["id"], tournament=self.request.user.profile.tournament
        )
        if direction == "up":
            obj.up()
        if direction == "down":
            obj.down()

        return redirect("tournament:phases")


@method_decorator(login_required, name="dispatch")
class JOccupationView(ListView):

    template_name = "tournament/joccupations.html"

    def get_queryset(self):
        return JurorOccupation.objects.filter(
            tournament=self.request.user.profile.tournament
        )


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("jury.add_juroroccupation", raise_exception=False),
    name="dispatch",
)
class JOccupationCreate(CreateView):

    model = JurorOccupation
    fields = [
        "name",
    ]

    success_url = reverse_lazy("tournament:joccupations")

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        try:
            return super(JOccupationCreate, self).form_valid(form)
        except IntegrityError:
            messages.add_message(self.request, messages.ERROR, "error")
            return redirect("tournament:joccupations")


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("jury.change_juroroccupation", raise_exception=False),
    name="dispatch",
)
class JOccupationChange(UpdateView):

    model = JurorOccupation
    fields = [
        "name",
    ]

    success_url = reverse_lazy("tournament:joccupations")

    def get_object(self, queryset=None):
        obj = JurorOccupation.objects.get(
            id=self.kwargs["id"], tournament=self.request.user.profile.tournament
        )
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("jury.delete_juroroccupation", raise_exception=False),
    name="dispatch",
)
class JOccupationDelete(ConfirmedDeleteView):

    redirection = "tournament:joccupations"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            JurorOccupation, tournament=request.user.profile.tournament, id=kwargs["id"]
        )
        return obj


@method_decorator(
    permission_required("jury.change_juroroccupation", raise_exception=False),
    name="dispatch",
)
class JOccupationMove(View):
    def post(self, request, id, direction):
        obj = get_object_or_404(
            JurorOccupation,
            id=self.kwargs["id"],
            tournament=self.request.user.profile.tournament,
        )
        if direction == "up":
            obj.up()
        if direction == "down":
            obj.down()

        return redirect("tournament:joccupations")


@method_decorator(login_required, name="dispatch")
class TRolesView(ListView):

    template_name = "tournament/trolesList.html"

    def get_queryset(self):
        return TeamRole.objects.filter(tournament=self.request.user.profile.tournament)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("team.add_teamrole", raise_exception=False), name="dispatch"
)
class TRoleCreate(CreateView):

    model = TeamRole
    fields = ["name", "type", "participation_roles"]

    success_url = reverse_lazy("tournament:troles")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return TRoleEditForm(
            self.request.user.profile.tournament, **self.get_form_kwargs()
        )

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        try:
            return super(TRoleCreate, self).form_valid(form)
        except IntegrityError:
            messages.add_message(
                self.request,
                messages.ERROR,
                "Team Role of type %s already exists"
                % form.instance.get_type_display(),
            )
            return redirect("tournament:troles")


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("team.change_teamrole", raise_exception=False), name="dispatch"
)
class TRoleChange(UpdateView):

    model = TeamRole
    fields = ["name", "type", "participation_roles"]

    success_url = reverse_lazy("tournament:troles")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return TRoleEditForm(
            self.request.user.profile.tournament, **self.get_form_kwargs()
        )

    def get_object(self, queryset=None):
        obj = TeamRole.objects.get(
            id=self.kwargs["id"], tournament=self.request.user.profile.tournament
        )
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("team.delete_teamrole", raise_exception=False), name="dispatch"
)
class TRoleDelete(ConfirmedDeleteView):

    redirection = "tournament:troles"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            TeamRole, tournament=request.user.profile.tournament, id=kwargs["id"]
        )
        return obj


@method_decorator(login_required, name="dispatch")
class GroupsView(ListView):

    template_name = "tournament/groupsList.html"

    def get_queryset(self):
        groups = self.request.user.profile.tournament.groups.all()
        gr = []
        for g in groups:
            if _more_perm_than_group(self.request.user, g):
                gr.append((g, True))
            else:
                gr.append((g, False))
        return gr


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("auth.add_group", raise_exception=False), name="dispatch"
)
class GroupCreate(CreateView):

    model = Group

    success_url = reverse_lazy("tournament:pgroups")

    form_class = GroupEditForm

    def get_form(self, form_class=None):
        return GroupEditForm(self.request.user.profile.active, **self.get_form_kwargs())

    def form_valid(self, form):
        g = form.save(commit=False)
        try:
            g.save()
            self.request.user.profile.tournament.groups.add(g)
        except IntegrityError:
            messages.add_message(
                self.request,
                messages.ERROR,
                "Group of name %s already exists" % form.instance.name,
            )
        form.save()
        return redirect("tournament:pgroups")


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("auth.change_group", raise_exception=False), name="dispatch"
)
class GroupChange(UpdateView):

    model = Group

    def get_form(self, form_class=None):
        return GroupEditForm(self.request.user.profile.active, **self.get_form_kwargs())

    success_url = reverse_lazy("tournament:pgroups")

    def get_object(self, queryset=None):
        obj = self.request.user.profile.tournament.groups.get(id=self.kwargs["id"])
        if obj.tournament_set.count() > 1:
            raise Group.DoesNotExist("It is a shared group")
        if not _more_perm_than_group(self.request.user, obj):
            raise Group.DoesNotExist("Not enough permissions")

        return obj


class MultiSerializer(pyyamlserializer.Serializer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current = None
        self.objects = []

    def start_serialization(self):
        pass

    pass


class DumpView(View):
    def get(self, request):
        serializer = MultiSerializer()
        serializer.serialize(
            TeamRole.objects.filter(tournament=request.user.profile.tournament),
            fields=(
                "name",
                "type",
                "participation_roles",
                "members_min",
                "members_max",
            ),
        )
        serializer.serialize(
            ParticipationRole.objects.filter(
                tournament=request.user.profile.tournament
            ),
            fields=("name", "type", "groups", "fee", "manager_approvable"),
        )
        serializer.serialize(
            Tournament.objects.filter(pk=request.user.profile.tournament.id)
        )
        serializer.serialize(
            AttendeeProperty.objects.filter(tournament=request.user.profile.tournament)
        )
        serializer.serialize(
            DefaultTemplate.objects.filter(tournament=request.user.profile.tournament)
        )
        serializer.serialize(
            Problem.objects.filter(tournament=request.user.profile.tournament)
        )
        serializer.serialize(request.user.profile.tournament.groups.all())
        data = serializer.getvalue()

        for obj in serializers.deserialize("yaml", data):
            print(obj)

        return render(request, "tournament/dump.html", context={"yaml": data})


@method_decorator(login_required, name="dispatch")
class ApiView(ListView):

    template_name = "tournament/apiList.html"

    def get_queryset(self):
        return ApiUser.objects.filter(tournament=self.request.user.profile.tournament)

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)

        visible_ids = []
        for a in self.get_queryset():
            for g in a.groups.all():
                if _more_perm_than_group(self.request.user, g):
                    visible_ids.append(a.id)

        context["visible"] = visible_ids
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("account.delete_apiuser", raise_exception=False),
    name="dispatch",
)
class ApiDelete(ConfirmedDeleteView):

    redirection = "tournament:apiusers"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            ApiUser, tournament=request.user.profile.tournament, id=kwargs["apiuser_id"]
        )
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("account.add_apiuser", raise_exception=False), name="dispatch"
)
class ApiCreate(CreateView):

    model = ApiUser

    success_url = reverse_lazy("tournament:apiusers")

    form_class = ApiUserEditForm

    def get_form(self, form_class=None):
        return ApiUserEditForm(
            self.request.user.profile.active, **self.get_form_kwargs()
        )

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        user = form.save(commit=False)
        try:
            user.save()
            key = binascii.hexlify(os.urandom(20)).decode()
            Token.objects.create(user=user, key=make_password(key))
            messages.add_message(
                self.request,
                messages.SUCCESS,
                "A new user was created with token. Please keep the token safe, as it will not be shown again: iyptcc.%d.%s"
                % (user.id, key),
            )
        except IntegrityError:
            messages.add_message(self.request, messages.ERROR, "User already exists")
        form.save()
        return redirect("tournament:apiusers")


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("account.delete_apiuser", raise_exception=False),
    name="dispatch",
)
class ApiDelete(ConfirmedDeleteView):

    redirection = "tournament:apiusers"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            ApiUser, tournament=request.user.profile.tournament, id=kwargs["id"]
        )
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("account.change_apiuser", raise_exception=False),
    name="dispatch",
)
class ApiChange(UpdateView):

    model = ApiUser

    def get_form(self, form_class=None):
        return ApiUserEditForm(
            self.request.user.profile.active, **self.get_form_kwargs()
        )

    success_url = reverse_lazy("tournament:apiusers")

    def get_object(self, queryset=None):
        obj = self.request.user.profile.tournament.apiuser_set.get(id=self.kwargs["id"])
        return obj


@login_required
@permission_required("account.change_apiuser", raise_exception=False)
def refreshtoken(request, apiuser_id):

    if request.method == "POST":

        trn = request.user.profile.tournament
        user = ApiUser.objects.get(tournament=trn, id=apiuser_id)
        user.auth_token.delete()
        key = binascii.hexlify(os.urandom(20)).decode()
        Token.objects.create(user=user, key=make_password(key))
        messages.add_message(
            request,
            messages.SUCCESS,
            "A new token was created. Please keep the token safe, as it will not be shown again: iyptcc.%d.%s"
            % (user.id, key),
        )

        return redirect("tournament:apiusers")

    return HttpResponseNotAllowed(["POST"])


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("tournament.delete_attendee_data", raise_exception=False),
    name="dispatch",
)
class PIIDelete(View):

    def get(self, request):
        trn = request.user.profile.tournament
        try:
            res = AsyncResult(trn.scrub_task_id)
        except:
            return redirect("tournament:properties")
        data = []
        if res.successful():
            data = ["done at : %s" % res.date_done]
            data += res.result
        else:
            data = [res.state]
        return render(request, "tournament/pii.html", context={"data": data})

    def post(self, request, *args, **kwargs):
        if "_delete" in request.POST:
            print("delete the shit")
            scrubPII.delay(request.user.profile.tournament.id)
        else:
            form = ScrubExceptForm(request.user.profile.tournament, request.POST)
            if form.is_valid():
                trn: Tournament
                trn = request.user.profile.tournament
                task = scrubpreparePII.delay(
                    trn.id,
                    attendeeproperty=list(
                        form.cleaned_data["attendeproperty"].values_list(
                            "id", flat=True
                        )
                    ),
                    applicationquestion=list(
                        form.cleaned_data["applicationquestion"].values_list(
                            "id", flat=True
                        )
                    ),
                )

                trn.scrub_task_id = task.id
                trn.save()
            else:
                messages.add_message(request, messages.ERROR, "Form invalid")

        return redirect("tournament:properties")
