import statistics
from datetime import datetime

from celery.result import AsyncResult
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth.decorators import login_required, permission_required
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.text import capfirst
from django.views import View, generic
from django_downloadview import ObjectDownloadView

from apps.account.models import ActiveUser, ParticipationRole
from apps.dashboard.delete import ConfirmedDeleteView
from apps.plan.models import Fight, Round, Stage
from apps.printer import context_generator
from apps.printer.models import Pdf, PdfTag, Template
from apps.printer.tasks import render_to_pdf, render_to_pdf_local
from apps.printer.utils import _get_next_pdfname
from apps.registration.models import AttendeeProperty, Property, UserPropertyValue
from apps.registration.utils import application_propertyvalues

from .forms import AcceptPossibleJurorForm, AssignForm, JurorForm, JuryForm
from .models import AssignResult, Juror, JurorRole, JurorSession, PossibleJuror
from .tasks import assignJob, renderFeedback, renderSheets
from .utils import assignments_light, create_fight_gradingsheets, plan_from_db


@method_decorator(login_required, name="dispatch")
class ListAssignments(View):

    def get(self, request):

        trn = request.user.profile.tournament

        form = AssignForm()

        results = []
        for result in AssignResult.objects.filter(tournament=trn).order_by("-created"):
            res = AsyncResult(result.task_id)
            p = None
            cost = None
            if res.state == "PROGRESS":
                p = 100 * res.info["current"] / res.info["total"]
            if res.successful():
                if len(res.result[0]) > 0:
                    cost = res.result[1]
                    if type(cost) == dict:
                        cost = cost["best_cost"]
                else:
                    cost = "errors"
            results.append(
                {"task": result, "state": res.state, "progress": p, "cost": cost}
            )

        return render(
            request,
            "jury/assignments.html",
            context={"assignments": results, "form": form},
        )


@login_required
def assignJurors(request):

    if request.method == "POST":

        trn = request.user.profile.tournament

        form = AssignForm(request.POST)

        if form.is_valid():

            if "_output" in request.POST:
                data = {
                    "simulation_rounds": form.cleaned_data["rounds"],
                    "jurors_per_room": form.cleaned_data["room_jurors"],
                    "cooling_base": form.cleaned_data["cooling_base"],
                    "fix_rounds": form.cleaned_data["fix_rounds"],
                }

                teams = []

                for t in trn.team_set.all():
                    teams.append({"id": t.origin.id, "name": t.origin.name})
                data["teams"] = teams

                jurors = []
                for jr in Juror.objects.filter(attendee__tournament_id=trn.id):
                    avgrp = None
                    if jr.availability_group:
                        avgrp = jr.availability_group.id
                    juror = {
                        "id": jr.id,
                        "name": jr.attendee.full_name,
                        "experience": jr.experience,
                        "availability": [
                            round in jr.availability.all()
                            for round in trn.round_set.all()
                        ],
                        "possible_chair": jr.possible_chair,
                        "local": jr.local,
                        "conflicts": jr.conflicting_ids_cached,
                        "bias": jr.bias,
                        "max_assignments": jr.max_assign,
                        "max_chairing": jr.max_chair,
                        "availability_group": avgrp,
                    }
                    jurors.append(juror)
                data["jurors"] = jurors

                schedule = []
                plan = []
                for r in trn.round_set(manager="selectives").all():
                    round = {"id": r.id, "fights": []}
                    for f in r.fight_set.all():
                        round["fights"].append(
                            {
                                "id": f.id,
                                "teams": list(
                                    f.stage_set.get(order=1)
                                    .attendees.all()
                                    .values_list("origin_id", flat=True)
                                ),
                                "room": f.room.name,
                            }
                        )
                    schedule.append(round)

                    if r.order <= data["fix_rounds"]:
                        round_fights = {
                            "fights": [],
                            "reserve": list(
                                r.reserved_jurors.all().values_list("id", flat=True)
                            ),
                            "id": r.id,
                        }

                        for fight in r.fight_set.all():
                            fight_data = {
                                "fight": fight.id,
                                "room": fight.room.name,
                                "jurors": [],
                                "nonvoting": [],
                            }

                            fight_data["jurors"] = [
                                js.juror.id
                                for js in list(
                                    fight.jurorsession_set(manager="voting").all()
                                )
                            ]
                            fight_data["nonvoting"] = [
                                js.juror.id
                                for js in list(
                                    fight.jurorsession_set(manager="nonvoting").all()
                                )
                            ]

                            round_fights["fights"].append(fight_data)

                        plan.append(round_fights)

                data["schedule"] = schedule
                data["plan"] = plan

                return JsonResponse(data)
            else:
                rounds = form.cleaned_data["rounds"]
                room_jurors = form.cleaned_data["room_jurors"]
                cooling_base = form.cleaned_data["cooling_base"]
                fix_rounds = form.cleaned_data["fix_rounds"]
                res = assignJob.delay(
                    trn.id,
                    total_rounds=rounds,
                    room_jurors=room_jurors,
                    cooling_base=cooling_base,
                    fix_rounds=fix_rounds,
                )

                AssignResult.objects.create(
                    tournament=trn,
                    task_id=res.id,
                    author=request.user.profile.active,
                    total_rounds=rounds,
                    room_jurors=room_jurors,
                    cooling_base=cooling_base,
                    fix_rounds=fix_rounds,
                )

                # return render(request, "jury/assign.html", context={"rounds":plan,'assignments':assignment_sorted})
                return redirect("jury:assign_preview", res.id)
        else:
            return redirect("jury:assign")

    return HttpResponseNotAllowed(["POST"])


@method_decorator(login_required, name="dispatch")
class JurorChange(generic.UpdateView):

    form_class = JurorForm

    success_url = reverse_lazy("jury:jurors")

    def get_object(self, queryset=None):
        obj = Juror.objects.get(
            id=self.kwargs["juror_id"],
            attendee__tournament=self.request.user.profile.tournament,
        )
        return obj


@login_required
def cost_graph(request, id):

    res = AsyncResult(id)
    get_object_or_404(
        AssignResult, task_id=res.id, tournament=request.user.profile.tournament
    )
    if res.successful():

        cost_obj = res.result[1]

        costs = []
        best_costs = []
        total = 0
        dissect = {}

        try:
            costs = cost_obj["cost_graph"]["total"]
            best_costs = cost_obj["best_cost_graph"]
            total = len(costs)
            dissect = cost_obj["cost_graph"]
            del dissect["total"]
        except:
            pass

        return render(
            request,
            "jury/cost_graph.html",
            context={
                "costs": costs,
                "best_costs": best_costs,
                "total": total,
                "dissect": dissect,
            },
        )


@method_decorator(login_required, name="dispatch")
class DisplayAssign(View):
    def get(self, request, id):

        trn = request.user.profile.tournament

        res = AsyncResult(id)
        ar = get_object_or_404(AssignResult, task_id=res.id, tournament=trn)

        plan = []
        assignment_sorted = []

        if res.successful() and len(res.result[0]) > 0:
            plan = res.result[0]
            cost_obj = res.result[1]

            costs = []
            best_costs = []
            total = 0
            dissect = {}

            try:
                costs = cost_obj["cost_graph"]["total"]
                best_costs = cost_obj["best_cost_graph"]
                total = len(costs)
                dissect = cost_obj["cost_graph"]
                del dissect["total"]
            except:
                pass

            # TODO: count at least one availability
            jurors_at_least_once = Juror.objects.filter(attendee__tournament=trn)

            assignment_sorted = assignments_light(plan, jurors_at_least_once)

            assigned_jurors = JurorSession.objects.filter(
                fight__round__tournament=trn, fight__round__order__gt=ar.fix_rounds
            ).exists()

            return render(
                request,
                "jury/assign.html",
                context={
                    "uuid": res.id,
                    "rounds": plan,
                    "assignments": assignment_sorted,
                    "assigned": assigned_jurors,
                    "costs": costs,
                    "best_costs": best_costs,
                    "total": total,
                    "dissect": dissect,
                    "object": ar,
                },
            )

        elif res.successful():
            errors = res.result[1]

            return render(request, "jury/errors.html", context={"errors": errors})

        else:
            if res.state == "PROGRESS":
                p = 100 * res.info["current"] / res.info["total"]
                ticks = res.info["total"] // 50
                try:
                    return render(
                        request,
                        "jury/progress.html",
                        context={
                            "progress": p,
                            "costs": res.info["costs"]["total"][0::ticks],
                            "best_costs": res.info["best_costs"][0::ticks],
                            "total": res.info["total"] / ticks,
                            "tickspace": ticks,
                        },
                    )
                except:
                    return render(request, "jury/pending.html")
            else:
                return render(request, "jury/pending.html")

    @method_decorator(permission_required("jury.assign_jurors"))
    @method_decorator(transaction.atomic)
    def post(self, request, id):

        trn = request.user.profile.tournament

        res = AsyncResult(id)
        ar = get_object_or_404(AssignResult, task_id=res.id, tournament=trn)

        if not JurorSession.objects.filter(
            fight__round__tournament=trn, fight__round__order__gt=ar.fix_rounds
        ).exists():
            if res.successful() and len(res.result[0]) > 0:
                chair_role = JurorRole.objects.get(type=JurorRole.CHAIR, tournament=trn)
                juror_role = JurorRole.objects.get(type=JurorRole.JUROR, tournament=trn)
                nonvote_role = JurorRole.objects.get(
                    type=JurorRole.NONVOTING, tournament=trn
                )

                plan = res.result[0]
                for round in plan[ar.fix_rounds :]:
                    for fight in round:
                        fobj = Fight.objects.get(pk=fight["pk"])
                        chair = Juror.objects.get(pk=fight["chair"]["id"])
                        jurors = Juror.objects.filter(
                            id__in=list(map(lambda x: x["id"], fight["jurors"]))
                        )
                        nonvoting = Juror.objects.filter(
                            id__in=list(map(lambda x: x["id"], fight["nonvoting"]))
                        )

                        JurorSession.objects.create(
                            juror=chair, fight=fobj, role=chair_role
                        )
                        for juror in jurors:
                            JurorSession.objects.create(
                                juror=juror, fight=fobj, role=juror_role
                            )
                        for juror in nonvoting:
                            JurorSession.objects.create(
                                juror=juror, fight=fobj, role=nonvote_role
                            )

        return redirect("jury:plan")


@login_required
def jurorlist(request):

    jurors = Juror.objects.filter(
        attendee__tournament=request.user.profile.tournament
    ).prefetch_related("availability", "attendee__active_user__user", "conflicting")

    rounds = Round.objects.filter(tournament=request.user.profile.tournament)

    return render(
        request, "jury/persons.html", context={"persons": jurors, "rounds": rounds}
    )


@method_decorator(login_required, name="dispatch")
class JuryPlan(generic.ListView):
    template_name = "jury/plan.html"
    context_object_name = "rounds"

    def get_queryset(self):
        return Round.objects.filter(
            tournament=self.request.user.profile.tournament
        ).prefetch_related(
            "fight_set__room",
            "fight_set__jurorsession_set__juror__attendee__active_user__user",
            "fight_set__jurorsession_set__role",
            "fight_set__stage_set__stageattendance_set__team__origin",
        )

    def get_context_data(self, **kwargs):
        context = super(JuryPlan, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        trn = self.request.user.profile.tournament
        freeJ = []
        for round in Round.objects.filter(tournament=trn):
            freeJr = {"round": round.order}
            freeJr["jurors"] = (
                Juror.objects.filter(attendee__tournament=trn, availability=round)
                .exclude(fights__in=round.fight_set.all())
                .prefetch_related("attendee__active_user__user")
            )

            try:
                res = AsyncResult(round.feedback_task_id)
                freeJr["feedback_task"] = res
            except:
                pass

            try:
                res = AsyncResult(round.grading_task_id)
                freeJr["sheet_task"] = res
            except:
                pass

            freeJ.append(freeJr)

        context["freeJ"] = freeJ

        # find never used but available Jurors
        unused = Juror.objects.filter(
            attendee__tournament=trn,
            availability__in=Round.objects.filter(tournament=trn),
        ).distinct()
        for round in Round.objects.filter(tournament=trn):
            unused = unused.exclude(
                jurorsession__fight__in=round.fight_set.all(),
                jurorsession__role__type__in=[JurorRole.CHAIR, JurorRole.JUROR],
            )

        context["unusedJ"] = unused

        # list assignments:

        plan = plan_from_db(trn)

        jurors_at_least_once = Juror.objects.filter(attendee__tournament=trn)

        assignment_sorted = assignments_light(plan, jurors_at_least_once)

        context["assignments"] = assignment_sorted

        return context


@login_required
def genpdfjuryround(request, round_nr):

    if request.method == "POST":

        trn = request.user.profile.tournament
        round = get_object_or_404(Round, order=round_nr, tournament=trn)

        context = context_generator.juryround(round)

        fileprefix = "jury-round-%d-v" % (round.order)

        pdf = Pdf.objects.create(
            name="%s%d" % (fileprefix, _get_next_pdfname(trn, fileprefix)),
            tournament=trn,
        )

        res = render_to_pdf.delay(
            trn.default_templates.get(type=Template.JURYROUND).id,
            pdf.id,
            context=context,
        )

        pdf.task_id = res.id
        pdf.save()

        try:
            pdf.tags.add(PdfTag.objects.get(tournament=trn, type=Template.JURYROUND))
        except:
            messages.add_message(
                request, messages.WARNING, "No PDF Tag found for Jury Round"
            )

        round.pdf_juryplan = pdf
        round.save()

        return redirect("jury:plan")

    return HttpResponseNotAllowed(["POST"])


@login_required
def genallpdfjuryfeedback(request, round_nr):

    if request.method == "POST":

        trn = request.user.profile.tournament
        round = get_object_or_404(Round, order=round_nr, tournament=trn)

        baseurl = request.build_absolute_uri("/")[:-1]

        task = renderFeedback.delay(baseurl, round.id)

        round.feedback_task_id = task.id
        round.save()

        return redirect("jury:plan")

    return HttpResponseNotAllowed(["POST"])


@login_required
def genpdfjuryfeedback(request, fight_id):

    if request.method == "POST":

        trn = request.user.profile.tournament
        fight = get_object_or_404(Fight, pk=fight_id, round__tournament=trn)

        context = context_generator.juryfeedback(
            request.build_absolute_uri("/")[:-1], fight
        )

        fileprefix = "jury-feedback-round-%d-room-%s-v" % (
            fight.round.order,
            fight.room.name,
        )

        pdf = Pdf.objects.create(
            name="%s%d" % (fileprefix, _get_next_pdfname(trn, fileprefix)),
            tournament=trn,
        )

        res = render_to_pdf.delay(
            trn.default_templates.get(type=Template.JURYFEEDBACK).id,
            pdf.id,
            context=context,
        )

        pdf.task_id = res.id
        pdf.save()

        try:
            pdf.tags.add(PdfTag.objects.get(tournament=trn, type=Template.JURYFEEDBACK))
        except:
            messages.add_message(
                request, messages.WARNING, "No PDF Tag found for Jury Round"
            )

        fight.pdf_jury_feedback = pdf
        fight.save()

        return redirect("jury:plan")

    return HttpResponseNotAllowed(["POST"])


@login_required
def genallpdfjurysheets(request, round_nr):

    if request.method == "POST":

        trn = request.user.profile.tournament
        round = get_object_or_404(Round, order=round_nr, tournament=trn)

        task = renderSheets.delay(round.id)

        round.grading_task_id = task.id
        round.save()

        return redirect("jury:plan")

    return HttpResponseNotAllowed(["POST"])


@login_required
def genpdfjurysheets(request, fight_id):

    if request.method == "POST":

        trn = request.user.profile.tournament
        fight = get_object_or_404(Fight, pk=fight_id, round__tournament=trn)
        try:
            tpl_id = trn.default_templates.get(type=Template.GRADING).id
        except:
            messages.add_message(request, messages.WARNING, "Default Template not set")
            return redirect("jury:plan")
        create_fight_gradingsheets(fight)

        return redirect("jury:plan")

    return HttpResponseNotAllowed(["POST"])


@login_required
def jurorplan(request, juror_id):

    juror = get_object_or_404(Juror, pk=juror_id)
    att = juror.jurorsession_set.order_by("fight__round__order").all()
    return render(
        request, "jury/juror.html", context={"juror": juror, "attendences": att}
    )


@method_decorator(login_required, name="dispatch")
class FightView(View):

    def get(self, request, fight_id):

        fight = get_object_or_404(Fight, pk=fight_id)

        form = JuryForm(fight)

        return render(
            request,
            "jury/fight.html",
            context={
                "round": fight.round.order,
                "room": fight.room.name,
                "attendants": fight.stage_set.all()[0],
                "form": form,
            },
        )

    @method_decorator(permission_required("jury.change_jurorsession"))
    def post(self, request, fight_id):

        fight = get_object_or_404(Fight, pk=fight_id)

        trn = request.user.profile.tournament

        form = JuryForm(fight, request.POST)
        if form.is_valid():
            try:
                current_chairrole = fight.jurorsession_set.get(
                    role__type=JurorRole.CHAIR
                )
                current_chairrole_juror = current_chairrole.juror
            except:
                current_chairrole = None
                current_chairrole_juror = None

            if form.cleaned_data["chair"]:
                new_juror = form.cleaned_data["chair"]
                if current_chairrole_juror != form.cleaned_data["chair"]:
                    # replace role with newly assigned
                    if current_chairrole:
                        current_chairrole.delete()

                    # clean up jurors other assignments
                    try:
                        JurorSession.objects.get(
                            juror=new_juror, fight__round=self.round
                        ).delete()
                    except:
                        pass
                    JurorSession.objects.create(
                        juror=new_juror,
                        fight=fight,
                        role=JurorRole.objects.get(
                            type=JurorRole.CHAIR, tournament=trn
                        ),
                    )

            elif current_chairrole:
                current_chairrole.delete()

            # jurors

            jnow_pk = set(form.cleaned_data["jurors"])
            jold_pk = set(form.fields["jurors"].obj_initial)

            print(jnow_pk)

            print(jold_pk)

            jrm_pk = jold_pk - jnow_pk
            jadd_pk = jnow_pk - jold_pk
            for jrm in list(jrm_pk):
                fight.jurorsession_set.get(juror=jrm).delete()

            for jadd in list(jadd_pk):
                try:
                    JurorSession.objects.get(
                        juror=jadd, fight__round=self.round
                    ).delete()
                except:
                    pass

                JurorSession.objects.create(
                    juror=jadd,
                    fight=fight,
                    role=JurorRole.objects.get(type=JurorRole.JUROR, tournament=trn),
                )

        return render(
            request,
            "jury/fight.html",
            context={
                "round": fight.round.order,
                "room": fight.room.name,
                "attendants": fight.stage_set.all()[0],
                "form": form,
            },
        )


@method_decorator(login_required, name="dispatch")
# @method_decorator(permission_required("plan.view_juror"), name='dispatch')
class PdfJuryView(ObjectDownloadView):

    attachment = False

    mimetype = "application/pdf"

    def get_object(self, queryset=None):
        try:
            obj = Round.objects.get(
                tournament=self.request.user.profile.tournament,
                order=self.kwargs["round"],
            ).pdf_juryplan
            if not obj.status in [Pdf.SUCCESS, Pdf.UPLOAD]:
                raise Pdf.DoesNotExist("File not yet available")
            return obj.file
        except:
            raise Pdf.DoesNotExist("File does not exist")


@method_decorator(login_required, name="dispatch")
# @method_decorator(permission_required("plan.view_juror"), name='dispatch')
class PdfJuryFeedback(ObjectDownloadView):

    attachment = False

    mimetype = "application/pdf"

    def get_object(self, queryset=None):
        try:
            obj = Fight.objects.get(
                round__tournament=self.request.user.profile.tournament,
                id=self.kwargs["fight_id"],
            ).pdf_jury_feedback
            if not obj.status in [Pdf.SUCCESS, Pdf.UPLOAD]:
                raise Pdf.DoesNotExist("File not yet available")
            return obj.file
        except:
            raise Pdf.DoesNotExist("File does not exist")


@method_decorator(login_required, name="dispatch")
# @method_decorator(permission_required("plan.view_juror"), name='dispatch')
class PdfJuryOverview(ObjectDownloadView):

    attachment = False

    mimetype = "application/pdf"

    def get_object(self, queryset=None):
        try:
            obj = Fight.objects.get(
                round__tournament=self.request.user.profile.tournament,
                id=self.kwargs["fight_id"],
            ).pdf_grade_overview
            if not obj.status in [Pdf.SUCCESS, Pdf.UPLOAD]:
                raise Pdf.DoesNotExist("File not yet available")
            return obj.file
        except:
            raise Pdf.DoesNotExist("File does not exist")


@method_decorator(login_required, name="dispatch")
# @method_decorator(permission_required("plan.view_juror"), name='dispatch')
class PdfJurySheet(ObjectDownloadView):

    attachment = False

    mimetype = "application/pdf"

    def get_object(self, queryset=None):
        try:
            obj = Stage.objects.get(
                fight__round__tournament=self.request.user.profile.tournament,
                fight__id=self.kwargs["fight_id"],
                order=self.kwargs["stage_order"],
            ).pdf_grading_sheets
            if not obj.status in [Pdf.SUCCESS, Pdf.UPLOAD, Pdf.MERGE]:
                raise Pdf.DoesNotExist("File not yet available")
            return obj.file
        except:
            raise Pdf.DoesNotExist("File does not exist")


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("jury.delete_all_jurorsessions", raise_exception=False),
    name="dispatch",
)
class JuryClean(ConfirmedDeleteView):

    def get_objects(self, request, *args, **kwargs):
        trn = request.user.profile.tournament
        return JurorSession.objects.filter(
            fight__round__tournament=trn, fight__round__order__gt=kwargs["fix_rounds"]
        )

    def get_redirection(self, request, *args, **kwargs):
        next = request.GET.get("next", None)
        if next:
            return redirect("jury:assign_preview", id=next)
        else:
            return redirect("jury:assign")


@method_decorator(permission_required("registration.accept_juror"), name="dispatch")
class ViewPossibleJuror(View):

    def get(self, request, id):

        pJ = get_object_or_404(
            PossibleJuror, id=id, tournament=request.user.profile.tournament
        )

        context = application_propertyvalues(
            pJ.tournament,
            ParticipationRole.objects.get(
                type=ParticipationRole.JUROR, tournament=pJ.tournament
            ),
            pJ.person,
        )

        previous = []
        for att in (
            pJ.person.attendee_set.all().order_by("tournament__date_end").reverse()
        ):
            if hasattr(att, "juror"):
                part = att.juror
                jss = []
                for js in att.juror.jurorsession_set.all():
                    jbiases = []
                    for stage in js.fight.stage_set.all():
                        for sa in stage.stageattendance_set.all():
                            holdupgrades = []
                            for jg in sa.jurorgrade_set.all():
                                holdupgrades.append(jg.public_grade)
                            try:
                                mygrade = sa.jurorgrade_set.get(
                                    juror_session=js
                                ).public_grade
                                jbiases.append(mygrade - statistics.mean(holdupgrades))
                            except:
                                pass
                    jsdata = {"jurorsession": js}
                    if len(jbiases):
                        jsdata["bias"] = statistics.mean(jbiases)
                    jss.append(jsdata)
                previous.append({"juror": part, "jurorsessions": jss, "attendee": att})
            else:
                previous.append({"attendee": att})
        print(previous)
        return render(
            request,
            "jury/accept_juror_application.html",
            context={**context, "previous": previous},
        )


@method_decorator(permission_required("registration.accept_juror"), name="dispatch")
class AcceptPossibleJuror(View):

    def get(self, request, id):

        pJ = get_object_or_404(
            PossibleJuror,
            id=id,
            tournament=request.user.profile.tournament,
            approved_at__isnull=True,
        )

        context = application_propertyvalues(
            pJ.tournament,
            ParticipationRole.objects.get(
                type=ParticipationRole.JUROR, tournament=pJ.tournament
            ),
            pJ.person,
        )

        form = AcceptPossibleJurorForm(pJ)

        return render(
            request,
            "jury/accept_juror_application.html",
            context={"form": form, **context},
        )

    def post(self, request, id):
        trn = request.user.profile.tournament

        pJ = get_object_or_404(
            PossibleJuror, id=id, tournament=trn, approved_at__isnull=True
        )

        form = AcceptPossibleJurorForm(pJ, request.POST)

        if form.is_valid():

            if "_accept" in request.POST:

                pJ.approved_at = timezone.now()
                pJ.approved_by = request.user.profile
                if "experience" in form.cleaned_data:
                    pJ.experience = form.cleaned_data["experience"]
                pJ.save()

                if form.cleaned_data["notify"]:
                    send_mail(
                        "Your application for %s as possible Juror was accepted"
                        % (pJ.tournament.name,),
                        "You are now eligible to be part of the jury at the tournament %s. You can now apply in your role to the tournament."
                        % (pJ.tournament.name,),
                        settings.EMAIL_FROM,
                        [pJ.person.user.email],
                        fail_silently=False,
                    )
            elif "_reject" in request.POST:
                pJ.delete()

                if form.cleaned_data["notify"]:
                    send_mail(
                        "Your application for %s as possible Juror was declined"
                        % (pJ.tournament.name,),
                        "Your application was rejected because of: \n%s"
                        % (form.cleaned_data["reason"]),
                        settings.EMAIL_FROM,
                        [pJ.person.user.email],
                        fail_silently=False,
                    )

            return redirect("jury:possiblejurors")

        return render(
            request, "jury/accept_juror_application.html", context={"form": form}
        )
