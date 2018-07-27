from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django_downloadview import ObjectDownloadView

from apps.dashboard.delete import ConfirmedDeleteView
from apps.plan.models import StageAttendance, TeamPlaceholder
from apps.printer import context_generator
from apps.printer.models import Pdf, PdfTag, Template
from apps.printer.tasks import render_to_pdf
from apps.printer.utils import _get_next_pdfname
from apps.team.models import Team
from apps.tournament.models import ScheduleTemplate

from .forms import TeamDrawForm
from .models import Round

# Create your views here.

@login_required
@permission_required('plan.view_plan')
def plan(request):


    rounds = Round.objects.filter(tournament = request.user.profile.tournament)\
        .order_by('order')\
        .prefetch_related('fight_set__stage_set__stageattendance_set',
                          'fight_set__room',
                          'fight_set__stage_set__rejections',
                          'fight_set__stage_set__stageattendance_set__role')
    return render(request, "plan/plan.html", context={'rounds':rounds})


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('plan.add_fight', raise_exception=False), name='dispatch')
class Placeholder(View):

    def get(self, request):

        scheds=ScheduleTemplate.objects.all()

        rounds = Round.selectives\
            .filter(tournament = request.user.profile.tournament)\
            .order_by('order')\
            .prefetch_related('fight_set__stage_set__stageattendance_set__role'
                              ,'fight_set__stage_set__stageattendance_set__team_placeholder'
                              ,'fight_set__room')
        return render(request, "plan/overview.html", context={'rounds':rounds,'schedules':scheds})





@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('plan.view_placeholders'), name='dispatch')
class PlaceholderTeams(View):

    def get(self,request):

        realnr = Team.competing.filter(tournament=request.user.profile.tournament).count()

        form = TeamDrawForm(request.user.profile.tournament)

        return render(request, "plan/phteams.html", context={'form':form,'realnr':realnr})

    @method_decorator(permission_required('plan.assign_placeholders',raise_exception=False))
    def post(self,request):

        realnr = Team.competing.filter(tournament=request.user.profile.tournament).count()

        form = TeamDrawForm(request.user.profile.tournament, request.POST)

        if form.is_valid():
            chgd=[]
            for k in form.changed_data:
                #print("ph:%s to: %s"%(form.placeholders[k],form.cleaned_data[k]))

                try:
                    if form.cleaned_data[k].teamplaceholder:
                        #print("already has a placeholder")
                        oldholder = form.cleaned_data[k].teamplaceholder
                        oldholder.team = None
                        oldholder.save()
                except:
                    pass
                form.placeholders[k].team=form.cleaned_data[k]
                form.placeholders[k].save()
                chgd.append(form.placeholders[k].name)

            messages.add_message(request,messages.INFO,"%s assigned"%(", ".join(chgd)))

        return render(request, "plan/phteams.html", context={'form': form, 'realnr': realnr})

@login_required
@permission_required('plan.assign_placeholders')
def drawTeam(request,team_id,placeholder_nr):
    if request.method == 'POST':
        trn = request.user.profile.tournament
        team = get_object_or_404(Team, id=team_id, tournament=trn)
        placeholder = get_object_or_404(TeamPlaceholder, name="Team %d"%int(placeholder_nr), tournament=trn)

        try:
            ph = team.teamplaceholder
            ph.team = None
            ph.save()
        except:
            pass

        placeholder.team = team
        placeholder.save()

        return JsonResponse({"assigned":team.pk})

@login_required
@permission_required('plan.assign_placeholders')
def drawdelTeam(request,team_id):
    if request.method == 'POST':
        trn = request.user.profile.tournament
        team = get_object_or_404(Team, id=team_id, tournament=trn)

        ph = team.teamplaceholder
        ph.team = None
        ph.save()

        return JsonResponse({"assigned":team.pk})

@login_required
@permission_required('plan.assign_placeholders')
def phbeamercontrol(request):

    trn=request.user.profile.tournament

    phteams = trn.teamplaceholder_set.all()
    teams = trn.team_set(manager='competing').all().order_by("origin__name")
    #print(teams)
    return render(request, "plan/beamerControl.html", context={"teams":teams, "phteams": phteams})

@login_required
@permission_required('plan.assign_placeholders')
def phbeamer(request):

    trn=request.user.profile.tournament

    ro = trn.round_set.first()
    return render(request, "plan/beamerDraw.html", context={"round":ro, "wide":trn.draw_wide})


@login_required
@permission_required('plan.add_teamplaceholder',raise_exception=False)
def phteamsgen(request):

    if request.method == 'POST':
        trn=request.user.profile.tournament

        realnr = Team.competing.filter(tournament=trn).count()
        for i in range(1,realnr+1):
            TeamPlaceholder.objects.get_or_create(tournament=trn,name="Team %d"%(i,))

    return redirect('plan:phteams')

@login_required
@permission_required('plan.delete_teamplaceholder',raise_exception=False)
def phteamsdel(request):

    if request.method == 'POST':
        trn = request.user.profile.tournament
        tp = TeamPlaceholder.objects.filter(tournament=trn)
        if "_last" in request.POST:
            tp.last().delete()
        elif "_all" in request.POST:
            tp.delete()

    return redirect('plan:phteams')

@login_required
@permission_required('plan.apply_schedule',raise_exception=False)
@transaction.atomic
def phplanapply(request):

    if request.method == 'POST':
        trn = request.user.profile.tournament
        sas = StageAttendance.objects.filter(stage__fight__round__tournament=trn)\
              .values("team").distinct()
        if sas.count() == 1 and sas[0]['team'] == None:

            if not TeamPlaceholder.objects.filter(tournament=trn,team=None).exists():

                for sa in StageAttendance.objects.filter(stage__fight__round__tournament=trn):
                    sa.team = sa.team_placeholder.team
                    sa.save()

                messages.add_message(request,messages.SUCCESS, "Teams successfully mapped according to draw")
                return redirect("plan:plan")

            messages.add_message(request,messages.ERROR, "Unassigned placeholder teams found")
            return redirect("plan:placeholder")

        messages.add_message(request,messages.ERROR, "Already assigned fights found")
        return redirect("plan:placeholder")

    return HttpResponseNotAllowed(['POST'])

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('plan.delete_round',raise_exception=False),name='dispatch')
class PhPlanDelete(ConfirmedDeleteView):

    redirection = "plan:placeholder"

    def get_objects(self, request, *args, **kwargs):
        return Round.objects.filter(tournament=request.user.profile.tournament)


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('plan.delete_final',raise_exception=False),name='dispatch')
class FinalDelete(ConfirmedDeleteView):

    redirection = "plan:final"

    def get_objects(self, request, *args, **kwargs):
        return Round.finals.get(tournament=request.user.profile.tournament).fight_set.all()


@login_required
def genpdfteamround(request, round_nr):

    if request.method == "POST":

        trn = request.user.profile.tournament
        round = get_object_or_404(Round, order=round_nr, tournament=trn)

        context = context_generator.teamround(round)

        fileprefix="team-round-%d-v"%(round.order)

        pdf = Pdf.objects.create(name="%s%d"%(fileprefix,_get_next_pdfname(trn, fileprefix)), tournament=trn)

        res = render_to_pdf.delay(trn.default_templates.get(type=Template.TEAMROUND).id, pdf.id, context=context)

        pdf.task_id = res.id
        pdf.save()

        try:
            pdf.tags.add(PdfTag.objects.get(tournament=trn, type=Template.TEAMROUND))
        except:
            messages.add_message(request, messages.WARNING,
                                 "No PDF Tag found for Team Round")


        round.pdf_teamplan = pdf
        round.save()

        return redirect("plan:plan")

    return HttpResponseNotAllowed(['POST'])

@method_decorator(login_required, name='dispatch')
#@method_decorator(permission_required("plan.view_jury"), name='dispatch')
class PdfTeamView(ObjectDownloadView):

    attachment = False

    mimetype = "application/pdf"

    def get_object(self, queryset=None):
        try:
            obj = Round.objects.get(tournament=self.request.user.profile.tournament, order=self.kwargs['round']).pdf_teamplan
            if not obj.status in [Pdf.SUCCESS, Pdf.UPLOAD]:
                raise Pdf.DoesNotExist("File not yet available")
            return obj.file
        except:
            raise Pdf.DoesNotExist("File does not exist")


@login_required
def genpdfproblemselect(request, round_nr):

    if request.method == "POST":

        trn = request.user.profile.tournament
        round = get_object_or_404(Round, order=round_nr, tournament=trn)

        context = context_generator.problem_select(round)

        fileprefix="problem-selection-round-%d-v"%(round.order)

        pdf = Pdf.objects.create(name="%s%d"%(fileprefix,_get_next_pdfname(trn, fileprefix)), tournament=trn)

        res = render_to_pdf.delay(trn.default_templates.get(type=Template.PROBLEMSELECT).id, pdf.id, context=context)

        pdf.task_id = res.id
        pdf.save()

        try:
            pdf.tags.add(PdfTag.objects.get(tournament=trn, type=Template.PROBLEMSELECT))
        except:
            messages.add_message(request, messages.WARNING,
                                 "No PDF Tag found for Problem Select")


        round.pdf_problem_select = pdf
        round.save()

        return redirect("plan:plan")

    return HttpResponseNotAllowed(['POST'])

@method_decorator(login_required, name='dispatch')
#@method_decorator(permission_required("plan.view_jury"), name='dispatch')
class PdfProblemSelect(ObjectDownloadView):

    attachment = False

    mimetype = "application/pdf"

    def get_object(self, queryset=None):
        try:
            obj = Round.objects.get(tournament=self.request.user.profile.tournament, order=self.kwargs['round']).pdf_problem_select
            if not obj.status in [Pdf.SUCCESS, Pdf.UPLOAD]:
                raise Pdf.DoesNotExist("File not yet available")
            return obj.file
        except:
            raise Pdf.DoesNotExist("File does not exist")
