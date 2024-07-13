import xlsxwriter
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.forms import modelformset_factory
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views import View

from apps.jury.models import Juror, JurorRole
from apps.plan.models import Fight, Round, Stage
from apps.postoffice.models import Template
from apps.postoffice.utils import render_template

from .forms import ChairFeedbackForm, JurorFeedbackForm
from .models import ChairFeedback, Feedback

# Create your views here.


@login_required
def plan(request):

    editall = request.user.has_perm("feedback.change_all_feedback")
    rs = []
    rounds = Round.objects.filter(tournament=request.user.profile.tournament).order_by(
        "order"
    )
    for round in rounds:
        fs = []
        for f in round.fight_set.select_related("room").all():
            fi = {"name": f.room.name, "pk": f.pk}
            fi["teams"] = f.stage_set.get(order=1).attendees.all()
            for team in fi["teams"]:
                if (
                    team.teammember_set.filter(
                        role__in=request.user.profile.tournament.feedback_permitted_roles.all()
                    )
                    .filter(attendee=request.user.profile.active)
                    .exists()
                ):
                    if request.user.profile.tournament.feedback_locked_by_assistants:
                        if not f.locked:
                            fi["active"] = team
                    else:
                        if not f.round.feedback_locked:
                            fi["active"] = team
            fs.append(fi)
        rs.append(fs)

    return render(
        request, "feedback/plan.html", context={"rounds": rs, "editall": editall}
    )


class FeedbackPermMixin(UserPassesTestMixin):
    def test_func(self):
        if self.request.user.has_perm("feedback.change_all_feedback"):
            return True
        try:
            fi = Fight.objects.get(pk=self.request.resolver_match.kwargs["fight_id"])
            team = fi.stage_set.get(order=1).attendees.get(
                origin__slug=self.request.resolver_match.kwargs["t_slug"]
            )
            if team.teammember_set.filter(
                role__in=self.request.user.profile.tournament.feedback_permitted_roles.all()
            ).get(attendee=self.request.user.profile.active):
                if self.request.user.profile.tournament.feedback_locked_by_assistants:
                    if fi.locked:
                        return False
                return not fi.round.feedback_locked
        except Exception:
            return False

        return False


@method_decorator(login_required, name="dispatch")
class FeedbackChange(FeedbackPermMixin, View):

    def parse(self, fight_id, t_slug):
        fight = get_object_or_404(
            Fight, id=fight_id, round__tournament=self.request.user.profile.tournament
        )
        team = fight.stage_set.get(order=1).attendees.get(origin__slug=t_slug)
        return fight, team

    def get_formset(self, fight_id, t_slug, post=None):
        fight, team = self.parse(fight_id, t_slug)

        js = fight.jurorsession_set(manager="voting").all()
        qs = Feedback.objects.filter(jurorsession__in=js, team=team)
        initials = []
        for j in js:
            if not qs.filter(jurorsession=j).exists():
                initials.append({"jurorsession": j, "team": team})

        JurorFeedbackFormSet = modelformset_factory(
            Feedback, form=JurorFeedbackForm, extra=len(initials)
        )

        if post is not None:
            return JurorFeedbackFormSet(post, queryset=qs, initial=initials)
        return JurorFeedbackFormSet(queryset=qs, initial=initials)

    def get_form(self, fight_id, t_slug, post=None):
        fight, team = self.parse(fight_id, t_slug)
        cs = fight.jurorsession_set(manager="chair").first()
        try:
            cf = ChairFeedback.objects.get(jurorsession=cs, team=team)
        except ChairFeedback.DoesNotExist:
            cf = None

        if post is not None:
            return ChairFeedbackForm(
                post,
                instance=cf,
                initial={"jurorsession": cs, "team": team},
                tournament=self.request.user.profile.tournament,
            )
        return ChairFeedbackForm(
            instance=cf,
            initial={"jurorsession": cs, "team": team},
            tournament=self.request.user.profile.tournament,
        )

    def get(self, request, fight_id, t_slug):

        return render(
            request,
            "feedback/feedback_form.html",
            context={
                "formset": self.get_formset(fight_id, t_slug),
                "form": self.get_form(fight_id, t_slug),
                "fightteam": self.parse(fight_id, t_slug),
            },
        )

    def post(self, request, fight_id, t_slug):

        formset = self.get_formset(fight_id, t_slug, request.POST)
        if formset.is_valid():
            formset.save()

        form = self.get_form(fight_id, t_slug, post=request.POST)
        if form.is_valid():
            form.save()

        return render(
            request,
            "feedback/feedback_form.html",
            context={
                "formset": formset,
                "form": form,
                "fightteam": self.parse(fight_id, t_slug),
            },
        )


@login_required
@permission_required("feedback.stats")
def overview(request):  # noqa: max-complexity: 13

    jurors = Juror.objects.filter(
        attendee__tournament=request.user.profile.tournament
    ).prefetch_related(
        "attendee__active_user__user", "jurorsession_set__feedback_set__grade"
    )

    chairs = (
        jurors.filter(jurorsession__role__type=JurorRole.CHAIR)
        .prefetch_related(
            "jurorsession_set__chairfeedback_set__chairfeedbackgrade_set__grade"
        )
        .distinct()
    )

    criteria = request.user.profile.tournament.chairfeedbackcriterion_set.all()

    format = request.GET.get("format", "").lower()
    if format == "xlsx":
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'filename="feedback.xlsx"'

        workbook = xlsxwriter.Workbook(response)
        chairsheet = workbook.add_worksheet("Chairs")
        chairsheet.write(0, 0, "Round")
        chairsheet.write(0, 1, "Room")
        chairsheet.write(0, 2, "Team")
        chairsheet.write(0, 3, "Name")
        for pi, p in enumerate(criteria):
            chairsheet.write(0, 4 + pi, p.name)
        chairsheet.write(0, 4 + len(criteria), "Comment")
        row = 1
        for juror in chairs:
            for ro in request.user.profile.tournament.round_set(
                manager="selectives"
            ).all():
                ro: Round
                for fight in ro.fight_set.all():
                    for js in juror.jurorsession_set.filter(fight=fight):
                        st1: Stage = fight.stage_set.first()
                        for team in st1.attendees.all():
                            for fb in js.chairfeedback_set.filter(team=team):
                                chairsheet.write(row, 0, ro.order)
                                chairsheet.write(row, 1, fight.room.name)
                                chairsheet.write(row, 2, team.origin.name)
                                chairsheet.write(row, 3, juror.attendee.full_name)
                                for ci, c in enumerate(criteria):
                                    for grade in fb.chairfeedbackgrade_set.filter(
                                        criterion=c
                                    ):
                                        chairsheet.write(row, 4 + ci, grade.grade.value)
                                chairsheet.write(row, 4 + len(criteria), fb.comment)
                                row += 1

        return response
    else:
        return render(
            request,
            "feedback/overview.html",
            context={
                "jurors": jurors,
                "chairs": chairs,
                "criteria": criteria,
                "rounds": request.user.profile.tournament.round_set(
                    manager="selectives"
                ).all(),
            },
        )


@method_decorator(
    permission_required("feedback.stats", raise_exception=False), name="dispatch"
)
class Email(View):

    def get(self, request):

        return None

        jurors = Juror.objects.filter(
            attendee__tournament=request.user.profile.tournament
        ).prefetch_related(
            "attendee__active_user__user", "jurorsession_set__feedback_set__grade"
        )[
            :10
        ]

        context = []

        for j in jurors:
            context.append(
                {"first_name": j.attendee.first_name, "last_name": j.attendee.last_name}
            )

        srcs = render_template(
            request.user.profile.tournament.default_templates.get(
                type=Template.JURORFEEDBACK
            ).id,
            context,
        )

        emails = []
        for idx, src in enumerate(srcs):
            emails.append(
                {
                    "email": jurors[idx].attendee.active_user.user.email,
                    "subject": src[0],
                    "body": src[1],
                }
            )

        context["srcs"] = emails
