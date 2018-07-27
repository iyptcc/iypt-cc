from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.cache import caches
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.utils.html import format_html_join, mark_safe
from django.views import View
from django_downloadview import ObjectDownloadView

from apps.dashboard.messages import Message
from apps.dashboard.simpleauth import purge_sessions
from apps.jury.forms import JuryForm
from apps.jury.models import JurorGrade, JurorRole, JurorSession
from apps.plan.models import Fight, Round
from apps.printer import context_generator
from apps.printer.models import Pdf, PdfTag, Template
from apps.printer.tasks import render_to_pdf
from apps.printer.utils import _get_next_pdfname
from apps.result.utils import _fightpreview
from apps.tournament.models import Phase

from .forms import ManageForm, PublishForm, StageForm
from .utils import fight_grades_valid

# Create your views here.

@login_required
@permission_required('jury.change_jurorsession')
def plan(request):

    editall=request.user.has_perm('jury.change_all_jurorsessions')
    rs=[]
    rounds = Round.objects.filter(tournament = request.user.profile.tournament).order_by('order')
    for round in rounds:
        fs=[]
        for f in round.fight_set.select_related('room').all():
            fi={'name':f.room.name,'my':False,'locked':True,'pk':f.pk}
            fi['stages']=range(f.stage_set.count())
            if f.operators.filter(id=request.user.profile.active_id).exists():
                fi['my']=True
                fi['locked']=f.locked
            fs.append(fi)
        rs.append(fs)

    return render(request, "fight/plan.html", context={'rounds':rs,'editall':editall})

@login_required
@permission_required('jury.validate_grades')
def validate_plan(request):

    rs=[]
    rounds = Round.objects.filter(tournament = request.user.profile.tournament).order_by('order')
    for round in rounds:
        fs=[]
        for f in round.fight_set.select_related('room').all():
            fi={'name':f.room.name,'locked':f.locked,'pk':f.pk}
            fi["valid"]= fight_grades_valid(f)
            fs.append(fi)
        rs.append(fs)

    return render(request, "fight/validate.html", context={'rounds':rs})

class FightAssistancePermMixin(UserPassesTestMixin):
    def test_func(self):
        if self.request.user.has_perm('jury.change_all_jurorsessions'):
            return True
        if not self.request.user.has_perm('jury.change_jurorsession'):
            return False
        try:
            fi = Fight.objects.get(pk=self.request.resolver_match.kwargs['fight_id'])
            if fi.operators.filter(id = self.request.user.profile.active_id).exists() and not fi.locked:
                return True
        except:
            return False

        return False

@method_decorator(login_required, name='dispatch')
class FightView(FightAssistancePermMixin,View):

    def get(self,request,fight_id, stage):

        fight = get_object_or_404(Fight, pk=fight_id)

        all_stages=[]
        act_stage={'is_last':False}
        for s in fight.stage_set.all():
            st = {'active': False}
            if act_stage['is_last']:
                act_stage['is_last']=False

            if s.order == int(stage):
                st['active']=True

                act_stage['is_last'] = True
                act_stage['order'] = s.order

                act_stage['rep'] = s.rep_attendance.team.origin.name
                act_stage['opp'] = s.opp_attendance.team.origin.name
                act_stage['rev'] = s.rev_attendance.team.origin.name
                act_stage['prev'] = _fightpreview(s.fight)[s.order - 1]

                act_stage['form'] = StageForm(s)

            all_stages.append(st)

        if 'form' not in act_stage:
            return redirect('fight:fightjury',fight_id=fight_id)

        return render(request, "fight/fight.html",context={'round':fight.round.order,
                                                           'room':fight.room.name,
                                                           'id':fight_id,
                                                           'all_stages':all_stages,'stage':act_stage,
                                                           'locked':fight.locked})

    def post(self, request, fight_id, stage):

        fight = get_object_or_404(Fight, pk=fight_id)

        all_stages = []
        act_stage = {'is_last': False,'order':int(stage)}
        for s in fight.stage_set.all():
            st = {'active': False}
            if act_stage['is_last']:
                act_stage['is_last'] = False

            if s.order == int(stage):
                st['active'] = True

                act_stage['is_last'] = True

                act_stage['rep'] = s.rep_attendance.team.origin.name
                act_stage['opp'] = s.opp_attendance.team.origin.name
                act_stage['rev'] = s.rev_attendance.team.origin.name
                act_stage['prev'] = _fightpreview(s.fight)[s.order - 1]

                act_stage['form'] = StageForm(s,request.POST)
                act_stage['obj'] = s

            all_stages.append(st)

        if 'form' not in act_stage:
            return redirect('fight:fightjury', fight_id=fight_id)

        form = act_stage['form']
        if form.is_valid():

            if form.has_changed():

                for fn in form.changed_data:

                    if fn == 'rejections':
                        act_stage['obj'].rejections.clear()

                        for p in form.cleaned_data['rejections']:
                            act_stage['obj'].rejections.add(p)

                    elif fn == 'presented':
                        act_stage['obj'].presented=form.cleaned_data['presented']
                        act_stage['obj'].save()

                    elif fn == 'rep':
                        if form.cleaned_data['rep']:
                            act_stage['obj'].rep_attendance.active_person=form.cleaned_data['rep']
                        else:
                            act_stage['obj'].rep_attendance.active_person = None
                        act_stage['obj'].rep_attendance.save()

                    elif fn == 'opp':
                        if form.cleaned_data['opp']:
                            act_stage['obj'].opp_attendance.active_person=form.cleaned_data['opp']
                        else:
                            act_stage['obj'].opp_attendance.active_person = None
                        act_stage['obj'].opp_attendance.save()

                    elif fn == 'rev':
                        if form.cleaned_data['rev']:
                            act_stage['obj'].rev_attendance.active_person=form.cleaned_data['rev']
                        else:
                            act_stage['obj'].rev_attendance.active_person = None
                        act_stage['obj'].rev_attendance.save()

                    elif fn.startswith('grade'):

                        js = form.fields[fn].jurorsession
                        att = form.fields[fn].attendance

                        grade=None
                        try:
                            grade=att.jurorgrade_set.get(juror_session=js)
                        except JurorGrade.DoesNotExist:
                            pass

                        if form.cleaned_data[fn]:
                            if grade:
                                grade.grade = form.cleaned_data[fn]
                                grade.valid = False
                                grade.save()
                            else:
                                JurorGrade.objects.create(juror_session=js, stage_attendee=att, grade=form.cleaned_data[fn], valid=False)
                        else:
                            if grade:
                                grade.delete()
                            else:
                                pass
                            



                pass

            if '_continue' in request.POST:
                return redirect('fight:fight', fight_id=fight_id, stage=int(stage)+1)
            if '_finish' in request.POST:
                return redirect('fight:fightpre', fight_id=fight_id)


        return render(request, "fight/fight.html",
                      context={'round': fight.round.order, 'room': fight.room.name, 'id': fight_id,
                               'all_stages': all_stages, 'stage': act_stage,
                               'locked':fight.locked})


@method_decorator(login_required, name='dispatch')
class FightJuryView(FightAssistancePermMixin,View):

    def get(self,request,fight_id):

        fight = get_object_or_404(Fight, pk=fight_id)

        form = JuryForm(fight)

        return render(request, "fight/jury.html",
                      context={'fight': fight,
                               'form': form,
                               'all_stages': range(fight.stage_set.count())})

    def post(self,request,fight_id):

        fight = get_object_or_404(Fight, pk=fight_id)

        form = JuryForm(fight,request.POST)

        if form.is_valid():

            if form.has_changed():
                if 'jurors' in form.changed_data:
                    now=form.cleaned_data['jurors']
                    old=form.fields['jurors'].obj_initial

                    additions=set(now)-set(old)

                    jrole=JurorRole.objects.get(tournament=fight.round.tournament,type=JurorRole.JUROR)

                    for j in additions:
                        JurorSession.objects.create(juror=j,fight=fight,role=jrole)

                    deletions = set(old)-set(now)

                    for j in deletions:
                        JurorSession.objects.get(juror=j,fight=fight).delete()

                if 'chair' in form.changed_data:

                    try:
                        JurorSession.objects.get(fight=fight,role__type=JurorRole.CHAIR).delete()
                    except:
                        pass

                    if form.cleaned_data['chair']:
                        crole = JurorRole.objects.get(tournament=fight.round.tournament, type=JurorRole.CHAIR)
                        JurorSession.objects.create(juror=form.cleaned_data['chair'], fight=fight, role=crole)


            if '_continue' in request.POST:
                return redirect('fight:fight', fight_id=fight_id, stage=1)

        return render(request, "fight/jury.html",
                      context={'fight': fight,
                               'form': form,
                               'all_stages': range(fight.stage_set.count())})

@method_decorator(login_required, name='dispatch')
class FightPreView(FightAssistancePermMixin,View):

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

        for stage in fight.stage_set.all():

            prev = _fightpreview(fight)[stage.order - 1]

            team = {}
            team['rep'] = stage.rep_attendance.team.origin.name
            team['opp'] = stage.opp_attendance.team.origin.name
            team['rev'] = stage.rev_attendance.team.origin.name

            person = {}
            person['rep'] = ""
            person['opp'] = ""
            person['rev'] = ""
            if stage.reporter:
                person['rep'] = stage.reporter
            else:
                errors.append("Stage %d missing reporter name" % stage.order)
            if stage.opponent:
                person['opp'] = stage.opponent
            else:
                errors.append("Stage %d missing opponent name" % stage.order)
            if stage.reviewer:
                person['rev'] = stage.reviewer
            else:
                errors.append("Stage %d missing reviewer name" % stage.order)

            presented = ""
            if stage.presented:
                presented = stage.presented.number
                if presented not in prev['free']:
                    warnings.append("Problem presented in stage %d not in preview"%stage.order)
                if presented in stage.rejections.all().values_list('number',flat=True):
                    errors.append("Stage %d presented problem is in rejected list" % stage.order)
            else:
                errors.append("Stage %d has no presented problem" % stage.order)

            grades_j = []
            for jurorsess in fight.jurorsession_set(manager="voting").select_related('juror').all():
                juror = jurorsess.juror
                grade_j = {'id': juror.id, 'name': juror.attendee}

                try:
                    grade_j['rep'] = int(JurorGrade.objects.get(stage_attendee=stage.rep_attendance,
                                                                juror_session__juror=juror).grade)
                except:
                    errors.append("Stage %d missing reporter grade from %s" % (stage.order, juror.attendee))
                try:
                    grade_j['opp'] = int(JurorGrade.objects.get(stage_attendee=stage.opp_attendance,
                                                                juror_session__juror=juror).grade)
                except:
                    errors.append("Stage %d missing opponent grade from %s" % (stage.order, juror.attendee))
                try:
                    grade_j['rev'] = int(JurorGrade.objects.get(stage_attendee=stage.rev_attendance,
                                                                juror_session__juror=juror).grade)
                except:
                    errors.append("Stage %d missing reviewer grade from %s" % (stage.order, juror.attendee))

                grades_j.append(grade_j)

            stage_info.append({'teams': team,
                               'persons': person,
                               'presented': presented,
                               'rejections': stage.rejections.all().values_list('number', flat=True),
                               'jurors': grades_j})

        return    {'fight': fight,
                   'chair': chair,
                   'jurors': jurors,
                   'stages': stage_info,
                   'errors': errors,
                   'warnings': warnings,
                   'all_stages': range(fight.stage_set.count())}

    def get(self,request,fight_id):

        fight = get_object_or_404(Fight, pk=fight_id)

        validator = request.user.has_perm("jury.validate_grades")

        context=self._fight_check(fight)
        context.update({"validator":validator})

        return render(request, "fight/preview.html",
                      context=context)

    @method_decorator(transaction.atomic)
    def post(self,request,fight_id):

        fight = get_object_or_404(Fight, pk=fight_id)

        chk=self._fight_check(fight)

        if len(chk['errors']) == 0 or True:
            if "_save" in request.POST:
                fight.locked=True
                fight.save()
            elif '_validate' in request.POST:
                if request.user.has_perm("jury.validate_grades") and fight.locked:
                    for grade in JurorGrade.objects.filter(stage_attendee__stage__fight=fight):
                        grade.valid = True
                        grade.save()
                    #clear all caches
                    caches['results'].delete("preview-%s"%fight.pk)
                    caches['results'].delete("points-%s"%fight.pk)
                    caches['results'].delete("grades-%s"%fight.pk)
                    messages.add_message(request, messages.SUCCESS, "All grades of fight %s validated"%fight)
                else:
                    messages.add_message(request, messages.ERROR, "No Permission or fight not locked")

                return redirect("fight:validate")


        return redirect("fight:plan")

@method_decorator(login_required, name='dispatch')
class ManageFightsView(View):

    @method_decorator(permission_required('plan.view_fight_operator'))
    def get(self,request):

        form = ManageForm(request.user.profile.tournament)

        return render(request, "fight/manage.html", context={"form":form})

    @method_decorator(permission_required('plan.change_fight_operator'))
    def post(self, request):
        form = ManageForm(request.user.profile.tournament, request.POST)

        if form.is_valid():

            if form.has_changed():
                changes = []
                for cf in form.changed_data:
                    if type(form.fields[cf]) == forms.ModelMultipleChoiceField:
                        changes.append((str(form.fields[cf].fight),form.fields[cf].old_attendees,", ".join([a.full_name for a in form.cleaned_data[cf]])))

                        form.fields[cf].fight.operators.set(form.cleaned_data[cf])
                        form.fields[cf].fight.save()

                    elif type(form.fields[cf]) == forms.BooleanField:
                        changes.append((str(form.fields[cf].fight),'locked' if form.fields[cf].initial else 'unlocked','locked' if form.cleaned_data[cf] else 'unlocked'))

                        form.fields[cf].fight.locked = form.cleaned_data[cf]
                        form.fields[cf].fight.save()

                cgs=format_html_join(
                    '', "<li>{} : {} <i class='fa fa-angle-right'></i> {}</li>",
                    (c for c in changes)
                )
                msg = [Message(subject=mark_safe("Saved assignments with changes: <ul>%s</ul>"%(cgs,)), level_tag='success')]
            else:
                msg = [Message(subject="No changes made", level_tag='warning')]
        else:
            print(form.errors)
            msg = [Message(subject="Form contains errors", level_tag='error')]


        return render(request, "fight/manage.html", context={"form":form,'messages':msg})


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required("jury.publish_fights"), name='dispatch')
class PublishView(View):
    def get(self, request):
        form = PublishForm(request.user.profile.tournament)

        return render(request, "fight/publish.html", context={'form': form})

    def post(self,request):

        trn=request.user.profile.tournament
        form = PublishForm(trn, request.POST)

        if form.is_valid():
            if form.has_changed():
                changes=[]
                for cf in form.changed_data:
                    if cf.startswith("grades-"):
                        changes.append(("published grades" if form.cleaned_data[cf] else "recalled grades", form.fields[cf].fight))
                        form.fields[cf].fight.publish_grades = form.cleaned_data[cf]
                        form.fields[cf].fight.save()
                    if cf.startswith("partial-"):
                        changes.append(("set partial grades file" if form.cleaned_data[cf] else "unlinked partial grades", form.fields[cf].fight))
                        form.fields[cf].fight.pdf_partial_grades = form.cleaned_data[cf]
                        form.fields[cf].fight.save()
                    if cf.startswith("preview-"):
                        changes.append(("published preview" if form.cleaned_data[cf] else "recalled preview", form.fields[cf].fight))
                        form.fields[cf].fight.publish_preview = form.cleaned_data[cf]
                        form.fields[cf].fight.save()
                    if cf.startswith("rank-"):
                        changes.append(("published ranking" if form.cleaned_data[cf] else "recalled ranking", form.fields[cf].round))
                        form.fields[cf].round.publish_ranking = form.cleaned_data[cf]
                        form.fields[cf].round.save()
                    if cf.startswith("sched-"):
                        changes.append(("published schedule" if form.cleaned_data[cf] else "recalled schedule", form.fields[cf].round))
                        form.fields[cf].round.publish_schedule = form.cleaned_data[cf]
                        form.fields[cf].round.save()
                    if cf == "protection":
                        trn.results_access=form.cleaned_data[cf]
                        trn.save()
                        messages.add_message(request, messages.SUCCESS,
                                             "Set access control to %s"%trn.get_results_access_display())

                    if cf=="password":
                        pw = make_password(form.cleaned_data[cf])
                        trn.results_password = pw
                        trn.save()
                        purge_sessions(trn)
                        messages.add_message(request, messages.SUCCESS,
                                             "Password changed, all sessions are closed")

                cgs = format_html_join(
                    '', "<li>{} for {}</li>",
                    (c for c in changes)
                )
                if len(changes) > 0:
                    messages.add_message(request,messages.SUCCESS,mark_safe("Saved assignments with changes: <ul>%s</ul>" % cgs))
            else:
                messages.add_message(request,messages.WARNING,"No changes made")
        else:
            messages.add_message(request,messages.ERROR, "Form contains errors")

        return render(request, "fight/publish.html", context={"form":form})

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required("jury.publish_fights"), name='dispatch')
class PdfPreviewView(ObjectDownloadView):

    attachment = False

    mimetype = "application/pdf"

    def get_object(self, queryset=None):
        try:
            obj = Fight.objects.get(round__tournament=self.request.user.profile.tournament, id=self.kwargs['fight_id']).pdf_preview
            if not obj.status in [Pdf.SUCCESS, Pdf.UPLOAD]:
                raise Pdf.DoesNotExist("File not yet available")
            return obj.file
        except:
            raise Pdf.DoesNotExist("File does not exist")

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required("jury.publish_fights"), name='dispatch')
class PdfResultView(ObjectDownloadView):

    attachment = False

    mimetype = "application/pdf"

    def get_object(self, queryset=None):
        try:
            obj = Fight.objects.get(round__tournament=self.request.user.profile.tournament, id=self.kwargs['fight_id']).pdf_result
            if not obj.status in [Pdf.SUCCESS, Pdf.UPLOAD]:
                raise Pdf.DoesNotExist("File not yet available")
            return obj.file
        except:
            raise Pdf.DoesNotExist("File does not exist")

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required("jury.publish_fights"), name='dispatch')
class PdfRankingView(ObjectDownloadView):

    attachment = False

    mimetype = "application/pdf"

    def get_object(self, queryset=None):
        try:
            obj = Round.objects.get(tournament=self.request.user.profile.tournament, order=self.kwargs['round_nr']).pdf_ranking
            if not obj.status in [Pdf.SUCCESS, Pdf.UPLOAD]:
                raise Pdf.DoesNotExist("File not yet available")
            return obj.file
        except:
            raise Pdf.DoesNotExist("File does not exist")


@login_required
@permission_required('jury.publish_fights')
def genpdfpreview(request, fight_id):

    if request.method == "POST" or True:

        trn = request.user.profile.tournament
        fight = get_object_or_404(Fight, pk=fight_id, round__tournament=trn)

        context = context_generator.preview(fight)

        fileprefix="preview-round-%d-room-%s-v"%(fight.round.order, fight.room.name)

        pdf = Pdf.objects.create(name="%s%d"%(fileprefix,_get_next_pdfname(trn,fileprefix)), tournament=trn)

        res = render_to_pdf.delay(trn.default_templates.get(type=Template.PREVIEW).id, pdf.id, context=context)

        pdf.task_id = res.id
        pdf.save()

        pdf.tags.add(PdfTag.objects.get(tournament=trn, type=Template.PREVIEW))

        fight.pdf_preview = pdf
        fight.save()

    return redirect("fight:publish")

@login_required
@permission_required('jury.publish_fights')
def genpdfresult(request, fight_id):

    if request.method == "POST" or True:

        trn = request.user.profile.tournament
        fight = get_object_or_404(Fight, pk=fight_id, round__tournament=trn)

        context = context_generator.result(fight)

        fileprefix="result-round-%d-room-%s-v"%(fight.round.order, fight.room.name)

        pdf = Pdf.objects.create(name="%s%d"%(fileprefix,_get_next_pdfname(trn,fileprefix)), tournament=trn)

        res = render_to_pdf.delay(trn.default_templates.get(type=Template.RESULTS).id, pdf.id, context=context)

        pdf.task_id = res.id
        pdf.save()

        pdf.tags.add(PdfTag.objects.get(tournament=trn, type=Template.RESULTS))

        fight.pdf_result = pdf
        fight.save()

    return redirect("fight:publish")

@login_required
@permission_required('jury.publish_fights')
def genpdfrank(request, round_nr):

    if request.method == "POST" or True:

        trn = request.user.profile.tournament
        round = get_object_or_404(Round, order=round_nr, tournament=trn)

        context = context_generator.ranking(round)

        fileprefix="ranking-round-%d-v"%(round.order)

        pdf = Pdf.objects.create(name="%s%d"%(fileprefix,_get_next_pdfname(trn,fileprefix)), tournament=trn)

        res = render_to_pdf.delay(trn.default_templates.get(type=Template.RANKING).id, pdf.id, context=context)

        pdf.task_id = res.id
        pdf.save()

        pdf.tags.add(PdfTag.objects.get(tournament=trn, type=Template.RANKING))

        round.pdf_ranking = pdf
        round.save()

    return redirect("fight:publish")

@login_required
@permission_required('jury.clock')
def fightclock(request, fight_id, stage):

    return render(request, "fight/clock.xml", context={"id":fight_id,"phases":request.user.profile.tournament.phase_set.all()}, content_type="image/svg+xml")

@login_required
@permission_required('jury.clocks')
def clocks(request, round_nr):
    phases = request.user.profile.tournament.phase_set.all()
    duration = sum(phases.values_list("duration",flat=True))
    fights = request.user.profile.tournament.round_set.get(order=round_nr).fight_set.all()
    return render(request, "fight/clocks.html", context={"phases":phases,"total_duration":duration,"fights":fights})
