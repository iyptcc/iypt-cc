import os
from glob import glob

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_list_or_404, get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView
from django_downloadview import ObjectDownloadView
from mattermostdriver import Driver
from tellme.models import Feedback

from apps.account.models import ActiveUser, ParticipationRole
from apps.dashboard.delete import ConfirmedDeleteView
from apps.feedback.models import ChairFeedbackCriterion, FeedbackGrade
from apps.jury.models import JurorRole
from apps.plan.models import FightRole
from apps.printer.models import PdfTag, Template, TemplateVersion
from apps.registration.models import UserProperty, UserPropertyValue
from apps.team.models import TeamRole
from apps.tournament.models import Phase, Tournament

from .forms import (
    PropertyChoiceFormSet,
    SetPasswordForm,
    TournamentEditForm,
    UDEditForm,
)
from .system import get_information

# Create your views here.


@method_decorator(login_required, name="dispatch")
class TournamentView(ListView):

    model = Tournament

    template_name = "management/list.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("tournament.add_tournament", raise_exception=False),
    name="dispatch",
)
class TournamentCreate(CreateView):

    model = Tournament

    success_url = reverse_lazy("management:list")

    form_class = TournamentEditForm

    def form_valid(self, form):
        trn = form.save(commit=False)
        trn.save()

        for typ, name in JurorRole.ROLE_TYPE:
            JurorRole.objects.create(tournament=trn, type=typ, name=name)

        for typ, name in ParticipationRole.ROLE_TYPE:
            ParticipationRole.objects.create(tournament=trn, type=typ, name=name)

        default_map = {
            TeamRole.CAPTAIN: [ParticipationRole.STUDENT],
            TeamRole.MEMBER: [ParticipationRole.STUDENT],
            TeamRole.LEADER: [ParticipationRole.TEAM_LEADER],
        }
        for typ, name in TeamRole.ROLE_TYPE:
            tr = TeamRole.objects.create(tournament=trn, type=typ, name=name)
            if typ in default_map:
                tr.participation_roles.add(
                    *ParticipationRole.objects.filter(
                        tournament=trn, type__in=default_map[typ]
                    )
                )
                tr.save()

        factor = 3.0
        for typ, name in FightRole.ROLE_TYPE:
            FightRole.objects.create(tournament=trn, type=typ, name=name, factor=factor)
            factor -= 1.0

        PdfTag.objects.create(
            tournament=trn, type=Template.PREVIEW, name="Preview", color="info"
        )
        PdfTag.objects.create(
            tournament=trn, type=Template.RESULTS, name="Results", color="success"
        )
        PdfTag.objects.create(
            tournament=trn, type=Template.RANKING, name="Ranking", color="primary"
        )
        PdfTag.objects.create(
            tournament=trn, type=Template.JURYROUND, name="Jury Round", color="info"
        )
        PdfTag.objects.create(
            tournament=trn, type=Template.INVOICE, name="Invoice", color="default"
        )
        PdfTag.objects.create(tournament=trn, name="Partials", color="warning")
        PdfTag.objects.create(tournament=trn, name="Debug", color="default")
        PdfTag.objects.create(
            tournament=trn,
            type=Template.REGISTRATION,
            name="Registration",
            color="info",
        )
        PdfTag.objects.create(
            tournament=trn, type=Template.TEAM, name="Team", color="success"
        )
        PdfTag.objects.create(
            tournament=trn, type=Template.PERSONS, name="Persons", color="default"
        )

        with open(
            os.path.join(settings.BASE_DIR, "data", "tex_defaults", "base.tex")
        ) as f:
            text = f.read()

            base_templ = Template.objects.create(tournament=trn, name="Base")
            TemplateVersion.objects.create(
                template=base_templ, author=self.request.user.profile, src=text
            )

        for typ, name in Template.TYPE:
            try:
                with open(
                    os.path.join(
                        settings.BASE_DIR, "data", "tex_defaults", "%s.tex" % typ
                    )
                ) as f:
                    text = f.read()
                    templ = Template.objects.create(
                        tournament=trn, name=name, type=typ, parent=base_templ
                    )
                    TemplateVersion.objects.create(
                        template=templ, author=self.request.user.profile, src=text
                    )
            except:
                pass
                # try multi import
                prefix = os.path.join(
                    settings.BASE_DIR, "data", "tex_defaults", "%s." % typ
                )
                files = glob(
                    os.path.join(
                        settings.BASE_DIR, "data", "tex_defaults", "%s.*.*.tex" % typ
                    )
                )
                for gl in files:
                    ps = gl[len(prefix) : -4].split(".")
                    tname = ps[0].replace("-", " ")
                    base = ps[1]
                    if base == "base":
                        parent = base_templ
                    else:
                        parent = None

                    with open(gl) as f:
                        text = f.read()
                        templ = Template.objects.create(
                            tournament=trn, name=tname, type=typ, parent=parent
                        )
                        TemplateVersion.objects.create(
                            template=templ, author=self.request.user.profile, src=text
                        )

        Phase.objects.create(
            tournament=trn,
            name="The Opponent challenges the Reporter for the problem",
            duration=60,
            linked=False,
        )
        Phase.objects.create(
            tournament=trn,
            name="The Reporter accepts or rejects the challenge",
            duration=60,
            linked=False,
        )
        Phase.objects.create(
            tournament=trn,
            name="Preparation of the Reporter",
            duration=300,
            linked=False,
        )
        Phase.objects.create(
            tournament=trn,
            name="Presentation of the report",
            duration=720,
            linked=False,
        )
        Phase.objects.create(
            tournament=trn,
            name="Questions of the Opponent to the Reporter and answers of the Reporter",
            duration=120,
            linked=False,
        )
        Phase.objects.create(
            tournament=trn,
            name="Preparation of the Opponent",
            duration=180,
            linked=False,
        )
        Phase.objects.create(
            tournament=trn,
            name="The Opponent takes the floor",
            duration=240,
            linked=False,
        )
        Phase.objects.create(
            tournament=trn,
            name="Discussion between the Reporter and the Opponent",
            duration=600,
            linked=True,
        )
        Phase.objects.create(
            tournament=trn,
            name="The Opponent summarizes the discussion",
            duration=60,
            linked=False,
        )
        Phase.objects.create(
            tournament=trn,
            name="Questions of the Reviewer to the Reporter and the Opponent and answers to the questions",
            duration=180,
            linked=False,
        )
        Phase.objects.create(
            tournament=trn,
            name="Preparation of the Reviewer",
            duration=120,
            linked=False,
        )
        Phase.objects.create(
            tournament=trn,
            name="The Reviewer takes the floor",
            duration=240,
            linked=False,
        )
        Phase.objects.create(
            tournament=trn,
            name="Concluding remarks of the Reporter",
            duration=120,
            linked=False,
        )
        Phase.objects.create(
            tournament=trn, name="Questions of the Jury", duration=300, linked=False
        )
        Phase.objects.create(tournament=trn, name="Grading", duration=300, linked=False)
        Phase.objects.create(
            tournament=trn, name="Justification of Grades", duration=180, linked=False
        )
        Phase.objects.create(tournament=trn, name="PAUSE", duration=600, linked=False)

        ChairFeedbackCriterion.objects.create(tournament=trn, name="Time management")
        ChairFeedbackCriterion.objects.create(
            tournament=trn, name="Jury question management"
        )
        ChairFeedbackCriterion.objects.create(
            tournament=trn, name="Overall performance"
        )

        FeedbackGrade.objects.create(tournament=trn, name="poor", value=4)
        FeedbackGrade.objects.create(tournament=trn, name="average", value=3)
        FeedbackGrade.objects.create(tournament=trn, name="good", value=2)
        FeedbackGrade.objects.create(tournament=trn, name="excellent", value=1)

        return redirect("management:list")


@login_required
def mm_create_team(request, trn_id):
    if request.method == "POST":
        trn = get_object_or_404(Tournament, id=trn_id)
        mm = Driver(
            {
                "url": settings.MM_URL,
                "token": settings.MM_TOKEN,
                "port": settings.MM_PORT,
            }
        )
        mm.login()
        teams = mm.teams.get_teams()
        if len(list(filter(lambda x: x["name"] == trn.slug, teams))) == 0:
            mm.teams.create_team(
                options={"name": trn.slug, "display_name": trn.name, "type": "I"}
            )
            messages.add_message(
                request, messages.SUCCESS, "Created new MM Team for %s" % trn.name
            )
        else:
            messages.add_message(
                request, messages.WARNING, "MM Team for %s already exists" % trn.name
            )

        return redirect("management:list")

    return HttpResponseNotAllowed(["POST"])


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("tournament.change_tournament", raise_exception=False),
    name="dispatch",
)
class TournamentChange(UpdateView):

    model = Tournament
    success_url = reverse_lazy("management:list")
    form_class = TournamentEditForm

    def get_object(self, queryset=None):
        obj = Tournament.objects.get(id=self.kwargs["id"])
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("tournament.delete_tournament", raise_exception=False),
    name="dispatch",
)
class TournamentDelete(ConfirmedDeleteView):

    redirection = "management:list"

    def get_objects(self, request, *args, **kwargs):
        objs = get_list_or_404(Tournament, pk=kwargs["id"])

        return objs


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("auth.add_user", raise_exception=False), name="dispatch"
)
class UserCreate(CreateView):

    model = User

    fields = ["username", "email", "first_name", "last_name"]
    success_url = reverse_lazy("management:users")

    def form_valid(self, form):

        new_user = User.objects.create_user(**form.cleaned_data)
        ActiveUser.objects.create(user=new_user)

        return redirect("management:users")


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("auth.change_user", raise_exception=False), name="dispatch"
)
class UserUpdate(UpdateView):

    model = User

    fields = ["email", "first_name", "last_name"]
    success_url = reverse_lazy("management:users")

    def get_object(self, queryset=None):
        obj = User.objects.get(profile=self.kwargs["id"])
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("auth.change_user", raise_exception=False), name="dispatch"
)
class SetPassword(View):

    def get(self, request, id):

        auser = get_object_or_404(ActiveUser, id=id)

        form = SetPasswordForm()

        return render(
            request,
            "management/setPassword.html",
            context={"form": form, "auser": auser},
        )

    def post(self, request, id):

        auser = get_object_or_404(ActiveUser, id=id)

        form = SetPasswordForm(request.POST)

        if form.is_valid():

            auser.user.set_password(form.cleaned_data["password"])
            auser.user.save()

            return redirect("management:users")

        return render(
            request,
            "management/setPassword.html",
            context={"form": form, "auser": auser},
        )


@method_decorator(login_required, name="dispatch")
class SystemInfo(View):

    def get(self, request):

        info = get_information(request)

        return render(request, "management/system.html", context={"info": info})


class FeedbackView(ListView):

    template_name = "management/feedback.html"

    paginate_by = 10

    def get_queryset(self):

        return Feedback.objects.all().order_by("-created")


class ScreenshotView(ObjectDownloadView):

    attachment = False

    def get_object(self, queryset=None):
        try:
            obj = Feedback.objects.get(id=self.kwargs["id"]).screenshot
            return obj
        except:
            raise Feedback.DoesNotExist("Screenshot does not exist")


class FeedbackDeleteView(ConfirmedDeleteView):

    redirection = "management:feedback"

    def get_objects(self, request, *args, **kwargs):
        objs = get_list_or_404(Feedback, pk=kwargs["id"])

        return objs


@method_decorator(login_required, name="dispatch")
class ProfileDataView(ListView):

    template_name = "management/properties.html"

    def get_queryset(self):
        return UserProperty.objects.filter()


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("management.change_profile_data", raise_exception=False),
    name="dispatch",
)
class UDChange(UpdateView):

    model = UserProperty

    success_url = reverse_lazy("management:properties")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return UDEditForm(**self.get_form_kwargs())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
        return super().form_valid(form)

    def get_object(self, queryset=None):
        obj = UserProperty.objects.get(id=self.kwargs["id"])
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("management.change_profile_data", raise_exception=False),
    name="dispatch",
)
class UDCreate(CreateView):

    model = UserProperty

    # form_class = ADEditForm

    success_url = reverse_lazy("management:properties")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return UDEditForm(**self.get_form_kwargs())

    def form_valid(self, form):
        try:
            validation = super().form_valid(form)
            # clear all caches
            return validation
        except IntegrityError:
            messages.add_message(
                self.request,
                messages.ERROR,
                "Attribute %s already exists" % form.instance.name,
            )
            return redirect("management:properties")


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("managment.delete_profile_data", raise_exception=False),
    name="dispatch",
)
class UDDelete(ConfirmedDeleteView):

    redirection = "management:properties"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(UserProperty, id=kwargs["id"])
        return obj


@method_decorator(
    permission_required("management.change_profile_data", raise_exception=False),
    name="dispatch",
)
class UDMove(View):
    def post(self, request, id, direction):
        obj = get_object_or_404(UserProperty, id=self.kwargs["id"])
        if direction == "up":
            obj.up()
        if direction == "down":
            obj.down()

        return redirect("management:properties")


def trigger_error(request):
    division_by_zero = 1 / 0
