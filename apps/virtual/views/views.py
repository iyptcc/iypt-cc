from decimal import Decimal

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.core import signing
from django.http import HttpResponseNotAllowed, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.crypto import constant_time_compare
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django_downloadview import ObjectDownloadView

from apps.account.models import Attendee, ParticipationRole
from apps.jury.models import GroupGrade, Juror, JurorGrade, JurorRole
from apps.plan.models import Fight, Round
from apps.team.models import Team, TeamRole

from ...dashboard.templatetags.flags import flag_url
from ...printer.models import Pdf
from ...result.utils import _fightdata, _fightpreview, _report_factor
from ...tournament.models import Tournament
from ..bbb import (
    create,
    create_hall,
    get_attendees,
    is_hall_running,
    is_meeting_running,
    join,
    join_hall,
)
from ..forms import JurorGradeForm, NameForm, RoomsForm
from ..models import Hall, Stream


def fight_info(request, f):
    fi = {"name": f.room.name, "pk": f.pk, "stages": f.stage_set.all(), "obj": f}
    stage1 = f.stage_set.all()[0]
    teams = [stage1.rep_attendance.team, stage1.opp_attendance.team]
    if f.round.review_phase:
        teams.append(stage1.rev_attendance.team)
    teams = list(filter(lambda x: x is not None, teams))
    if stage1.obs_attendance:
        teams.append(stage1.obs_attendance.team)
    fi["teams"] = teams

    team_tag = None
    role_tag = None
    roles = []
    for t in teams:
        if t is None:
            continue
        if t.get_students().filter(active_user=request.user.profile):
            roles.append(ParticipationRole.STUDENT)
            if request.user.profile.tournament.participationrole_set.get(
                type=ParticipationRole.STUDENT
            ).virtual_show_team:
                team_tag = t.origin.name
            role_tag = request.user.profile.tournament.participationrole_set.get(
                type=ParticipationRole.STUDENT
            ).virtual_name_tag

    if f.operators.filter(active_user=request.user.profile):
        roles.append(ParticipationRole.FIGHT_ASSISTANT)
        role_tag = request.user.profile.tournament.participationrole_set.get(
            type=ParticipationRole.FIGHT_ASSISTANT
        ).virtual_name_tag

    if f.round.publish_jurors:
        js = f.jurorsession_set.filter(juror__attendee=request.user.profile.active)
        if js.exists():
            roles.append(ParticipationRole.JUROR)
            fi["is_juror"] = True
            role_tag = request.user.profile.tournament.participationrole_set.get(
                type=ParticipationRole.JUROR
            ).virtual_name_tag

            if js.first().role.type == JurorRole.CHAIR:
                roles.append(ParticipationRole.CHAIR)
                role_tag = request.user.profile.tournament.participationrole_set.get(
                    type=ParticipationRole.CHAIR
                ).virtual_name_tag
    fi["roles"] = roles

    bbb_role = Tournament.BBB_ROLE_GUEST
    role_order = [a[0] for a in Tournament.BBB_ROLES]
    for r in roles:
        try:
            ro = request.user.profile.tournament.participationrole_set.get(
                type=r
            ).virtual_room_role
            if role_order.index(ro) > role_order.index(bbb_role):
                bbb_role = ro
        except:
            pass

    fi["roles"] = [
        request.user.profile.tournament.participationrole_set.get(type=r) for r in roles
    ]
    fi["bbb_role"] = bbb_role
    tags = ""
    if team_tag is not None or role_tag is not None:
        tags = " (%s)" % (
            ", ".join(filter(lambda x: x is not None, [role_tag, team_tag]))
        )
    fi["bbb_name"] = "%s%s" % (request.user.profile.active.full_name, tags)
    return fi


def hall_info(request, h):
    bbb_role = None
    role_order = [a[0] for a in Tournament.BBB_ROLES]
    team_tag = None
    role_tag = None
    for r in h.hallrole_set.filter(role__in=request.user.profile.active.roles.all()):
        if bbb_role == None:
            bbb_role = Tournament.BBB_ROLE_GUEST
        if role_order.index(r.mode) > role_order.index(bbb_role):
            bbb_role = r.mode
            role_tag = r.role.virtual_name_tag
        try:
            att: Attendee = request.user.profile.active
            team_tag = att.team_set.first().origin.name
        except:
            pass

    tags = ""
    if team_tag is not None or role_tag is not None:
        tags = " (%s)" % (
            ", ".join(filter(lambda x: x is not None, [role_tag, team_tag]))
        )

    return {
        "bbb_role": bbb_role,
        "bbb_name": "%s%s" % (request.user.profile.active.full_name, tags),
    }


@login_required
def overview(request):

    halls = Hall.objects.filter(
        roles__in=request.user.profile.active.roles.all()
    ).distinct()
    hobj = []
    for h in halls:
        hobj.append({"obj": h, **hall_info(request, h)})
    streams = Stream.objects.filter(
        access__in=request.user.profile.active.roles.all()
    ).distinct()

    rs = []
    rounds = Round.objects.filter(tournament=request.user.profile.tournament).order_by(
        "order"
    )
    # juror = Juror.objects.get_ attendee=request.user.profile.active)
    for round in rounds:
        fs = []
        for f in round.fight_set.select_related("room").all():
            if f.stage_set.first().stageattendance_set.count() > 0:
                fs.append(fight_info(request, f))
        rs.append({"fights": fs, "obj": round})

    return render(
        request,
        "virtual/plan.html",
        context={
            "rounds": rs,
            "halls": hobj,
            "streams": streams,
            "room_show_grades": request.user.profile.tournament.room_show_grades,
        },
    )


@method_decorator(login_required, name="dispatch")
class AvatarView(ObjectDownloadView):
    attachment = False

    def get_object(self, queryset=None):
        try:
            trn = self.request.user.profile.tournament
            user: User = User.objects.get(pk=self.kwargs["avatar_id"])
            att = user.profile.attendee_set.get(tournament=trn)
            if att.virtual_rooms.exists() or att.hall_set.exists():
                return user.profile.avatar
        except Exception as e:
            print(e)
            raise User.DoesNotExist("Avatar does not exist")


@login_required
def joinroom(request, fight_id):

    f = get_object_or_404(
        Fight, id=fight_id, round__tournament=request.user.profile.tournament
    )

    info = fight_info(request, f)

    if info["bbb_role"] == Tournament.BBB_ROLE_MODERATOR:
        e = create(f)
        link = join(
            f, info["bbb_name"], info["bbb_role"], userID="iyptcc_%d" % request.user.id
        )
        return render(
            request, "virtual/join.html", context={"fight": info, "link": link}
        )
    else:
        if all(is_meeting_running(f)):
            link = join(
                f,
                info["bbb_name"],
                info["bbb_role"],
                userID="iyptcc_%d" % request.user.id,
            )
            return render(
                request, "virtual/join.html", context={"fight": info, "link": link}
            )
        else:
            return render(request, "virtual/wait.html", context={"fight": info})


@login_required
def joinhall(request, hall_id):

    h = get_object_or_404(Hall, id=hall_id, tournament=request.user.profile.tournament)

    hi = hall_info(request, h)
    bbb_role = hi["bbb_role"]
    if (
        bbb_role == Tournament.BBB_ROLE_MODERATOR
        or bbb_role == Tournament.BBB_ROLE_ATTENDEE
        and h.allow_attendees_to_start_meeting
    ):
        create_hall(h)
        link = join_hall(
            h, hi["bbb_name"], bbb_role, userID="iyptcc_%d" % request.user.id
        )
        return render(request, "virtual/join.html", context={"link": link, "hall": h})
    else:
        if all(is_hall_running(h)):
            link = join_hall(
                h, hi["bbb_name"], bbb_role, userID="iyptcc_%d" % request.user.id
            )
            return render(
                request, "virtual/join.html", context={"link": link, "hall": h}
            )
        else:
            return render(request, "virtual/wait.html", context={})


@login_required
def watchstream(request, stream_id):

    streams = Stream.objects.filter(
        access__in=request.user.profile.active.roles.all(),
        id=stream_id,
        tournament=request.user.profile.tournament,
    ).distinct()
    if len(streams) != 1:
        return HttpResponseNotFound()

    h = streams.first()

    if h.external_link:
        return redirect(h.external_link)
    else:
        return render(request, "virtual/stream.html", context=h.random_urls)


class HallInviteView(View):
    def _auth_sig(self, hall, role, sig):
        signer = signing.Signer(salt="invite-links")
        # set password according to role
        if role not in [r[0] for r in Tournament.BBB_ROLES]:
            return False
        r = signer.sign(
            "%s-invitation-hall-%d-role-%s" % (hall.tournament.slug, hall.id, role)
        )
        newsig = r.split(":")[-1]

        if constant_time_compare(sig, newsig):
            return True
        return False

    def get(self, request, t_slug, hall_id, role, sig):
        print("in hallinvite")
        hall = get_object_or_404(Hall, id=hall_id)

        if not self._auth_sig(hall, role, sig):
            return redirect("result:plan", t_slug)

        form = NameForm()

        return render(request, "virtual/join.html", context={"form": form})

    def post(self, request, t_slug, hall_id, role, sig):
        hall = get_object_or_404(Hall, id=hall_id)

        if not self._auth_sig(hall, role, sig):
            return redirect("result:plan", t_slug)

        form = NameForm(request.POST)
        if form.is_valid():
            if all(is_hall_running(hall)):
                link = join_hall(hall, form.cleaned_data["name"], role)
                return render(request, "virtual/join.html", context={"link": link})
            else:
                return render(request, "virtual/wait.html", context={})

        return render(request, "virtual/join.html", context={"form": form})


class RoomInviteView(View):
    def _auth_sig(self, fight, role, sig):
        signer = signing.Signer(salt="invite-links")
        # set password according to role
        if role not in [r[0] for r in Tournament.BBB_ROLES]:
            return False
        r = signer.sign(
            "%s-invitation-fight-%d-role-%s"
            % (fight.round.tournament.slug, fight.id, role)
        )
        newsig = r.split(":")[-1]

        if constant_time_compare(sig, newsig):
            return True
        return False

    def get(self, request, t_slug, fight_id, role, sig):
        fight = get_object_or_404(Fight, id=fight_id)

        if not self._auth_sig(fight, role, sig):
            return redirect("result:plan", t_slug)

        form = NameForm()

        return render(request, "virtual/join.html", context={"form": form})

    def post(self, request, t_slug, fight_id, role, sig):
        fight = get_object_or_404(Fight, id=fight_id)

        if not self._auth_sig(fight, role, sig):
            return redirect("result:plan", t_slug)

        form = NameForm(request.POST)
        if form.is_valid():
            if all(is_meeting_running(fight)):
                link = join(fight, form.cleaned_data["name"], role)
                return render(request, "virtual/join.html", context={"link": link})
            else:
                return render(request, "virtual/wait.html", context={})

        return render(request, "virtual/join.html", context={"form": form})


@login_required
def fightviewclock(request, fight_id, stage):

    return render(
        request,
        "virtual/fightclock.xml",
        context={
            "id": fight_id,
            "stage": stage,
            "phases": request.user.profile.tournament.phase_set.all(),
        },
        content_type="image/svg+xml",
    )


class JurorPermMixin(UserPassesTestMixin):
    def test_func(self):
        if self.request.user.has_perm("jury.change_all_jurorsessions"):
            return True
        try:
            fi = Fight.objects.get(pk=self.request.resolver_match.kwargs["fight_id"])
            if (
                fi.juror_set.filter(attendee=self.request.user.profile.active).exists()
                and not fi.locked
            ):
                return True
        except:
            return False

        return False


@method_decorator(login_required, name="dispatch")
class FightView(JurorPermMixin, View):

    def get(self, request, fight_id, stage):

        fight = get_object_or_404(Fight, pk=fight_id)
        try:
            stage = fight.stage_set.get(order=stage)
        except:
            redirect("virtual:overview")

        all_stages = fight.stage_set.all()

        preview = _fightpreview(fight)[stage.order - 1]

        form = JurorGradeForm(
            fight.jurorsession_set.get(juror__attendee=request.user.profile.active),
            stage,
        )

        return render(
            request,
            "virtual/grades.html",
            context={
                "round": fight.round.order,
                "room": fight.room.name,
                "id": fight_id,
                "all_stages": all_stages,
                "stage": stage,
                "preview": preview,
                "form": form,
                "grading_sheet": fight.round.tournament.grading_sheet_pdf,
            },
        )

    def post(self, request, fight_id, stage):

        fight = get_object_or_404(Fight, pk=fight_id)
        try:
            stage = fight.stage_set.get(order=stage)
        except:
            redirect("virtual:overview")

        all_stages = fight.stage_set.all()

        preview = _fightpreview(fight)[stage.order - 1]

        js = fight.jurorsession_set.get(juror__attendee=request.user.profile.active)
        form = JurorGradeForm(js, stage, request.POST)

        if form.is_valid():

            if form.has_changed():

                for fn in form.changed_data:

                    if fn.startswith("grade") and stage.jurors_grading is True:

                        att = form.fields[fn].attendance
                        grade = None
                        try:
                            grade = att.jurorgrade_set.get(juror_session=js)
                        except JurorGrade.DoesNotExist:
                            pass

                        if form.cleaned_data[fn]:
                            if grade:
                                grade.grade = form.cleaned_data[fn]
                                grade.valid = False
                                grade.save()
                            else:
                                JurorGrade.objects.create(
                                    juror_session=js,
                                    stage_attendee=att,
                                    grade=form.cleaned_data[fn],
                                    valid=False,
                                )
                        else:
                            if grade:
                                grade.delete()
                            else:
                                pass

                    elif fn.startswith("partial") and stage.jurors_grading is True:

                        gr = form.fields[fn].gradinggroup
                        att = form.fields[fn].attendance
                        grade = None
                        try:
                            grade = gr.groupgrade_set.get(
                                juror_session=js, stage_attendee=att
                            )
                        except GroupGrade.DoesNotExist:
                            pass

                        if type(form.cleaned_data[fn]) == float:
                            if grade:
                                grade.value = form.cleaned_data[fn]
                                grade.save()
                            else:
                                GroupGrade.objects.create(
                                    juror_session=js,
                                    stage_attendee=att,
                                    group=gr,
                                    value=form.cleaned_data[fn],
                                )
                        else:
                            if grade:
                                grade.delete()
                            else:
                                pass

        if "_continue" in request.POST:
            return redirect(
                "virtual:fight", fight_id=fight.id, stage=int(stage.order) + 1
            )

        return render(
            request,
            "virtual/grades.html",
            context={
                "round": fight.round.order,
                "room": fight.room.name,
                "id": fight_id,
                "all_stages": all_stages,
                "stage": stage,
                "preview": preview,
                "form": form,
                "grading_sheet": fight.round.tournament.grading_sheet_pdf,
            },
        )


@method_decorator(login_required, name="dispatch")
@method_decorator(xframe_options_sameorigin, name="get")
class GradingSheetView(ObjectDownloadView):

    attachment = False

    mimetype = "application/pdf"

    def get_object(self, queryset=None):
        try:
            obj = self.request.user.profile.tournament.grading_sheet_pdf.file
            return obj
        except Pdf.DoesNotExist:
            raise Pdf.DoesNotExist("File does not exist")


def prelim_grades(request, fight_id):

    fight = get_object_or_404(
        Fight,
        id=fight_id,
        round__tournament=request.user.profile.tournament,
        round__tournament__room_show_grades=True,
    )

    info = fight_info(request, fight)

    if len(info["roles"]) == 0:
        return HttpResponseNotAllowed("Only room participants see grades")

    stage_info = []
    for stage in fight.stage_set.all():
        team = {}
        team["rep"] = stage.rep_attendance.team.origin.name
        team["opp"] = stage.opp_attendance.team.origin.name
        if fight.round.review_phase:
            team["rev"] = stage.rev_attendance.team.origin.name

        person = {}
        person["rep"] = ""
        person["opp"] = ""
        if fight.round.review_phase:
            person["rev"] = ""
        if stage.reporter:
            person["rep"] = stage.reporter.abbr_name
        if stage.opponent:
            person["opp"] = stage.opponent.abbr_name
        if fight.round.review_phase:
            if stage.reviewer:
                person["rev"] = stage.reviewer.abbr_name

        avg_s = {}
        factors = {}
        avg_w = {}

        factors["rep"] = _report_factor(stage.rep_attendance)
        factors["opp"] = 2.0
        factors["rev"] = 1.0

        if not stage.jurors_grading:
            avg_s["rep"] = stage.rep_attendance.prelim_average
            avg_s["opp"] = stage.opp_attendance.prelim_average
            if fight.round.review_phase:
                avg_s["rev"] = stage.rev_attendance.prelim_average

            avg_w["rep"] = stage.rep_attendance.prelim_average
            if avg_w["rep"]:
                avg_w["rep"] *= Decimal(str(_report_factor(stage.rep_attendance)))
            avg_w["opp"] = stage.opp_attendance.prelim_average
            if avg_w["opp"]:
                avg_w["opp"] *= Decimal("2.0")
            if fight.round.review_phase:
                avg_w["rev"] = stage.rev_attendance.prelim_average

        presented = ""
        if stage.presented:
            presented = {
                "number": stage.presented.number,
                "title": stage.presented.title,
            }
        stage_info.append(
            {
                "teams": team,
                "persons": person,
                "average": avg_s,
                "w_average": avg_w,
                "factors": factors,
                "presented": presented,
                "rejections": stage.rejections.all().values("number", "title"),
            }
        )

    grades_j = []
    for jurorsess in (
        fight.jurorsession_set(manager="voting").select_related("juror").all()
    ):
        juror = jurorsess.juror
        if fight.round.tournament.publish_juror_conflicting:
            confl = [(o.name, flag_url(o)) for o in juror.conflicting.all()]
        else:
            confl = []
        grade_j = {
            "id": juror.id,
            "first_name": juror.attendee.first_name,
            "last_name": juror.attendee.last_name,
            "conflicting": confl,
        }

        grades_s = []
        for stage in fight.stage_set.all():
            grade_s = {}
            if stage.jurors_grading:
                grade_s["rep"] = "grading"
                grade_s["opp"] = "grading"
                if fight.round.review_phase:
                    grade_s["rev"] = "grading"
            else:
                try:
                    grade_s["rep"] = JurorGrade.objects.get(
                        stage_attendee=stage.rep_attendance, juror_session__juror=juror
                    ).grade
                    grade_s["rep_partial"] = GroupGrade.objects.filter(
                        stage_attendee=stage.rep_attendance, juror_session__juror=juror
                    )
                except:
                    pass
                try:
                    grade_s["opp"] = JurorGrade.objects.get(
                        stage_attendee=stage.opp_attendance, juror_session__juror=juror
                    ).grade
                    grade_s["opp_partial"] = GroupGrade.objects.filter(
                        stage_attendee=stage.opp_attendance, juror_session__juror=juror
                    )
                except:
                    pass
                if fight.round.review_phase:
                    try:
                        grade_s["rev"] = JurorGrade.objects.get(
                            stage_attendee=stage.rev_attendance,
                            juror_session__juror=juror,
                        ).grade
                        grade_s["rev_partial"] = GroupGrade.objects.filter(
                            stage_attendee=stage.rev_attendance,
                            juror_session__juror=juror,
                        )
                    except:
                        pass

            grades_s.append(grade_s)

        grade_j["grades"] = grades_s

        grades_j.append(grade_j)

    context = {
        "room": fight.room.name,
        "round": fight.round.order,
        "grades": grades_j,
        "info": stage_info,
    }

    return render(
        request,
        "virtual/prelim.html",
        context={
            "fight": context,
            "tournament": request.user.profile.tournament.slug,
            "round": fight.round.order,
            "room": fight.room.name,
        },
    )


@method_decorator(login_required, name="dispatch")
class ManageRoomsView(View):

    @method_decorator(permission_required("plan.view_fight_operator"))
    def get(self, request):

        form = RoomsForm(request.user.profile.tournament)

        return render(request, "virtual/rooms.html", context={"form": form})

    @method_decorator(permission_required("plan.change_fight_operator"))
    def post(self, request):
        form = RoomsForm(request.user.profile.tournament, request.POST)

        if form.is_valid():
            form.save()

        return render(request, "virtual/rooms.html", context={"form": form})


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("plan.view_fight_operator", raise_exception=False),
    name="dispatch",
)
class RoomLinks(View):
    def get(self, request, id):
        fight = get_object_or_404(
            Fight, id=id, round__tournament=self.request.user.profile.tournament
        )

        signer = signing.Signer(salt="invite-links")
        # set password according to role
        links = []
        for role in [r[0] for r in Tournament.BBB_ROLES]:
            sig = signer.sign(
                "%s-invitation-fight-%d-role-%s"
                % (fight.round.tournament.slug, fight.id, role)
            )
            li = {
                "slug": fight.round.tournament.slug,
                "fight": id,
                "role": role,
                "sig": sig.split(":")[-1],
            }
            links.append(li)

        return render(
            request,
            "virtual/joinlinks.html",
            context={"links": links, "fight": str(fight)},
        )
