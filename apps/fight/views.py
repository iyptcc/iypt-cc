import os
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO

import paramiko
from celery.result import AsyncResult
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.cache import caches
from django.core.files.base import ContentFile
from django.core.signing import Signer
from django.db import transaction
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.utils.html import format_html_join, mark_safe
from django.views import View
from django_downloadview import ObjectDownloadView
from paramiko import SFTPClient, SSHException
from pdf2image import convert_from_path

from apps.dashboard.messages import Message
from apps.dashboard.simpleauth import purge_sessions
from apps.jury.forms import JuryForm
from apps.jury.models import (
    GradingSheet,
    GroupGrade,
    JurorGrade,
    JurorRole,
    JurorSession,
)
from apps.plan.models import Fight, FightRole, Round, Stage, StageAttendance
from apps.printer import context_generator
from apps.printer.models import FileServer, Pdf, PdfTag, Template
from apps.printer.tasks import render_to_pdf
from apps.printer.utils import _get_next_pdfname
from apps.result.utils import _fightpreview, _report_factor
from apps.tournament.models import Origin, Phase

from ..printer.views import ORMHostKeyPolicy
from .forms import (
    ManageForm,
    PublishForm,
    ScanForm,
    SlidesForm,
    SlidesImportForm,
    SlidesRedirForm,
    StageForm,
)
from .models import ClockState, ScanProcessing
from .tasks import importSlides, processJob
from .utils import areas as sheet_areas
from .utils import crop_image, fight_grades_valid

# Create your views here.


@login_required
@permission_required("jury.change_jurorsession")
def plan(request):

    editall = request.user.has_perm("jury.change_all_jurorsessions")
    rs = []
    rounds = Round.objects.filter(tournament=request.user.profile.tournament).order_by(
        "order"
    )
    for round in rounds:
        fs = []
        for f in round.fight_set.select_related("room").all():
            fi = {"name": f.room.name, "my": False, "locked": True, "pk": f.pk}
            fi["stages"] = range(f.stage_set.count())
            if f.operators.filter(id=request.user.profile.active_id).exists():
                fi["my"] = True
                fi["locked"] = f.locked
            fs.append(fi)
        rs.append(fs)

    return render(
        request, "fight/plan.html", context={"rounds": rs, "editall": editall}
    )


@login_required
@permission_required("jury.validate_grades")
def validate_plan(request):

    rs = []
    rounds = Round.objects.filter(tournament=request.user.profile.tournament).order_by(
        "order"
    )
    for round in rounds:
        fs = []
        for f in round.fight_set.select_related("room").all():
            fi = {"name": f.room.name, "locked": f.locked, "pk": f.pk}
            fi["valid"] = fight_grades_valid(f)
            fs.append(fi)
        rs.append(fs)

    return render(request, "fight/validate.html", context={"rounds": rs})


class FightAssistancePermMixin(UserPassesTestMixin):
    def test_func(self):
        if self.request.user.has_perm("jury.change_all_jurorsessions"):
            return True
        if not self.request.user.has_perm("jury.change_jurorsession"):
            return False
        try:
            fi = Fight.objects.get(pk=self.request.resolver_match.kwargs["fight_id"])
            if (
                fi.operators.filter(id=self.request.user.profile.active_id).exists()
                and not fi.locked
            ):
                return True
        except:
            return False

        return False


@method_decorator(login_required, name="dispatch")
class FightView(FightAssistancePermMixin, View):

    def get(self, request, fight_id, stage):

        fight = get_object_or_404(Fight, pk=fight_id)

        all_stages = []
        act_stage = {"is_last": False}
        for s in fight.stage_set.all():
            st = {"active": False}
            if act_stage["is_last"]:
                act_stage["is_last"] = False

            if s.order == int(stage):
                st["active"] = True

                act_stage["is_last"] = True
                act_stage["order"] = s.order

                act_stage["rep"] = s.rep_attendance.team.origin.name
                act_stage["opp"] = s.opp_attendance.team.origin.name
                if fight.round.review_phase:
                    act_stage["rev"] = s.rev_attendance.team.origin.name
                act_stage["prev"] = _fightpreview(s.fight)[s.order - 1]

                act_stage["obj"] = s
                act_stage["form"] = StageForm(s)

            all_stages.append(st)

        if "form" not in act_stage:
            return redirect("fight:fightjury", fight_id=fight_id)

        return render(
            request,
            "fight/fight.html",
            context={
                "round": fight.round.order,
                "room": fight.room.name,
                "id": fight_id,
                "all_stages": all_stages,
                "stage": act_stage,
                "locked": fight.locked,
                "phases": request.user.profile.tournament.phase_set.all(),
            },
        )

    def post(self, request, fight_id, stage):

        fight = get_object_or_404(Fight, pk=fight_id)

        all_stages = []
        act_stage = {"is_last": False, "order": int(stage)}
        for s in fight.stage_set.all():
            st = {"active": False}
            if act_stage["is_last"]:
                act_stage["is_last"] = False

            if s.order == int(stage):
                st["active"] = True

                act_stage["is_last"] = True

                act_stage["rep"] = s.rep_attendance.team.origin.name
                act_stage["opp"] = s.opp_attendance.team.origin.name
                if fight.round.review_phase:
                    act_stage["rev"] = s.rev_attendance.team.origin.name
                act_stage["prev"] = _fightpreview(s.fight)[s.order - 1]

                act_stage["form"] = StageForm(s, request.POST)
                act_stage["obj"] = s

            all_stages.append(st)

        if "form" not in act_stage:
            return redirect("fight:fightjury", fight_id=fight_id)

        form = act_stage["form"]
        if form.is_valid():

            if form.has_changed():

                for fn in form.changed_data:

                    if fn == "rejections":
                        act_stage["obj"].rejections.clear()

                        for p in form.cleaned_data["rejections"]:
                            act_stage["obj"].rejections.add(p)

                    elif fn == "presented":
                        act_stage["obj"].presented = form.cleaned_data["presented"]
                        act_stage["obj"].save()

                    elif fn == "rep":
                        if form.cleaned_data["rep"]:
                            act_stage["obj"].rep_attendance.active_person = (
                                form.cleaned_data["rep"]
                            )
                        else:
                            act_stage["obj"].rep_attendance.active_person = None
                        act_stage["obj"].rep_attendance.save()

                    elif fn == "opp":
                        if form.cleaned_data["opp"]:
                            act_stage["obj"].opp_attendance.active_person = (
                                form.cleaned_data["opp"]
                            )
                        else:
                            act_stage["obj"].opp_attendance.active_person = None
                        act_stage["obj"].opp_attendance.save()

                    elif fn == "rev":
                        if form.cleaned_data["rev"]:
                            act_stage["obj"].rev_attendance.active_person = (
                                form.cleaned_data["rev"]
                            )
                        else:
                            act_stage["obj"].rev_attendance.active_person = None
                        act_stage["obj"].rev_attendance.save()

                    elif (
                        fn.startswith("grade")
                        and act_stage["obj"].jurors_grading is False
                    ):

                        js = form.fields[fn].jurorsession
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

                pass

            if "_continue" in request.POST:
                return redirect("fight:fight", fight_id=fight_id, stage=int(stage) + 1)
            if "_finish" in request.POST:
                return redirect("fight:fightpre", fight_id=fight_id)

            if "_toggle_grading" in request.POST:
                act_stage["obj"].jurors_grading = not act_stage["obj"].jurors_grading
                print("switched grading to ", act_stage["obj"].jurors_grading)
                act_stage["obj"].save()
                return redirect("fight:fight", fight_id=fight_id, stage=int(stage))

        return render(
            request,
            "fight/fight.html",
            context={
                "round": fight.round.order,
                "room": fight.room.name,
                "id": fight_id,
                "all_stages": all_stages,
                "stage": act_stage,
                "locked": fight.locked,
                "phases": request.user.profile.tournament.phase_set.all(),
            },
        )


@method_decorator(login_required, name="dispatch")
class FightJuryView(FightAssistancePermMixin, View):

    def get(self, request, fight_id):

        fight = get_object_or_404(Fight, pk=fight_id)

        form = JuryForm(fight)

        return render(
            request,
            "fight/jury.html",
            context={
                "fight": fight,
                "form": form,
                "all_stages": range(fight.stage_set.count()),
            },
        )

    def post(self, request, fight_id):

        fight = get_object_or_404(Fight, pk=fight_id)

        form = JuryForm(fight, request.POST)

        if form.is_valid():

            if form.has_changed():
                if "jurors" in form.changed_data:
                    now = form.cleaned_data["jurors"]
                    old = form.fields["jurors"].obj_initial

                    additions = set(now) - set(old)

                    jrole = JurorRole.objects.get(
                        tournament=fight.round.tournament, type=JurorRole.JUROR
                    )

                    for j in additions:
                        JurorSession.objects.create(juror=j, fight=fight, role=jrole)

                    deletions = set(old) - set(now)

                    for j in deletions:
                        JurorSession.objects.get(juror=j, fight=fight).delete()

                if "chair" in form.changed_data:

                    try:
                        JurorSession.objects.get(
                            fight=fight, role__type=JurorRole.CHAIR
                        ).delete()
                    except:
                        pass

                    if form.cleaned_data["chair"]:
                        crole = JurorRole.objects.get(
                            tournament=fight.round.tournament, type=JurorRole.CHAIR
                        )
                        JurorSession.objects.create(
                            juror=form.cleaned_data["chair"], fight=fight, role=crole
                        )

            if "_continue" in request.POST:
                return redirect("fight:fight", fight_id=fight_id, stage=1)

        return render(
            request,
            "fight/jury.html",
            context={
                "fight": fight,
                "form": form,
                "all_stages": range(fight.stage_set.count()),
            },
        )


@method_decorator(login_required, name="dispatch")
class FightPreView(FightAssistancePermMixin, View):

    def _fight_check(self, fight):

        errors = []
        warnings = []
        chair = None
        try:
            chair = fight.jurorsession_set.get(role__type=JurorRole.CHAIR)
        except:
            errors.append("Please set a chair")

        jurors = fight.jurorsession_set.filter(role__type=JurorRole.JUROR)

        if jurors.count() < 4:
            errors.append("A fight needs at least 5 jurors")

        stage_info = []

        teams = {}

        for stage in fight.stage_set.all():

            prev = _fightpreview(fight)[stage.order - 1]

            team_name = {}
            team_name["rep"] = stage.rep_attendance.team.origin.name
            team_name["opp"] = stage.opp_attendance.team.origin.name
            if fight.round.review_phase:
                team_name["rev"] = stage.rev_attendance.team.origin.name

            person = {}
            person["rep"] = ""
            person["opp"] = ""
            if fight.round.review_phase:
                person["rev"] = ""
            if stage.reporter:
                person["rep"] = stage.reporter
            else:
                errors.append("Stage %d missing reporter name" % stage.order)
            if stage.opponent:
                person["opp"] = stage.opponent
            else:
                errors.append("Stage %d missing opponent name" % stage.order)
            if fight.round.review_phase:
                if stage.reviewer:
                    person["rev"] = stage.reviewer
                else:
                    errors.append("Stage %d missing reviewer name" % stage.order)

            presented = ""
            if stage.presented:
                presented = stage.presented.number
                if presented not in [p["number"] for p in prev["free"]]:
                    warnings.append(
                        "Problem presented in stage %d not in preview" % stage.order
                    )
                if presented in stage.rejections.all().values_list("number", flat=True):
                    errors.append(
                        "Stage %d presented problem is in rejected list" % stage.order
                    )
            else:
                errors.append("Stage %d has no presented problem" % stage.order)

            grades_j = []
            r_grades = {}
            r_grades["rep"] = []
            r_grades["opp"] = []
            r_grades["rev"] = []

            for jurorsess in fight.jurorsession_set.select_related("juror").all():
                juror = jurorsess.juror
                voting = jurorsess.role.type in [JurorRole.JUROR, JurorRole.CHAIR]
                grade_j = {"id": juror.id, "name": juror.attendee, "voting": voting}

                try:
                    grade_j["rep"] = int(
                        JurorGrade.objects.get(
                            stage_attendee=stage.rep_attendance,
                            juror_session__juror=juror,
                        ).grade
                    )
                    grade_j["rep_partial"] = GroupGrade.objects.filter(
                        stage_attendee=stage.rep_attendance, juror_session__juror=juror
                    )
                    sum_floor = sum([gr.value for gr in grade_j["rep_partial"]]) + 1
                    if (
                        int(sum_floor) > grade_j["rep"]
                        or grade_j["rep"] > int(sum_floor) + 1
                    ):
                        warnings.append(
                            "Stage %d reporter grade from %s has large difference %.2f vs %d"
                            % (stage.order, juror.attendee, sum_floor, grade_j["rep"])
                        )
                    if voting:
                        r_grades["rep"].append(Decimal(grade_j["rep"]))
                except:
                    errors.append(
                        "Stage %d missing reporter grade from %s"
                        % (stage.order, juror.attendee)
                    )
                try:
                    grade_j["opp"] = int(
                        JurorGrade.objects.get(
                            stage_attendee=stage.opp_attendance,
                            juror_session__juror=juror,
                        ).grade
                    )
                    grade_j["opp_partial"] = GroupGrade.objects.filter(
                        stage_attendee=stage.opp_attendance, juror_session__juror=juror
                    )
                    if voting:
                        r_grades["opp"].append(Decimal(grade_j["opp"]))
                except:
                    errors.append(
                        "Stage %d missing opponent grade from %s"
                        % (stage.order, juror.attendee)
                    )

                if fight.round.review_phase:
                    try:
                        grade_j["rev"] = int(
                            JurorGrade.objects.get(
                                stage_attendee=stage.rev_attendance,
                                juror_session__juror=juror,
                            ).grade
                        )
                        grade_j["rev_partial"] = GroupGrade.objects.filter(
                            stage_attendee=stage.rev_attendance,
                            juror_session__juror=juror,
                        )
                        if voting:
                            r_grades["rev"].append(Decimal(grade_j["rev"]))
                    except:
                        errors.append(
                            "Stage %d missing reviewer grade from %s"
                            % (stage.order, juror.attendee)
                        )

                grades_j.append(grade_j)

            avg_s = {}
            for role in ["rep", "opp", "rev"]:

                if len(r_grades[role]) >= 3:
                    best = max(r_grades[role])
                    worst = min(r_grades[role])

                    r_grades[role].remove(best)
                    r_grades[role].remove(worst)

                    r_grades[role].append((best + worst) / Decimal("2"))

                    avg_s[role] = sum(r_grades[role]) / len(r_grades[role])
                elif len(r_grades[role]) > 0:
                    avg_s[role] = sum(r_grades[role]) / len(r_grades[role])
                else:
                    avg_s[role] = None

            factors = {}
            factors["rep"] = _report_factor(stage.rep_attendance)
            factors["opp"] = 2.0
            factors["rev"] = 1.0

            avg_w = {}
            avg_w["rep"] = avg_s["rep"]
            if avg_w["rep"]:
                avg_w["rep"] *= Decimal(str(_report_factor(stage.rep_attendance)))
            avg_w["opp"] = avg_s["opp"]
            if avg_w["opp"]:
                avg_w["opp"] *= Decimal("2.0")
            avg_w["rev"] = avg_s["rev"]

            attendance = stage.rep_attendance_grades
            team = attendance.team
            team_id = attendance.team_id
            if team_id not in teams:
                teams[team_id] = [team, 0, 0, 0]
            teams[team.pk][3] += Decimal(str(_report_factor(stage.rep_attendance)))
            if avg_w["rep"]:
                teams[team.pk][1] += avg_w["rep"]
                teams[team.pk][2] += Decimal(str(_report_factor(stage.rep_attendance)))

            attendance = stage.opp_attendance_grades
            team = attendance.team
            team_id = attendance.team_id
            if team_id not in teams:
                teams[team_id] = [team, 0, 0, 0]
            teams[team_id][3] += 2
            if avg_w["opp"]:

                teams[team_id][1] += avg_w["opp"]
                teams[team_id][2] += 2

            if fight.round.review_phase:
                attendance = stage.rev_attendance_grades
                team = attendance.team
                team_id = attendance.team_id
                if team_id not in teams:
                    teams[team_id] = [team, 0, 0, 0]
                teams[team_id][3] += 1
                if avg_w["rev"]:
                    teams[team_id][1] += avg_w["rev"]
                    teams[team_id][2] += 1

            stage_info.append(
                {
                    "teams": team_name,
                    "persons": person,
                    "average": avg_s,
                    "w_average": avg_w,
                    "factors": factors,
                    "presented": presented,
                    "rejections": stage.rejections.all().values_list(
                        "number", flat=True
                    ),
                    "jurors": grades_j,
                }
            )

        result = reversed(
            sorted(
                map(
                    lambda t: {
                        "pk": t[0].pk,
                        "won": False,
                        "name": t[0].origin.name,
                        "sp": Decimal(t[1]).quantize(Decimal("1.1"), ROUND_HALF_UP),
                        "factors": t[2],
                        "total_factor": t[3],
                        "estimate": (t[1] / (t[2] or Decimal("1"))) * t[3],
                        "slug": t[0].origin.slug,
                    },
                    teams.values(),
                ),
                key=lambda t: t["estimate"],
            )
        )

        result = list(result)

        fb_given = set()
        for js in fight.jurorsession_set.all():
            fb_given.update(js.chairfeedback_set.values_list("team", flat=True))
            fb_given.update(js.feedback_set.values_list("team", flat=True))

        for team in fight.stage_set.get(order=1).attendees.all():
            if team.id not in fb_given:
                warnings.append(
                    "Team %s did not provide feedback!" % (team.origin.name)
                )

        return {
            "fight": fight,
            "chair": chair,
            "jurors": jurors,
            "stages": stage_info,
            "result": result,
            "errors": errors,
            "warnings": warnings,
            "all_stages": range(fight.stage_set.count()),
        }

    def get(self, request, fight_id):

        fight = get_object_or_404(Fight, pk=fight_id)

        validator = request.user.has_perm("jury.validate_grades")

        context = self._fight_check(fight)
        context.update({"validator": validator})

        return render(request, "fight/preview.html", context=context)

    @method_decorator(transaction.atomic)
    def post(self, request, fight_id):

        fight = get_object_or_404(
            Fight, pk=fight_id, round__tournament=request.user.profile.tournament
        )

        chk = self._fight_check(fight)

        if len(chk["errors"]) == 0 or True:
            if "_save" in request.POST:
                fight.locked = True
                fight.save()
            elif "_validate" in request.POST:
                if request.user.has_perm("jury.validate_grades") and fight.locked:
                    for grade in JurorGrade.objects.filter(
                        stage_attendee__stage__fight=fight
                    ):
                        grade.valid = True
                        grade.save()
                    # clear all caches
                    caches["results"].delete("preview-%s" % fight.pk)
                    caches["results"].delete("points-%s" % fight.pk)
                    caches["results"].delete("grades-%s" % fight.pk)
                    messages.add_message(
                        request,
                        messages.SUCCESS,
                        "All grades of fight %s validated" % fight,
                    )
                else:
                    messages.add_message(
                        request, messages.ERROR, "No Permission or fight not locked"
                    )

                return redirect("fight:validate")

        return redirect("fight:plan")


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("jury.publish_fights"), name="dispatch")
class ListScanProessing(View):

    def get(self, request, pdf_id=None, page=None):

        trn = request.user.profile.tournament
        form = ScanForm(trn)

        pdf = None
        if pdf_id and page:
            pdf = get_object_or_404(Pdf, tournament=trn, id=pdf_id)
            form.fields["pdf"].initial = pdf.id
            form.fields["page"].initial = page

        results = []
        for result in ScanProcessing.objects.filter(tournament=trn).order_by(
            "-created"
        ):
            res = AsyncResult(result.task_id)
            p = None
            errors = None
            info = None
            if res.state == "PROGRESS":
                p = 100 * res.info["current"] / res.info["total"]
            if res.successful():
                if len(res.result) > 0:
                    if type(res.result) != dict:
                        errors = res.result
                    else:
                        info = res.result
                        for k, v in info.items():
                            if "sheet_id" in v:
                                try:
                                    v["stage"] = GradingSheet.objects.get(
                                        id=v["sheet_id"]
                                    ).stage
                                except:
                                    pass

            results.append(
                {
                    "task": result,
                    "state": res.state,
                    "progress": p,
                    "errors": errors,
                    "info": info,
                }
            )

        return render(
            request,
            "fight/scanningtasks.html",
            context={"tasks": results, "form": form, "pdf": pdf, "page": page},
        )


@login_required
def get_pdf_page(request, pdf_id, page):
    trn = request.user.profile.tournament
    pdf = get_object_or_404(Pdf, tournament=trn, id=pdf_id)
    img = convert_from_path(
        pdf.file.path, first_page=page, last_page=page, dpi=300, fmt="jpg"
    )[0]

    response = HttpResponse(content_type="image/jpeg")
    img.save(response, "JPEG")
    return response


@login_required
def processPDF(request):
    if request.method == "POST":

        trn = request.user.profile.tournament

        form = ScanForm(trn, request.POST)

        if form.is_valid():

            pdf = form.cleaned_data["pdf"]
            if pdf.tournament != trn:
                return redirect("fight:processing")

            if "_auto" in request.POST:

                res = processJob.delay(trn.id, pdf_id=pdf.id)

                ScanProcessing.objects.create(
                    tournament=trn,
                    task_id=res.id,
                    author=request.user.profile.active,
                    pdf=pdf,
                )

            elif "_single" in request.POST:

                js = form.cleaned_data["jurorsession"]
                # print("file for js:",js)
                stage = js.fight.stage_set.get(order=form.cleaned_data["stage"])

                page = form.cleaned_data["page"]
                tosave = convert_from_path(
                    pdf.file.path, first_page=page, last_page=page, dpi=300, fmt="jpg"
                )[0]

                orient = form.cleaned_data["orientation"]
                if orient:
                    tosave = tosave.transpose(int(orient))

                # print("and stage:", stage)

                cf = {}
                for area in ["data", "rep", "opp", "rev", "full"]:
                    f = BytesIO()
                    try:
                        crop_image(tosave, sheet_areas[area]).save(f, format="jpeg")
                        cf[area] = ContentFile(
                            f.getvalue(), "%s-%d-%d.jpg" % (area, js.id, stage.id)
                        )
                    finally:
                        f.close()

                if not GradingSheet.objects.filter(
                    jurorsession=js, stage=stage
                ).exists():
                    GradingSheet.objects.create(
                        jurorsession=js,
                        stage=stage,
                        header=cf["data"],
                        rep=cf["rep"],
                        opp=cf["opp"],
                        rev=cf["rev"],
                        full=cf["full"],
                    )

            # return render(request, "jury/assign.html", context={"rounds":plan,'assignments':assignment_sorted})
        return redirect("fight:processing")

    return HttpResponseNotAllowed(["POST"])


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("jury.publish_fights"), name="dispatch")
class FightScanView(View):
    def get(self, request, fight_id):

        fight = get_object_or_404(
            Fight, pk=fight_id, round__tournament=request.user.profile.tournament
        )

        stage_info = []

        chair = None
        try:
            chair = fight.jurorsession_set.get(role__type=JurorRole.CHAIR)
        except:
            pass

        jurors = fight.jurorsession_set.filter(role__type=JurorRole.JUROR)

        for stage in fight.stage_set.all():
            team = {}
            team["rep"] = stage.rep_attendance.team.origin.name
            team["opp"] = stage.opp_attendance.team.origin.name
            if fight.round.review_phase:
                team["rev"] = stage.rev_attendance.team.origin.name

            person = {}
            person["rep"] = ""
            person["opp"] = ""
            person["rev"] = ""
            if stage.reporter:
                person["rep"] = stage.reporter
            if stage.opponent:
                person["opp"] = stage.opponent
            if fight.round.review_phase:
                if stage.reviewer:
                    person["rev"] = stage.reviewer

            presented = ""
            if stage.presented:
                presented = stage.presented.number

            grades_j = []
            for jurorsess in (
                fight.jurorsession_set(manager="voting").select_related("juror").all()
            ):
                juror = jurorsess.juror
                grade_j = {"id": juror.id, "name": juror.attendee}

                try:
                    grade_j["sheet"] = jurorsess.gradingsheet_set.get(stage=stage)
                except:
                    pass

                try:
                    grade_j["rep"] = int(
                        JurorGrade.objects.get(
                            stage_attendee=stage.rep_attendance,
                            juror_session__juror=juror,
                        ).grade
                    )
                except:
                    pass
                try:
                    grade_j["opp"] = int(
                        JurorGrade.objects.get(
                            stage_attendee=stage.opp_attendance,
                            juror_session__juror=juror,
                        ).grade
                    )
                except:
                    pass
                try:
                    if fight.round.review_phase:
                        grade_j["rev"] = int(
                            JurorGrade.objects.get(
                                stage_attendee=stage.rev_attendance,
                                juror_session__juror=juror,
                            ).grade
                        )
                except:
                    pass

                grades_j.append(grade_j)

            stage_info.append(
                {
                    "teams": team,
                    "persons": person,
                    "presented": presented,
                    "rejections": stage.rejections.all().values_list(
                        "number", flat=True
                    ),
                    "jurors": grades_j,
                    "id": stage.id,
                }
            )

        return render(
            request,
            "fight/scan_preview.html",
            context={
                "fight": fight,
                "chair": chair,
                "jurors": jurors,
                "stages": stage_info,
            },
        )

    @method_decorator(transaction.atomic)
    def post(self, request, fight_id):

        fight = get_object_or_404(
            Fight, pk=fight_id, round__tournament=request.user.profile.tournament
        )

        if "_validate" in request.POST:
            if request.user.has_perm("jury.validate_grades") and fight.locked:
                for grade in JurorGrade.objects.filter(
                    stage_attendee__stage__fight=fight
                ):
                    grade.valid = True
                    grade.save()
                # clear all caches
                caches["results"].delete("preview-%s" % fight.pk)
                caches["results"].delete("points-%s" % fight.pk)
                caches["results"].delete("grades-%s" % fight.pk)
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    "All grades of fight %s validated" % fight,
                )
            else:
                messages.add_message(
                    request, messages.ERROR, "No Permission or fight not locked"
                )

        # DELETE SINGLE sheet
        for gs in GradingSheet.objects.filter(jurorsession__fight=fight):
            if "_delete_%d" % gs.id in request.POST:
                gs.delete()

        if "_delete" in request.POST:
            sheets = GradingSheet.objects.filter(jurorsession__fight=fight)
            deled = ["%s" % sheet for sheet in sheets]
            sheets.delete()
            messages.add_message(
                request, messages.SUCCESS, "Deleted sheets %s" % (", ".join(deled))
            )

        return redirect("fight:validate")


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("jury.publish_fights"), name="dispatch")
class ScanView(ObjectDownloadView):
    attachment = False

    def get_object(self, queryset=None):
        if self.kwargs["typ"] in ["header", "rep", "opp", "rev"]:
            try:
                obj = GradingSheet.objects.filter(
                    stage__fight__round__tournament=self.request.user.profile.tournament,
                    id=self.kwargs["stage_id"],
                ).first()
                file = obj.__getattribute__(self.kwargs["typ"])
                return file
            except:
                raise Pdf.DoesNotExist("File does not exist")


@method_decorator(login_required, name="dispatch")
class ManageFightsView(View):

    @method_decorator(permission_required("plan.view_fight_operator"))
    def get(self, request):

        form = ManageForm(request.user.profile.tournament)

        return render(request, "fight/manage.html", context={"form": form})

    @method_decorator(permission_required("plan.change_fight_operator"))
    def post(self, request):
        form = ManageForm(request.user.profile.tournament, request.POST)

        if form.is_valid():
            for r in request.user.profile.tournament.round_set.all():
                if "_import_%d" % r.order in request.POST:
                    srcround: Round = form.cleaned_data["import-%d" % r.order]
                    if srcround is not None:
                        print("import FA from round", srcround, "for round", r.order)
                        for fight in r.fight_set.all():
                            try:
                                srcfight = srcround.fight_set.get(room=fight.room)
                                fight.operators.set(srcfight.operators.all())
                                fight.save()
                            except Round.DoesNotExist:
                                pass
                        return redirect("fight:manage")
                if "_unlock_%d" % r.order in request.POST:
                    for fight in r.fight_set.all():
                        fight.locked = False
                        fight.save()
                    return redirect("fight:manage")
            if form.has_changed():
                changes = []
                for cf in form.changed_data:
                    if cf.startswith("op-"):
                        changes.append(
                            (
                                str(form.fields[cf].fight),
                                form.fields[cf].old_attendees,
                                ", ".join([a.full_name for a in form.cleaned_data[cf]]),
                            )
                        )

                        form.fields[cf].fight.operators.set(form.cleaned_data[cf])
                        form.fields[cf].fight.save()

                    elif cf.startswith("locked-"):
                        changes.append(
                            (
                                str(form.fields[cf].fight),
                                "locked" if form.fields[cf].initial else "unlocked",
                                "locked" if form.cleaned_data[cf] else "unlocked",
                            )
                        )

                        form.fields[cf].fight.locked = form.cleaned_data[cf]
                        form.fields[cf].fight.save()

                cgs = format_html_join(
                    "",
                    "<li>{} : {} <i class='fa fa-angle-right'></i> {}</li>",
                    (c for c in changes),
                )
                msg = [
                    Message(
                        subject=mark_safe(
                            "Saved assignments with changes: <ul>%s</ul>" % (cgs,)
                        ),
                        level_tag="success",
                    )
                ]
            else:
                msg = [Message(subject="No changes made", level_tag="warning")]

            for r in request.user.profile.tournament.round_set.all():
                if "_open_grading_%d" % r.order in request.POST:
                    for fi in r.fight_set.all():
                        st: Stage
                        for st in fi.stage_set.all():
                            st.jurors_grading = True
                            st.save()
                if "_close_grading_%d" % r.order in request.POST:
                    for fi in r.fight_set.all():
                        st: Stage
                        for st in fi.stage_set.all():
                            st.jurors_grading = False
                            st.save()
        else:
            print(form.errors)
            msg = [Message(subject="Form contains errors", level_tag="error")]

        return render(
            request, "fight/manage.html", context={"form": form, "messages": msg}
        )


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("jury.publish_fights"), name="dispatch")
class SlidesView(View):
    def get(self, request):
        form = SlidesForm(request.user.profile.tournament)

        redirform = SlidesRedirForm(request.user.profile.tournament)

        return render(
            request, "fight/slides.html", context={"form": form, "redirform": redirform}
        )

    def post(self, request):
        if "_redir" in request.POST:
            redirform = SlidesRedirForm(request.user.profile.tournament, request.POST)
            if redirform.is_valid():
                return redirect(
                    "fight:slides_import",
                    id=redirform.cleaned_data["server"].id,
                    round_order=redirform.cleaned_data["round"].order,
                    path=redirform.cleaned_data["path"],
                )
            else:
                form = SlidesForm(request.user.profile.tournament)
                return render(
                    request,
                    "fight/slides.html",
                    context={"form": form, "redirform": redirform},
                )

        trn = request.user.profile.tournament
        form = SlidesForm(trn, request.POST, request.FILES)
        print(request.FILES)
        if form.is_valid():
            print(form.cleaned_data)
            if form.has_changed():
                for cf in form.changed_data:
                    if cf.startswith("slides-"):
                        print(form.cleaned_data[cf])
                        form.fields[cf].stage.pdf_presentation = form.cleaned_data[cf]
                        form.fields[cf].stage.save()

        return render(request, "fight/slides.html", context={"form": form})


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("jury.publish_fights"), name="dispatch")
class SlidesImport(View):

    def get(self, request, id, round_order, path):
        trn = request.user.profile.tournament
        server = get_object_or_404(FileServer, tournament=trn, id=id)
        round = get_object_or_404(Round, tournament=trn, order=round_order)

        ssh = paramiko.SSHClient()
        policy = ORMHostKeyPolicy(server)
        ssh.set_missing_host_key_policy(policy)
        try:
            ssh.connect(
                hostname=server.hostname,
                port=server.port,
                username=server.username,
                password=server.password,
            )
            sftp: SFTPClient = ssh.open_sftp()

            form = SlidesImportForm(sftp, trn, round, path)
        except SSHException as e:
            return render(request, "fight/slides_import.html", {"error": e})
        return render(
            request,
            "fight/slides_import.html",
            {"form": form, "round": round_order, "server": server, "path": path},
        )

    def post(self, request, id, round_order, path):
        trn = request.user.profile.tournament
        server = get_object_or_404(FileServer, tournament=trn, id=id)
        round = get_object_or_404(Round, tournament=trn, order=round_order)
        ssh = paramiko.SSHClient()
        policy = ORMHostKeyPolicy(server)
        ssh.set_missing_host_key_policy(policy)
        ssh.connect(
            hostname=server.hostname,
            port=server.port,
            username=server.username,
            password=server.password,
        )
        sftp = ssh.open_sftp()

        form = SlidesImportForm(sftp, trn, round, path, request.POST)

        jobs = []
        if form.is_valid():
            print("valid", form.cleaned_data)
            for file in form.cleaned_data["files"]:
                try:
                    base = os.path.split(file)[0]
                    ori = Origin.objects.filter(slug=base, tournament=trn).first()
                    stage = StageAttendance.objects.get(
                        stage__fight__round=round,
                        role__type=FightRole.REP,
                        team__origin=ori,
                    ).stage
                    print("stage", stage)
                    print("saving ", file)
                    jobs.append({"stage_id": stage.id, "sub_path": file})
                except:
                    pass
            importSlides.delay(server.id, path, jobs)
            return redirect("fight:slides")

        return render(
            request,
            "fight/slides_import.html",
            {"form": form, "round": round_order, "server": server, "path": path},
        )


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("jury.publish_fights"), name="dispatch")
class PublishView(View):
    def get(self, request):
        form = PublishForm(request.user.profile.tournament)

        return render(request, "fight/publish.html", context={"form": form})

    def post(self, request):

        trn = request.user.profile.tournament
        form = PublishForm(trn, request.POST)

        if form.is_valid():
            if form.has_changed():
                changes = []
                for cf in form.changed_data:
                    if cf.startswith("grades-"):
                        changes.append(
                            (
                                (
                                    "published grades"
                                    if form.cleaned_data[cf]
                                    else "recalled grades"
                                ),
                                form.fields[cf].fight,
                            )
                        )
                        form.fields[cf].fight.publish_grades = form.cleaned_data[cf]
                        form.fields[cf].fight.save()
                    if cf.startswith("single-"):
                        changes.append(
                            (
                                (
                                    "published single sheets"
                                    if form.cleaned_data[cf]
                                    else "recalled sheets"
                                ),
                                form.fields[cf].fight,
                            )
                        )
                        form.fields[cf].fight.publish_partials = form.cleaned_data[cf]
                        form.fields[cf].fight.save()
                    if cf.startswith("slides-"):
                        changes.append(
                            (
                                (
                                    "published slides"
                                    if form.cleaned_data[cf]
                                    else "recalled slies"
                                ),
                                form.fields[cf].fight,
                            )
                        )
                        form.fields[cf].fight.publish_slides = form.cleaned_data[cf]
                        form.fields[cf].fight.save()
                    if cf.startswith("partial-"):
                        changes.append(
                            (
                                (
                                    "set partial grades file"
                                    if form.cleaned_data[cf]
                                    else "unlinked partial grades"
                                ),
                                form.fields[cf].fight,
                            )
                        )
                        form.fields[cf].fight.pdf_partial_grades = form.cleaned_data[cf]
                        form.fields[cf].fight.save()
                    if cf.startswith("preview-"):
                        changes.append(
                            (
                                (
                                    "published preview"
                                    if form.cleaned_data[cf]
                                    else "recalled preview"
                                ),
                                form.fields[cf].fight,
                            )
                        )
                        form.fields[cf].fight.publish_preview = form.cleaned_data[cf]
                        form.fields[cf].fight.save()
                    if cf.startswith("rank-"):
                        changes.append(
                            (
                                (
                                    "published ranking"
                                    if form.cleaned_data[cf]
                                    else "recalled ranking"
                                ),
                                form.fields[cf].round,
                            )
                        )
                        form.fields[cf].round.publish_ranking = form.cleaned_data[cf]
                        form.fields[cf].round.save()
                    if cf.startswith("sched-"):
                        changes.append(
                            (
                                (
                                    "published schedule"
                                    if form.cleaned_data[cf]
                                    else "recalled schedule"
                                ),
                                form.fields[cf].round,
                            )
                        )
                        form.fields[cf].round.publish_schedule = form.cleaned_data[cf]
                        form.fields[cf].round.save()
                    if cf.startswith("fixed-"):
                        changes.append(
                            ("preview only fixed problem ", form.fields[cf].round)
                        )
                        form.fields[cf].round.preview_fixed_problem = form.cleaned_data[
                            cf
                        ]
                        form.fields[cf].round.save()
                    if cf.startswith("fblocked-"):
                        changes.append(
                            ("set feedback lock in round ", form.fields[cf].round)
                        )
                        form.fields[cf].round.feedback_locked = form.cleaned_data[cf]
                        form.fields[cf].round.save()
                    if cf.startswith("jury-"):
                        changes.append(
                            (
                                (
                                    "published jury"
                                    if form.cleaned_data[cf]
                                    else "recalled jury"
                                ),
                                form.fields[cf].round,
                            )
                        )
                        form.fields[cf].round.publish_jurors = form.cleaned_data[cf]
                        form.fields[cf].round.save()
                    if cf.startswith("active-"):
                        changes.append(
                            (
                                (
                                    "set active"
                                    if form.cleaned_data[cf]
                                    else "set passive"
                                ),
                                form.fields[cf].round,
                            )
                        )
                        form.fields[cf].round.currently_active = form.cleaned_data[cf]
                        form.fields[cf].round.save()
                    if cf.startswith("review-"):
                        changes.append(
                            (
                                (
                                    "set reviewing"
                                    if form.cleaned_data[cf]
                                    else "set no review"
                                ),
                                form.fields[cf].round,
                            )
                        )
                        form.fields[cf].round.review_phase = form.cleaned_data[cf]
                        form.fields[cf].round.save()

                    if cf == "protection":
                        trn.results_access = form.cleaned_data[cf]
                        trn.save()
                        messages.add_message(
                            request,
                            messages.SUCCESS,
                            "Set access control to %s"
                            % trn.get_results_access_display(),
                        )

                    if cf == "slides_public":
                        trn.slides_public = form.cleaned_data[cf]
                        trn.save()
                        messages.add_message(
                            request,
                            messages.SUCCESS,
                            "Set slides public access to %s" % trn.slides_public,
                        )

                    if cf == "password":
                        pw = make_password(form.cleaned_data[cf])
                        trn.results_password = pw
                        trn.save()
                        purge_sessions(trn)
                        messages.add_message(
                            request,
                            messages.SUCCESS,
                            "Password changed, all sessions are closed",
                        )

                cgs = format_html_join("", "<li>{} for {}</li>", (c for c in changes))
                if len(changes) > 0:
                    messages.add_message(
                        request,
                        messages.SUCCESS,
                        mark_safe("Saved assignments with changes: <ul>%s</ul>" % cgs),
                    )
            else:
                messages.add_message(request, messages.WARNING, "No changes made")
        else:
            messages.add_message(request, messages.ERROR, "Form contains errors")

        return render(request, "fight/publish.html", context={"form": form})


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("jury.publish_fights"), name="dispatch")
class PdfPreviewView(ObjectDownloadView):

    attachment = False

    mimetype = "application/pdf"

    def get_object(self, queryset=None):
        try:
            obj = Fight.objects.get(
                round__tournament=self.request.user.profile.tournament,
                id=self.kwargs["fight_id"],
            ).pdf_preview
            if not obj.status in [Pdf.SUCCESS, Pdf.UPLOAD]:
                raise Pdf.DoesNotExist("File not yet available")
            return obj.file
        except:
            raise Pdf.DoesNotExist("File does not exist")


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("jury.publish_fights"), name="dispatch")
class PdfResultView(ObjectDownloadView):

    attachment = False

    mimetype = "application/pdf"

    def get_object(self, queryset=None):
        try:
            obj = Fight.objects.get(
                round__tournament=self.request.user.profile.tournament,
                id=self.kwargs["fight_id"],
            ).pdf_result
            if not obj.status in [Pdf.SUCCESS, Pdf.UPLOAD]:
                raise Pdf.DoesNotExist("File not yet available")
            return obj.file
        except:
            raise Pdf.DoesNotExist("File does not exist")


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("jury.publish_fights"), name="dispatch")
class PdfRankingView(ObjectDownloadView):

    attachment = False

    mimetype = "application/pdf"

    def get_object(self, queryset=None):
        try:
            obj = Round.objects.get(
                tournament=self.request.user.profile.tournament,
                order=self.kwargs["round_nr"],
            ).pdf_ranking
            if not obj.status in [Pdf.SUCCESS, Pdf.UPLOAD]:
                raise Pdf.DoesNotExist("File not yet available")
            return obj.file
        except:
            raise Pdf.DoesNotExist("File does not exist")


@login_required
@permission_required("jury.publish_fights")
def genpdfpreview(request, fight_id):

    if request.method == "POST" or True:

        trn = request.user.profile.tournament
        fight = get_object_or_404(Fight, pk=fight_id, round__tournament=trn)

        context = context_generator.preview(fight)

        fileprefix = "preview-round-%d-room-%s-v" % (fight.round.order, fight.room.name)

        pdf = Pdf.objects.create(
            name="%s%d" % (fileprefix, _get_next_pdfname(trn, fileprefix)),
            tournament=trn,
        )

        res = render_to_pdf.delay(
            trn.default_templates.get(type=Template.PREVIEW).id, pdf.id, context=context
        )

        pdf.task_id = res.id
        pdf.save()

        pdf.tags.add(PdfTag.objects.get(tournament=trn, type=Template.PREVIEW))

        fight.pdf_preview = pdf
        fight.save()

    return redirect("fight:publish")


@login_required
@permission_required("jury.publish_fights")
def genpdfresult(request, fight_id):

    if request.method == "POST" or True:

        trn = request.user.profile.tournament
        fight = get_object_or_404(Fight, pk=fight_id, round__tournament=trn)

        context = context_generator.result(fight)

        fileprefix = "result-round-%d-room-%s-v" % (fight.round.order, fight.room.name)

        pdf = Pdf.objects.create(
            name="%s%d" % (fileprefix, _get_next_pdfname(trn, fileprefix)),
            tournament=trn,
        )

        res = render_to_pdf.delay(
            trn.default_templates.get(type=Template.RESULTS).id, pdf.id, context=context
        )

        pdf.task_id = res.id
        pdf.save()

        pdf.tags.add(PdfTag.objects.get(tournament=trn, type=Template.RESULTS))

        fight.pdf_result = pdf
        fight.save()

    return redirect("fight:publish")


@login_required
@permission_required("jury.publish_fights")
def genpdfrank(request, round_nr):

    if request.method == "POST" or True:

        trn = request.user.profile.tournament
        round = get_object_or_404(Round, order=round_nr, tournament=trn)

        context = context_generator.ranking(round)

        fileprefix = "ranking-round-%d-v" % (round.order)

        pdf = Pdf.objects.create(
            name="%s%d" % (fileprefix, _get_next_pdfname(trn, fileprefix)),
            tournament=trn,
        )

        res = render_to_pdf.delay(
            trn.default_templates.get(type=Template.RANKING).id, pdf.id, context=context
        )

        pdf.task_id = res.id
        pdf.save()

        pdf.tags.add(PdfTag.objects.get(tournament=trn, type=Template.RANKING))

        round.pdf_ranking = pdf
        round.save()

    return redirect("fight:publish")


@login_required
@permission_required("jury.clock")
def fightclock(request, fight_id, stage):

    return render(
        request,
        "fight/clock.xml",
        context={
            "id": fight_id,
            "stage": stage,
            "phases": request.user.profile.tournament.phase_set.all(),
        },
        content_type="image/svg+xml",
    )


@login_required
@permission_required("jury.clock")
def fightreplicaclock(request, fight_id, stage):

    return render(
        request,
        "fight/replicaclock.xml",
        context={
            "id": fight_id,
            "stage": stage,
            "phases": request.user.profile.tournament.phase_set.all(),
        },
        content_type="image/svg+xml",
    )


@login_required
@permission_required("jury.clocks")
def clocks(request, round_nr):
    phases = request.user.profile.tournament.phase_set.all()
    duration = sum(phases.values_list("duration", flat=True))
    fights = request.user.profile.tournament.round_set.get(
        order=round_nr
    ).fight_set.all()
    st = []
    for i in range(1, 5):
        stages = Stage.objects.filter(
            fight__round__tournament=request.user.profile.tournament,
            fight__round__order=round_nr,
            order=i,
        )
        st.append(stages)
    return render(
        request,
        "fight/clocks.html",
        context={"phases": phases, "total_duration": duration, "stages": st},
    )


@login_required
@permission_required("jury.clocks")
def fight_phases(request, round_nr):

    r = get_object_or_404(
        Round, order=round_nr, tournament=request.user.profile.tournament
    )
    fst = []
    for fi in r.fight_set.all():
        fst.append({"data": ClockState.objects.filter(stage__fight=fi), "fight": fi})

    return render(request, "fight/fight_phases.html", context={"fights": fst})
