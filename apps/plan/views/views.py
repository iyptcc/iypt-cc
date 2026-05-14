import csv

import yaml
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views import View
from django_downloadview import ObjectDownloadView
from unidecode import unidecode

from apps.dashboard.delete import ConfirmedDeleteView
from apps.plan.models import StageAttendance, TeamPlaceholder
from apps.printer import context_generator
from apps.printer.models import Pdf, PdfTag, Template
from apps.printer.tasks import render_to_pdf
from apps.printer.utils import _get_next_pdfname
from apps.team.models import Team, TeamMember, TeamRole
from apps.tournament.models import Origin, Problem, ScheduleTemplate

from ...account.models import ActiveUser, Attendee, ParticipationRole
from ..forms import AttendeeCreateImportForm, TeamCreateImportForm, TeamDrawForm
from ..models import Round

# Create your views here.


@login_required
@permission_required("plan.view_plan")
def plan(request):

    rounds = (
        Round.objects.filter(tournament=request.user.profile.tournament)
        .order_by("order")
        .prefetch_related(
            "fight_set__stage_set__stageattendance_set",
            "fight_set__room",
            "fight_set__stage_set__rejections",
            "fight_set__stage_set__stageattendance_set__role",
        )
    )
    return render(request, "plan/plan.html", context={"rounds": rounds})


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("plan.add_fight", raise_exception=False), name="dispatch"
)
class Placeholder(View):

    def get(self, request):

        scheds = ScheduleTemplate.objects.filter(
            teams=request.user.profile.tournament.teamplaceholder_set.count()
        )

        rounds = (
            Round.selectives.filter(tournament=request.user.profile.tournament)
            .order_by("order")
            .prefetch_related(
                "fight_set__stage_set__stageattendance_set__role",
                "fight_set__stage_set__stageattendance_set__team_placeholder",
                "fight_set__room",
            )
        )
        return render(
            request,
            "plan/overview.html",
            context={"rounds": rounds, "schedules": scheds},
        )


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("plan.view_placeholders"), name="dispatch")
class PlaceholderTeams(View):

    def get(self, request):

        realnr = Team.competing.filter(
            tournament=request.user.profile.tournament
        ).count()

        form = TeamDrawForm(request.user.profile.tournament)

        return render(
            request, "plan/phteams.html", context={"form": form, "realnr": realnr}
        )

    @method_decorator(
        permission_required("plan.assign_placeholders", raise_exception=False)
    )
    def post(self, request):

        realnr = Team.competing.filter(
            tournament=request.user.profile.tournament
        ).count()

        form = TeamDrawForm(request.user.profile.tournament, request.POST)

        if form.is_valid():
            chgd = []
            for k in form.changed_data:
                # print("ph:%s to: %s"%(form.placeholders[k],form.cleaned_data[k]))

                try:
                    if form.cleaned_data[k].teamplaceholder:
                        # print("already has a placeholder")
                        oldholder = form.cleaned_data[k].teamplaceholder
                        oldholder.team = None
                        oldholder.save()
                except:
                    pass
                form.placeholders[k].team = form.cleaned_data[k]
                form.placeholders[k].save()
                chgd.append(form.placeholders[k].name)

            messages.add_message(
                request, messages.INFO, "%s assigned" % (", ".join(chgd))
            )

        return render(
            request, "plan/phteams.html", context={"form": form, "realnr": realnr}
        )


@login_required
@permission_required("plan.assign_placeholders")
def drawTeam(request, team_id, placeholder_nr):
    if request.method == "POST":
        trn = request.user.profile.tournament
        team = get_object_or_404(Team, id=team_id, tournament=trn)
        placeholder = get_object_or_404(
            TeamPlaceholder, name="Team %d" % int(placeholder_nr), tournament=trn
        )

        try:
            ph = team.teamplaceholder
            ph.team = None
            ph.save()
        except:
            pass

        placeholder.team = team
        placeholder.save()

        return JsonResponse({"assigned": team.pk})


@login_required
@permission_required("plan.assign_placeholders")
def drawdelTeam(request, team_id):
    if request.method == "POST":
        trn = request.user.profile.tournament
        team = get_object_or_404(Team, id=team_id, tournament=trn)

        ph = team.teamplaceholder
        ph.team = None
        ph.save()

        return JsonResponse({"assigned": team.pk})


@login_required
@permission_required("plan.assign_placeholders")
def phbeamercontrol(request):

    trn = request.user.profile.tournament

    phteams = trn.teamplaceholder_set.all()
    teams = trn.team_set(manager="competing").all().order_by("origin__name")
    # print(teams)
    return render(
        request, "plan/beamerControl.html", context={"teams": teams, "phteams": phteams}
    )


@login_required
@permission_required("plan.assign_placeholders")
def phbeamer(request):

    trn = request.user.profile.tournament

    ro = trn.round_set.first()
    return render(
        request, "plan/beamerDraw.html", context={"round": ro, "wide": trn.draw_wide}
    )


@login_required
@permission_required("plan.add_teamplaceholder", raise_exception=False)
def phteamsgen(request):

    if request.method == "POST":
        trn = request.user.profile.tournament

        realnr = Team.competing.filter(tournament=trn).count()
        for i in range(1, realnr + 1):
            TeamPlaceholder.objects.get_or_create(tournament=trn, name="Team %d" % (i,))

    return redirect("plan:phteams")


@login_required
@permission_required("plan.delete_teamplaceholder", raise_exception=False)
def phteamsdel(request):

    if request.method == "POST":
        trn = request.user.profile.tournament
        tp = TeamPlaceholder.objects.filter(tournament=trn)
        if "_last" in request.POST:
            tp.last().delete()
        elif "_all" in request.POST:
            tp.delete()

    return redirect("plan:phteams")


@login_required
@permission_required("plan.apply_schedule", raise_exception=False)
@transaction.atomic
def phplanapply(request):

    if request.method == "POST":
        trn = request.user.profile.tournament
        sas = (
            StageAttendance.objects.filter(stage__fight__round__tournament=trn)
            .values("team")
            .distinct()
        )
        if sas.count() == 1 and sas[0]["team"] == None:

            if not TeamPlaceholder.objects.filter(tournament=trn, team=None).exists():

                for sa in StageAttendance.objects.filter(
                    stage__fight__round__tournament=trn
                ):
                    sa.team = sa.team_placeholder.team
                    sa.save()

                messages.add_message(
                    request,
                    messages.SUCCESS,
                    "Teams successfully mapped according to draw",
                )
                return redirect("plan:plan")

            messages.add_message(
                request, messages.ERROR, "Unassigned placeholder teams found"
            )
            return redirect("plan:placeholder")

        messages.add_message(request, messages.ERROR, "Already assigned fights found")
        return redirect("plan:placeholder")

    return HttpResponseNotAllowed(["POST"])


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("plan.delete_round", raise_exception=False), name="dispatch"
)
class PhPlanDelete(ConfirmedDeleteView):

    redirection = "plan:placeholder"

    def get_objects(self, request, *args, **kwargs):
        return Round.objects.filter(tournament=request.user.profile.tournament)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("plan.delete_round", raise_exception=False), name="dispatch"
)
class RoundFightDelete(ConfirmedDeleteView):

    redirection = "plan:plan"

    def get_objects(self, request, *args, **kwargs):
        return Round.objects.get(
            tournament=request.user.profile.tournament, order=kwargs["round"]
        ).fight_set.all()


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("plan.delete_final", raise_exception=False), name="dispatch"
)
class FinalDelete(ConfirmedDeleteView):

    redirection = "plan:final"

    def get_objects(self, request, *args, **kwargs):
        try:
            return Round.finals.get(
                tournament=request.user.profile.tournament
            ).fight_set.all()
        except Round.DoesNotExist:
            return Round.objects.none()


@login_required
def genpdfteamround(request, round_nr):

    if request.method == "POST":

        trn = request.user.profile.tournament
        round = get_object_or_404(Round, order=round_nr, tournament=trn)

        context = context_generator.teamround(round)

        fileprefix = "team-round-%d-v" % (round.order)

        pdf = Pdf.objects.create(
            name="%s%d" % (fileprefix, _get_next_pdfname(trn, fileprefix)),
            tournament=trn,
        )

        res = render_to_pdf.delay(
            trn.default_templates.get(type=Template.TEAMROUND).id,
            pdf.id,
            context=context,
        )

        pdf.task_id = res.id
        pdf.save()

        try:
            pdf.tags.add(PdfTag.objects.get(tournament=trn, type=Template.TEAMROUND))
        except:
            messages.add_message(
                request, messages.WARNING, "No PDF Tag found for Team Round"
            )

        round.pdf_teamplan = pdf
        round.save()

        return redirect("plan:plan")

    return HttpResponseNotAllowed(["POST"])


@method_decorator(login_required, name="dispatch")
# @method_decorator(permission_required("plan.view_jury"), name='dispatch')
class PdfTeamView(ObjectDownloadView):

    attachment = False

    mimetype = "application/pdf"

    def get_object(self, queryset=None):
        try:
            obj = Round.objects.get(
                tournament=self.request.user.profile.tournament,
                order=self.kwargs["round"],
            ).pdf_teamplan
            if not obj.status in [Pdf.SUCCESS, Pdf.UPLOAD]:
                raise Http404("File not yet available")
            return obj.file
        except:
            raise Http404("File does not exist")


@login_required
def genpdfproblemselect(request, round_nr):

    if request.method == "POST":

        trn = request.user.profile.tournament
        round = get_object_or_404(Round, order=round_nr, tournament=trn)

        context = context_generator.problem_select(round)

        fileprefix = "problem-selection-round-%d-v" % (round.order)

        pdf = Pdf.objects.create(
            name="%s%d" % (fileprefix, _get_next_pdfname(trn, fileprefix)),
            tournament=trn,
        )

        res = render_to_pdf.delay(
            trn.default_templates.get(type=Template.PROBLEMSELECT).id,
            pdf.id,
            context=context,
        )

        pdf.task_id = res.id
        pdf.save()

        try:
            pdf.tags.add(
                PdfTag.objects.get(tournament=trn, type=Template.PROBLEMSELECT)
            )
        except:
            messages.add_message(
                request, messages.WARNING, "No PDF Tag found for Problem Select"
            )

        round.pdf_problem_select = pdf
        round.save()

        return redirect("plan:plan")

    return HttpResponseNotAllowed(["POST"])


@method_decorator(login_required, name="dispatch")
# @method_decorator(permission_required("plan.view_jury"), name='dispatch')
class PdfProblemSelect(ObjectDownloadView):

    attachment = False

    mimetype = "application/pdf"

    def get_object(self, queryset=None):
        try:
            obj = Round.objects.get(
                tournament=self.request.user.profile.tournament,
                order=self.kwargs["round"],
            ).pdf_problem_select
            if not obj.status in [Pdf.SUCCESS, Pdf.UPLOAD]:
                raise Http404("File not yet available")
            return obj.file
        except:
            raise Http404("File does not exist")


@login_required
@permission_required("plan.view_plan")
def jurydatadump(request):
    trn = request.user.profile.tournament

    response = HttpResponse(content_type="text/yaml")
    response["Content-Disposition"] = 'filename="result.yml"'

    data = {}
    rooms = {}
    for room in trn.room_set.all():
        rooms[room.id] = {"name": room.name}
    data["rooms"] = rooms
    teams = {}
    for team in trn.team_set.all():
        teams[team.id] = {"origin": {"name": team.origin.name}}
    data["teams"] = teams
    rounds = []
    for round in trn.round_set.all():
        r = {"type": round.type, "order": round.order}
        fights = []
        for fight in round.fight_set.all():
            f = {"room": fight.room_id, "stages": []}
            for stage in fight.stage_set.all():
                st = {"order": stage.order}
                for att in stage.stageattendance_set.all():
                    st[att.role.type] = att.team_id
                f["stages"].append(st)
            fights.append(f)
        r["fights"] = fights
        rounds.append(r)
    data["rounds"] = rounds
    yaml.dump(data, response)
    return response


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("account.add_attendee"), name="dispatch")
class ImportAttendees(View):

    def get(self, request):

        form = AttendeeCreateImportForm(request.user.profile.tournament)

        return render(request, "plan/attendeecsv.html", context={"form": form})

    def post(self, request):

        form = AttendeeCreateImportForm(request.user.profile.tournament, request.POST)

        if form.is_valid():
            if "_save" in request.POST:
                # print("save", form.cleaned_data)

                reader = csv.DictReader(form.cleaned_data["input"].splitlines())
                for row in reader:
                    lno = form.row_key(row)
                    first_name = row[form.cleaned_data["first_name_column"]].strip()
                    last_name = row[form.cleaned_data["last_name_column"]].strip()
                    email = form.cleaned_data["default_email"]
                    if (
                        "email_column" in form.cleaned_data
                        and form.cleaned_data["email_column"]
                    ):
                        email = row.get(form.cleaned_data["email_column"], "").strip()
                        if not len(email):
                            email = form.cleaned_data["default_email"]
                    role = form.cleaned_data["assigned_role"]

                    if form.cleaned_data.get(f"import_{lno}") is True:
                        if form.cleaned_data.get(f"user_{lno}") is None:
                            # print("create user", first_name, last_name, email)

                            name = f"{first_name} {last_name}"
                            username = "%s-%s" % (
                                request.user.profile.tournament.slug,
                                slugify(unidecode(name)),
                            )
                            user = User.objects.create_user(
                                username,
                                first_name=first_name,
                                last_name=last_name,
                                email=email,
                            )

                            auser = ActiveUser.objects.get_or_create(user=user)[0]
                        else:
                            # print("use active", form.cleaned_data[f"user_{lno}"] )
                            auser = form.cleaned_data[f"user_{lno}"]

                        attendee = Attendee.objects.get_or_create(
                            active_user=auser,
                            tournament=request.user.profile.tournament,
                        )[0]

                        attendee.roles.add(role)

                        # print("make attendee", row)
                        # print("assign role", role)
                return redirect("plan:persons")

        return render(request, "plan/attendeecsv.html", context={"form": form})


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("tournament.add_origin"), name="dispatch")
class ImportTeams(View):

    def get(self, request):

        form = TeamCreateImportForm(request.user.profile.tournament)

        return render(request, "plan/teamcsv.html", context={"form": form})

    def post(self, request):

        trn = request.user.profile.tournament
        form = TeamCreateImportForm(trn, request.POST)

        if form.is_valid():
            if "_create_teams" in request.POST:

                reader = csv.DictReader(form.cleaned_data["input"].splitlines())
                teamset = set()
                teams = {}
                for row in reader:
                    team = row[form.cleaned_data["team_column"]].strip()
                    teamset.add(team)

                for team in teamset:
                    if form.cleaned_data.get(f"team_{form.row_key(team)}") is None:
                        print("create", team)
                        ori = Origin.objects.create(name=team, tournament=trn)
                        teams[team] = ori
                    else:
                        teams[team] = form.cleaned_data[f"team_{form.row_key(team)}"]

                print(teams)

            if "_save" in request.POST:
                reader = csv.DictReader(form.cleaned_data["input"].splitlines())
                for row in reader:
                    team = row[form.cleaned_data["team_column"]].strip()
                    role_str = row[form.cleaned_data["role_column"]].strip()
                    att: Attendee = form.cleaned_data[f"member_{form.row_key(row)}"]

                    role: TeamRole = form.cleaned_data.get(
                        f"role_{form.row_key(role_str)}"
                    )
                    origin = form.cleaned_data[f"team_{form.row_key(team)}"]

                    team, cre = Team.objects.get_or_create(
                        origin=origin, tournament=trn
                    )

                    print("add", att, role, team)
                    try:
                        tm = TeamMember.objects.get(attendee=att, team=team)
                        tm.role = role
                        tm.save()
                    except TeamMember.DoesNotExist:
                        TeamMember.objects.create(attendee=att, team=team, role=role)

                    for pr in role.participation_roles.all():
                        att.roles.add(pr)

                    try:
                        problem = int(row.get(form.cleaned_data["problem_column"]))
                        prob = Problem.objects.get(tournament=trn, number=problem)
                        team.aypt_prepared_problems.add(prob)
                    except Exception as e:
                        print(e)

                return redirect("plan:teams")

                #    attnd.roles.add(prstudent)

        return render(request, "plan/teamcsv.html", context={"form": form})
