from django import forms
from django.db import IntegrityError
from django.utils.html import format_html_join
from django_select2.forms import Select2MultipleWidget, Select2Widget

from apps.account.models import Attendee
from apps.plan.models import FightRole
from apps.printer.models import Pdf, PdfTag
from apps.result.utils import _fightpreview
from apps.team.models import TeamRole
from apps.tournament.models import Problem, Tournament

from .utils import fight_grades_valid


class StageForm(forms.Form):

    def __init__(self,stage, *args, **kwargs):
        super(StageForm, self).__init__(*args, **kwargs)



        prev=_fightpreview(stage.fight)[stage.order-1]
        if prev['pk'] != stage.pk:
            raise IntegrityError("Stage number integrity Error")

        self.fields['rejections'] = forms.ModelMultipleChoiceField(queryset=Problem.objects.filter(tournament=stage.fight.round.tournament), required=False, widget=Select2MultipleWidget) # , number__in=prev['free']
        self.fields['presented'] = forms.ModelChoiceField(queryset=Problem.objects.filter(tournament=stage.fight.round.tournament),widget=Select2Widget ,required=False ) #, number__in=prev['free']
        if stage.presented:
            self.fields['presented'].initial = stage.presented_id

        self.fields['rejections'].initial = list(stage.rejections.all().values_list('pk',flat=True))

        self.fields['rep']=forms.ModelChoiceField(queryset=stage.rep_attendance.team.teammember_set(manager="students").prefetch_related('attendee__active_user__user').all(),widget=Select2Widget,required=False)
        if stage.reporter:
            self.fields['rep'].initial = stage.rep_attendance.active_person
        self.fields['opp']=forms.ModelChoiceField(queryset=stage.opp_attendance.team.teammember_set(manager="students").prefetch_related('attendee__active_user__user').all(),widget=Select2Widget,required=False)
        if stage.opponent:
            self.fields['opp'].initial = stage.opp_attendance.active_person
        self.fields['rev']=forms.ModelChoiceField(queryset=stage.rev_attendance.team.teammember_set(manager="students").prefetch_related('attendee__active_user__user').all(),widget=Select2Widget,required=False)
        if stage.reviewer:
            self.fields['rev'].initial = stage.rev_attendance.active_person

        self.grades=[]
        index=30
        for js in stage.fight.jurorsession_set(manager="voting").all():
            j={'name':js.juror.attendee.full_name,'pk':js.pk}

            f=forms.IntegerField(min_value=1,max_value=10,required=False)
            self.fields['grade-%d-rep'%(js.pk, )]=f
            f.widget.attrs['tabindex']=index
            f.jurorsession=js
            f.attendance=stage.rep_attendance
            try:
                f.initial_obj = stage.rep_attendance.jurorgrade_set.get(juror_session=js)
                f.initial = int(f.initial_obj.grade)
            except:
                pass

            f = forms.IntegerField(min_value=1, max_value=10,required=False)
            self.fields['grade-%d-opp' % (js.pk,)] = f
            f.widget.attrs['tabindex'] = index+50
            f.jurorsession = js
            f.attendance = stage.opp_attendance
            try:
                f.initial_obj = stage.opp_attendance.jurorgrade_set.get(juror_session=js)
                f.initial = int(f.initial_obj.grade)
            except:
                pass

            f = forms.IntegerField(min_value=1, max_value=10,required=False)
            self.fields['grade-%d-rev' % (js.pk,)] = f
            f.widget.attrs['tabindex'] = index+100
            f.jurorsession = js
            f.attendance = stage.rev_attendance
            try:
                f.initial_obj = stage.rev_attendance.jurorgrade_set.get(juror_session=js)
                f.initial = int(f.initial_obj.grade)
            except:
                pass

            index+=1
            self.grades.append(j)


    def as_grades_table(self):

        return format_html_join(
                '', "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>",
                ((j['name'],
                        self.__getitem__('grade-%d-rep' % (j['pk'])),
                        self.__getitem__('grade-%d-opp' % (j['pk'])),
                        self.__getitem__('grade-%d-rev' % (j['pk'])),) for j in self.grades)
            )

class ManageForm(forms.Form):

    def __init__(self,tournament, *args, **kwargs):
        super(ManageForm, self).__init__(*args, **kwargs)

        self.rs=[]
        for round in tournament.round_set(manager='selectives').filter():
            r=[]
            for fight in round.fight_set.select_related('room').all():
                f = forms.BooleanField(label=fight.room.name, required=False)
                f.initial = fight.locked
                ass = forms.ModelMultipleChoiceField(queryset=tournament.attendee_set(manager='assistants'), widget=Select2MultipleWidget, required=False)
                ass.fight = fight
                f.fight = fight
                ass.old_attendees = None
                if fight.operators.count() > 0:
                    ass.initial=fight.operators.all().values_list("id",flat=True)
                    ass.old_attendees = ", ".join([a.full_name for a in fight.operators.all()])
                r.append('%d-%d'%(round.order,fight.pk))
                self.fields['locked-%d-%d'%(round.order,fight.pk)]=f
                self.fields['op-%d-%d'%(round.order,fight.pk)]=ass
            self.rs.append(r)

    def rounds(self):
        for round in self.rs:
            yield [ (self.__getitem__("locked-%s"%(name,)),self.__getitem__("op-%s"%(name,))) for name in round ]


class PublishForm(forms.Form):

    def __init__(self,tournament, *args, **kwargs):
        super(PublishForm, self).__init__(*args, **kwargs)

        self.rs=[]
        self.valid={}
        self.pdf_preview={}
        self.pdf_result={}
        self.pdf_rank={}
        self.fight_id={}

        partial_tag = PdfTag.objects.filter(tournament=tournament, name="Partials").first()

        for round in tournament.round_set.filter():
            rank = forms.BooleanField(required=False)
            rank.initial = round.publish_ranking
            rank.round = round
            self.fields["rank-%d"%round.order] = rank

            sched = forms.BooleanField(required=False)
            sched.initial = round.publish_schedule
            sched.round = round
            self.fields["sched-%d" % round.order] = sched


            r=[]
            for fight in round.fight_set.select_related('room').all():
                fg = forms.BooleanField(label=fight.room.name, required=False)
                fg.initial = fight.publish_grades
                fg.fight = fight

                fp = forms.BooleanField(label=fight.room.name, required=False)
                fp.initial = fight.publish_preview
                fp.fight = fight

                fppart = forms.ModelChoiceField(Pdf.objects.filter(tournament=tournament, tags__in=[partial_tag]),widget=Select2Widget,required=False)
                fppart.initial = fight.pdf_partial_grades
                fppart.fight = fight

                r.append('%d-%d'%(round.order,fight.pk))
                self.fields['grades-%d-%d'%(round.order,fight.pk)]=fg
                self.fields['preview-%d-%d'%(round.order,fight.pk)]=fp
                self.fields['partial-%d-%d'%(round.order,fight.pk)]=fppart

                self.valid['%d-%d' % (round.order, fight.pk)] = fight_grades_valid(fight)
                self.pdf_preview['%d-%d' % (round.order, fight.pk)] = fight.pdf_preview_id
                self.pdf_result['%d-%d' % (round.order, fight.pk)] = fight.pdf_result_id
                self.pdf_rank['%d-%d' % (round.order, fight.pk)] = round.pdf_ranking
                self.fight_id['%d-%d' % (round.order, fight.pk)] = fight.pk

            self.rs.append(r)

        self.fields['protection'] = forms.ChoiceField(choices=Tournament.RESULTS_ACCESS_TYPE, initial=tournament.results_access)
        self.fields['password'] = forms.CharField(widget=forms.PasswordInput, required=False)

    def rounds(self):
        for order, round in enumerate(self.rs):
            yield [ {"grade_check":self.__getitem__("grades-%s"%(name,)),
                     "preview_check":self.__getitem__("preview-%s"%(name,)),
                     "rank_check":self.__getitem__("rank-%d"%(order+1,)),
                     "sched_check": self.__getitem__("sched-%d" % (order + 1,)),
                     "partial_file":self.__getitem__("partial-%s"%(name,)),
                     "valid":self.valid[name],
                     "pdf_preview":self.pdf_preview[name],
                     "pdf_result":self.pdf_result[name],
                     "pdf_rank":self.pdf_rank[name],
                     "fight_id":self.fight_id[name]} for name in round ]

    def clean(self):
        cleaned_data = super(PublishForm, self).clean()

        rp=[]
        for order, round in enumerate(self.rs):
            pubed = cleaned_data.get("rank-%d"%(order+1))
            if pubed and not all(rp):
                raise forms.ValidationError(
                    "You have to publish rankings consecutively."
                )
            rp.append(pubed)

        sp = []
        for order, round in enumerate(self.rs):
            pubed = cleaned_data.get("sched-%d" % (order + 1))
            if pubed and not all(sp):
                raise forms.ValidationError("You have to publish schedule rounds consecutively.")
            sp.append(pubed)
