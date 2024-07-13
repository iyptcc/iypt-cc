import csv

import yaml
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotFound,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django_downloadview import ObjectDownloadView

from apps.jury.models import GradingSheet, Juror
from apps.plan.models import Event, Fight, Room, Round, Stage
from apps.printer.models import Pdf
from apps.team.models import Team
from apps.tournament.models import Origin, Tournament

# Create your views here.
from ..virtual.bbb import is_meeting_running, join
from ..virtual.forms import NameForm
from .utils import (
    _best_members,
    _fightdata,
    _fightpreview,
    _fightresult,
    _gradedump,
    _jurystats,
    _member_rank,
    _ranking,
    _resultdump,
)


def listTournaments(request):

    if request.user.is_authenticated and request.user.profile.tournament:
        return redirect("result:plan", t_slug=request.user.profile.tournament.slug)

    ts = []
    for trn in Tournament.objects.filter(
        results_access__in=[Tournament.RESULTS_PUBLIC, Tournament.RESULTS_PASSWORD]
    ):
        t = {
            "name": trn.name,
            "slug": trn.slug,
            "protected": trn.results_access == Tournament.RESULTS_PASSWORD,
            "unlock": request.session.get("results-auth-%s" % trn.slug, False),
        }
        ts.append(t)

    return render(request, "result/list.html", context={"tournaments": ts})


def _view_grades_perm(request, tournament):

    if tournament.results_access == Tournament.RESULTS_PUBLIC:
        return True

    elif tournament.results_access == Tournament.RESULTS_PERMISSION:
        if request.user.has_perm("jury.view_results"):
            if request.user.profile.tournament == tournament:
                return True
            else:
                return redirect("account:tournament")

    elif tournament.results_access == Tournament.RESULTS_PASSWORD:

        if request.user.is_authenticated:
            if request.user.has_perm("jury.view_results"):
                if request.user.profile.tournament == tournament:
                    return True
                else:
                    return redirect("account:tournament")

        if request.session.get("results-auth-%s" % tournament.slug, False):
            return True
        else:
            return redirect("dashboard:simplelogin", t_slug=tournament.slug)

    return render(request, "result/empty.html")


def _view_slides_perm(request, tournament):

    if tournament.slides_public:
        return True
    else:
        if request.user.profile.tournament == tournament:
            return True

    return render(request, "result/empty.html")


def plan(request, t_slug):

    tournament = get_object_or_404(Tournament, slug=t_slug)

    # authz
    auth = _view_grades_perm(request, tournament)
    if type(auth) != bool:
        return auth

    rounds = Round.objects.filter(tournament=tournament).order_by("order")

    grades = []

    for round in rounds:
        grades_r = []
        for fight in round.fight_set.all():

            meta = {
                "order": fight.round.order,
                "final": fight.round.type == Round.FINAL,
            }

            if fight.publish_grades:
                res = _fightresult(fight)
                res.update(meta)
                grades_r.append(res)
            elif fight.publish_preview:
                stage1 = fight.stage_set.all()[0]
                teams = [stage1.rep_attendance.team, stage1.opp_attendance.team]
                if fight.round.review_phase:
                    teams.append(stage1.rev_attendance.team)
                if stage1.obs_attendance:
                    teams.append(stage1.obs_attendance.team)
                res = {
                    "room": fight.room.name,
                    "teams": teams,
                    "preview": _fightpreview(fight),
                }
                res.update(meta)
                grades_r.append(res)

        if len(grades_r) > 0:
            grades.append(grades_r)

    return render(
        request,
        "result/plan.html",
        context={"rounds": grades, "tournament": tournament.slug},
    )


def schedule(request, t_slug):

    tournament = get_object_or_404(Tournament, slug=t_slug)

    # authz
    auth = _view_grades_perm(request, tournament)
    if type(auth) != bool:
        return auth

    rounds = (
        Round.objects.filter(tournament=tournament, publish_schedule=True)
        .order_by("order")
        .prefetch_related(
            "fight_set__stage_set__stageattendance_set",
            "fight_set__room",
            "fight_set__stage_set__rejections",
            "fight_set__stage_set__stageattendance_set__role",
        )
    )

    virutal_role = tournament.fight_room_public_role
    clock = tournament.public_clock

    return render(
        request,
        "result/schedule.html",
        context={
            "rounds": rounds,
            "tournament": tournament.slug,
            "virtual": virutal_role,
            "clock": clock,
        },
    )


def slides(request, t_slug):

    tournament = get_object_or_404(Tournament, slug=t_slug)

    # authz
    auth = _view_slides_perm(request, tournament)
    if type(auth) != bool:
        return auth

    rounds = (
        Round.objects.filter(tournament=tournament)
        .order_by("order")
        .prefetch_related(
            "fight_set__stage_set__stageattendance_set",
            "fight_set__room",
            "fight_set__stage_set__rejections",
            "fight_set__stage_set__stageattendance_set__role",
        )
    )

    return render(
        request,
        "result/slides.html",
        context={
            "rounds": rounds,
            "tournament": tournament.slug,
        },
    )


def teams(request, t_slug):

    tournament = get_object_or_404(Tournament, slug=t_slug)
    # authz
    auth = _view_grades_perm(request, tournament)
    if type(auth) != bool:
        return auth

    teams = Origin.objects.filter(tournament=tournament, publish_participation=True)
    events = Event.objects.filter(tournament=tournament, public=True)

    return render(
        request,
        "result/teams.html",
        context={"teams": teams, "events": events, "tournament": tournament.slug},
    )


def fight_table(request, t_slug, round_nr, room_slug):

    tournament = get_object_or_404(Tournament, slug=t_slug)
    ro = get_object_or_404(Round, order=round_nr, tournament=tournament)
    room = get_object_or_404(Room, slug=room_slug, tournament=tournament)

    auth = _view_grades_perm(request, tournament)
    if type(auth) != bool:
        return auth

    fight = ro.fight_set.get(room=room)
    if not fight.publish_grades:
        return HttpResponseNotFound("")

    tmpl = "result/fight_table_norev.html"
    if ro.review_phase:
        tmpl = "result/fight_table.html"
    return render(
        request,
        tmpl,
        context={"fight": _fightdata(fight), "tournament": tournament.slug},
    )


def team(request, t_slug, origin_slug):

    tournament = get_object_or_404(Tournament, slug=t_slug)
    team = get_object_or_404(Team, tournament=tournament, origin__slug=origin_slug)

    auth = _view_grades_perm(request, tournament)
    if type(auth) != bool:
        return auth

    grades = []

    for fight in (
        Fight.objects.filter(stage__attendees=team).distinct().order_by("round")
    ):
        if fight.publish_grades:
            fc = _fightdata(fight)
            fc["result"] = _fightresult(fight)["result"]
            fc["final"] = fight.round.type == Round.FINAL
            grades.append(fc)
        elif fight.publish_preview:
            stage1 = fight.stage_set.all()[0]
            teams = [stage1.rep_attendance.team, stage1.opp_attendance.team]
            if fight.round.review_phase:
                teams.append(stage1.rev_attendance.team)
            if stage1.obs_attendance:
                teams.append(stage1.obs_attendance.team)
            grades.append(
                {
                    "room": fight.room.name,
                    "round": fight.round.order,
                    "teams": teams,
                    "preview": _fightpreview(fight),
                }
            )

    return render(
        request,
        "result/team.html",
        context={
            "fights": grades,
            "team": team,
            "teamid": team.id,
            "tournament": tournament.slug,
        },
    )


def fight(request, t_slug, round_nr, room_slug):

    tournament = get_object_or_404(Tournament, slug=t_slug)
    ro = get_object_or_404(Round, order=round_nr, tournament=tournament)
    room = get_object_or_404(Room, slug=room_slug, tournament=tournament)

    fight = ro.fight_set.get(room=room)

    auth = _view_grades_perm(request, tournament)
    if type(auth) != bool:
        return auth

    fail = True
    fc = None
    if fight.publish_grades:
        fc = _fightdata(fight)
        fc["result"] = _fightresult(fight)["result"]
        fc["final"] = fight.round.type == Round.FINAL
        fc["partial_grades"] = fight.pdf_partial_grades
        fail = False
    fp = None
    if fight.publish_preview:
        fp = _fightpreview(fight)
        fail = False

    if fail:
        return HttpResponseNotFound("")

    return render(
        request,
        "result/fight.html",
        context={
            "fight": fc,
            "tournament": tournament.slug,
            "preview": fp,
            "round": fight.round.order,
            "room": fight.room.name,
        },
    )


def clock(request, t_slug, round_nr, room_slug, stage_nr):
    tournament = get_object_or_404(Tournament, slug=t_slug, public_clock=True)
    ro = get_object_or_404(Round, order=round_nr, tournament=tournament)
    room = get_object_or_404(Room, slug=room_slug, tournament=tournament)
    fight = ro.fight_set.get(room=room)

    return render(
        request,
        "result/fightclock.xml",
        context={
            "id": fight.id,
            "stage": stage_nr,
            "phases": tournament.phase_set.all(),
        },
        content_type="image/svg+xml",
    )


class PublicRoomInviteView(View):

    def get(self, request, t_slug, round_nr, room_slug):

        tournament = get_object_or_404(Tournament, slug=t_slug)
        ro = get_object_or_404(Round, order=round_nr, tournament=tournament)
        room = get_object_or_404(Room, slug=room_slug, tournament=tournament)
        # fight = ro.fight_set.get(room=room)

        auth = _view_grades_perm(request, tournament)
        if type(auth) != bool:
            return auth

        if tournament.fight_room_public_role is not None:
            form = NameForm()
            return render(request, "virtual/join.html", context={"form": form})
        else:
            return redirect("result:plan", t_slug)

    def post(self, request, t_slug, round_nr, room_slug):
        tournament = get_object_or_404(Tournament, slug=t_slug)
        ro = get_object_or_404(Round, order=round_nr, tournament=tournament)
        room = get_object_or_404(Room, slug=room_slug, tournament=tournament)
        fight = ro.fight_set.get(room=room)

        auth = _view_grades_perm(request, tournament)
        if type(auth) != bool:
            return auth

        if tournament.fight_room_public_role is not None:
            form = NameForm(request.POST)
            if form.is_valid():
                if all(is_meeting_running(fight)):
                    link = join(
                        fight,
                        form.cleaned_data["name"],
                        tournament.fight_room_public_role,
                    )
                    return render(request, "virtual/join.html", context={"link": link})
                else:
                    return render(request, "virtual/wait.html", context={})

            return render(request, "virtual/join.html", context={"form": form})
        else:
            return redirect("result:plan", t_slug)


class PdfPartialView(ObjectDownloadView):

    attachment = False

    mimetype = "application/pdf"

    def get_object(self, queryset=None):

        try:
            tournament = get_object_or_404(Tournament, slug=self.kwargs["t_slug"])
            ro = get_object_or_404(
                Round, order=self.kwargs["round_nr"], tournament=tournament
            )
            room = get_object_or_404(
                Room, slug=self.kwargs["room_slug"], tournament=tournament
            )

            auth = _view_grades_perm(self.request, tournament)
            if type(auth) != bool:
                raise Http404("File does not exist")

            fight = ro.fight_set.get(room=room)

            obj = fight.pdf_partial_grades
            if not obj.status in [Pdf.SUCCESS, Pdf.UPLOAD]:
                raise Http404("File not yet available")
            return obj.file
        except:
            raise Http404("File not found")


class SinglePartialView(ObjectDownloadView):

    attachment = False

    def get_object(self, queryset=None):
        try:
            tournament = get_object_or_404(Tournament, slug=self.kwargs["t_slug"])
            print("get ", tournament, "id", self.kwargs["sheet_id"])
            obj = GradingSheet.objects.get(
                stage__fight__round__tournament=tournament, id=self.kwargs["sheet_id"]
            )

            auth = _view_grades_perm(self.request, obj.stage.fight.round.tournament)
            if type(auth) != bool:
                raise Http404("File not found")

            if not obj.stage.fight.publish_partials:
                raise Http404("File not found")

            file = obj.full
            return file
        except Exception as e:
            raise Http404("File not found")


class SlidesView(ObjectDownloadView):

    attachment = False

    def get_object(self, queryset=None):
        try:
            tournament = get_object_or_404(Tournament, slug=self.kwargs["t_slug"])
            obj = Stage.objects.get(
                fight__round__tournament=tournament, id=self.kwargs["stage_id"]
            )

            auth = _view_slides_perm(self.request, obj.fight.round.tournament)
            if type(auth) != bool:
                raise Http404("File not found")

            if not obj.fight.publish_slides:
                raise Http404("File not found")

            file = obj.pdf_presentation
            return file
        except Exception as e:
            raise Http404("File not found")


def rank(request, t_slug):

    tournament = get_object_or_404(Tournament, slug=t_slug)

    rounds = Round.selectives.filter(tournament=tournament).order_by("order")

    auth = _view_grades_perm(request, tournament)
    if type(auth) != bool:
        return auth

    grades = _ranking(rounds)

    final_rank = None

    final = Round.finals.filter(tournament=tournament)
    if final.exists():
        final = final.first()
        if final.publish_ranking:
            final_rank = _fightresult(final.fight_set.first())

    return render(
        request,
        "result/rank.html",
        context={
            "rounds": reversed(grades),
            "final": final_rank,
            "tournament": tournament.slug,
        },
    )


@login_required
@permission_required("jury.stats")
def jurystats(request, t_slug):
    trn = get_object_or_404(Tournament, slug=t_slug)

    auth = _view_grades_perm(request, trn)
    if type(auth) != bool:
        return auth

    show_email = False
    if request.user.has_perm("tournament.app_jury"):
        show_email = True
    print(request.GET)
    format = request.GET.get("format", "").lower()

    stats = _jurystats(trn, emails=show_email)

    if format == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'filename="jurystats.csv"'
        writer = csv.DictWriter(response, fieldnames=stats["jurors"][0].keys())
        print(stats)
        writer.writeheader()
        for row in stats["jurors"]:
            writer.writerow(row)
        return response
    else:
        return render(request, "result/jurystats.html", context=stats)


@login_required
@permission_required("jury.grade_dump")
def gradedump(request, t_slug):
    trn = get_object_or_404(Tournament, slug=t_slug)

    auth = _view_grades_perm(request, trn)
    if type(auth) != bool:
        return auth

    response = HttpResponse(content_type="text/csv")
    # response = HttpResponse(content_type='text/plain')
    # response['Content-Disposition'] = 'attachment; filename="grades.csv"'
    response["Content-Disposition"] = 'filename="grades.csv"'

    writer = csv.writer(response)
    grades = _gradedump(trn)
    print(grades)
    for row in grades:
        writer.writerow(row)

    return response


def resultdump(request, t_slug):
    trn = get_object_or_404(Tournament, slug=t_slug)

    auth = _view_grades_perm(request, trn)
    if type(auth) != bool:
        return auth

    response = HttpResponse(content_type="text/yaml")
    response["Content-Disposition"] = f'filename="result-{t_slug}.yml"'

    yaml.dump(_resultdump(trn), response)

    # return render(request, "printer/error.html", context={"out":yaml.dump(trn)})
    return response


@login_required
@permission_required("jury.member_rank")
def memberrank(request, t_slug):
    trn = get_object_or_404(Tournament, slug=t_slug)

    auth = _view_grades_perm(request, trn)
    if type(auth) != bool:
        return auth

    members = _member_rank(trn)
    b = _best_members(trn)
    best = [
        (a, sorted(b, key=lambda x: x[a] if a in x else 0, reverse=True))
        for a in ["rep_tot", "opp_tot", "rev_tot"]
    ]

    return render(
        request,
        "result/memberstats.html",
        context={"members": members, "top_role": best},
    )
