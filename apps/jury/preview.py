from django import forms
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.utils.decorators import method_decorator
from django.utils.text import capfirst
from django_select2.forms import Select2MultipleWidget, Select2Widget
from formtools.preview import FormPreview

from apps.account.models import ParticipationRole
from apps.dashboard.messages import Message
from apps.dashboard.preview import ListPreview
from apps.plan.models import Round
from apps.plan.preview import ModelDeleteListField
from apps.tournament.models import Origin

from .models import Juror, JurorRole, JurorSession, PossibleJuror
from .utils import assignments_light, async_plan_from_db, check_conflict_origin, plan_cost, plan_from_db

#@method_decorator(permission_required('plan.view_all_persons'), name='__call__')

class PossibleJurorPreview(ListPreview):

    form_template = "jury/possiblejurors.html"
    success_url = "jury:possiblejurors"

    def get_filters(self, request):
        trn = request.user.profile.tournament

        filters = [
            {'name': "Experience", "elements": [self.DirectSelector(x[0], x[1]) for x in Juror.EXPERIENCES],
                    "filter": "experience__in"},
        ]

        return filters

    def get_prefetch(self):
        return []

    def form_members(self):
        experience = forms.ChoiceField(choices=Juror.EXPERIENCES, required=False,
                                          widget=Select2Widget())

        return {"experience":experience}

    def get_queryset(self):
        trn = self.request.user.profile.tournament
        return PossibleJuror.objects.filter(tournament=trn)

    def preview_actions(self, request, form, context):

        if "_role" in request.POST:

            context['action'] = "_role"

            self.preview_template = "jury/possiblejurors_preview.html"

            persons = []

            jurorrole = request.user.profile.tournament.participationrole_set.filter(type=ParticipationRole.JUROR)

            for pj in form.cleaned_data['obj_list']:

                person = {"full_name": "%s %s"%(pj.person.user.first_name,pj.person.user.last_name), 'obj':pj, "attending":False, "new_roles":[],"experience":pj.experience}

                if pj.id in context["attendees"]:
                    person["attending"]=True
                    old_roles = context["attendees"][pj.id]
                    person["roles"] = old_roles
                    if not old_roles.filter(type=ParticipationRole.JUROR).exists():
                        person["new_roles"] = jurorrole

                persons.append(person)

            context['persons']=persons

        elif "_experience" in request.POST:

            context['action'] = "_experience"

            self.preview_template = "jury/possiblejurors_preview.html"

            persons = []

            try:
                level = int(form.cleaned_data["experience"])
            except:
                return

            for pj in form.cleaned_data['obj_list']:

                person = {"full_name": "%s %s"%(pj.person.user.first_name,pj.person.user.last_name), 'obj':pj, "attending":True, "new_roles":[], "experience":pj.experience}

                if pj.id in context["attendees"]:
                    person["attending"]=True
                    old_roles = context["attendees"][pj.id]
                    person["roles"] = old_roles


                if pj.experience != level:
                    person["new_experience"] = level


                persons.append(person)

            context['persons']=persons

        elif "_mailto" in request.POST:

            context['action'] = "_mailto"

            self.preview_template = "jury/possiblejurors_mailto_preview.html"

            persons = []

            for pj in form.cleaned_data['obj_list']:

                person = {"full_name": "%s %s"%(pj.person.user.first_name,pj.person.user.last_name), 'obj':pj, "email":pj.person.user.email}
                persons.append(person)

            context['persons']=persons

    def get_context(self, request, form):
        context = super().get_context(request, form)

        attendees = {}
        ejs = {}
        for pJ in self.get_queryset():
            try:
                attendees[pJ.id] = pJ.person.attendee_set.get(tournament=self.request.user.profile.tournament).roles.all()
            except:
                pass

            ejs[pJ.id] = pJ.person.application_set.filter(tournament=self.request.user.profile.tournament, participation_role__type=ParticipationRole.JUROR).exists()

        context["attendees"] = attendees
        context["ejs"] = ejs
        print(ejs)
        return context

    def done_actions(self, request, cleaned_data):

        if request.POST['action'] == '_role':
            trn = request.user.profile.tournament

            jurorrole = request.user.profile.tournament.participationrole_set.filter(type=ParticipationRole.JUROR)

            for pj in cleaned_data['obj_list']:
                if pj.person.attendee_set.filter(tournament=trn).exists():
                    pj.person.attendee_set.get(tournament=trn).roles.add(*jurorrole)

        elif request.POST['action'] == '_experience':
            trn = request.user.profile.tournament

            level = int(cleaned_data["experience"])

            for pj in cleaned_data['obj_list']:
                pj.experience = level
                pj.save()

        elif request.POST['action'] == '_mailto':
            pass


@method_decorator(login_required, name='__call__')
class JurorsPreview(FormPreview):

    form_template = "jury/persons.html"
    preview_template = "dashboard/previewObjsDelete.html"

    class DirectSelector(object):

        def __init__(self, id, name):
            self.id = id
            self.name = name

        def __str__(self):
            return "%s" % self.name


    def parse_params(self, request):
        trn=request.user.profile.tournament

        self.filters = [
            {"name": "Local",
             "filter": "local__in",
             "elements": [self.DirectSelector(1,"Jurors")]},
            {'name': "Possible Chair",
             "elements": [self.DirectSelector(1, "Chairs")],
             "filter": "possible_chair__in"},
            {'name': "Experience",
             "elements": [self.DirectSelector(x[0], x[1]) for x in Juror.EXPERIENCES],
             "filter": "experience__in"},
            {'name': "Availability",
             "elements": trn.round_set.all(),
             "filter": "availability__in"},
            {"name": "Conflicting",
             "filter": "conflicting__in",
             "elements": trn.origin_set.all().order_by("name")}
        ]

        self._filters={}
        self._excludes={}

        for fname in [x['filter'] for x in self.filters]:
            try:
                inarg = request.GET.getlist("in_%s"%fname, None)
                if len(inarg) > 0:
                    self._filters[fname] = list(map(int,inarg))
                exarg = request.GET.getlist("ex_%s"%fname, None)
                if len(exarg) > 0:
                    self._excludes[fname] = list(map(int,exarg))
            except:
                pass

        ex_query = Q()

        for k in self._excludes:
            ex_query |= Q(**{k:self._excludes[k]})

        jurors = ModelDeleteListField(queryset=Juror.objects.filter(attendee__tournament=trn,
                                                                    **self._filters)
                                        .exclude(ex_query).distinct()
                                      .prefetch_related('availability',
                                                        "attendee__active_user__user",
                                                        "conflicting"))

        conflicting = forms.ModelMultipleChoiceField(queryset=Origin.objects.filter(tournament=trn),
                                                     widget=Select2MultipleWidget(), required=False)

        local = forms.BooleanField(required=False)
        local_set = forms.BooleanField(required=False)

        possible_chair = forms.BooleanField(required=False)
        possible_chair_set = forms.BooleanField(required=False)

        experience_set = forms.BooleanField(required=False)
        experience = forms.ChoiceField(choices=Juror.EXPERIENCES, required=False)

        round_forms=[]
        extra_fields={}
        for r in Round.objects.filter(tournament=trn):
            rf = forms.BooleanField(required=False)
            rf_set = forms.BooleanField(required=False)
            extra_fields["round_%d"%r.order] = rf
            extra_fields["round_%d_set"%r.order] = rf_set

            round_forms.append(r)

        self.round_forms=round_forms

        def get_round_forms(self):
            for r in self.round_forms:
                yield (self.__getitem__("round_%d"%r.order),self.__getitem__("round_%d_set"%r.order))


        membervars={'jurors':jurors,'conflicting':conflicting,
                   'local':local, "local_set":local_set,
                   'possible_chair':possible_chair, "possible_chair_set":possible_chair_set,
                   'experience': experience, 'experience_set':experience_set,
                   "round_forms":round_forms, 'get_round_forms':get_round_forms}
        membervars.update(extra_fields)
        self.form = type("JurorsForm", (forms.Form,), membervars )

    def get_context(self, request, form):
        trn = request.user.profile.tournament

        filters = []

        for fil in self.filters:
            f = {'name': fil['name'],
                 "elements": fil['elements'],
                 "link_name": fil['filter']}

            #f['active'] = self.filter.get(f['link_name'], None)

            filter_rest = "&".join(["&".join(["in_%s=%s"%(f,g) for g in self._filters[f]])
                                    for f in self._filters if f != fil['filter']])

            exclude_rest = "&".join(["&".join(["ex_%s=%s" % (f, g) for g in self._excludes[f]])
                                    for f in self._excludes if f != fil['filter']])

            f['link_rest'] = "&".join([filter_rest,exclude_rest])

            f["in_actives"] = self._filters.get(fil['filter'],[])
            f["ex_actives"] = self._excludes.get(fil['filter'],[])

            filters.append(f)

        return {
                'filters': filters,
                'form': form,
                'stage_field': self.unused_name('stage'),
                'state': self.state,
                'rounds': Round.objects.filter(tournament=trn),
               }

    def process_preview(self, request, form, context):

        trn = request.user.profile.tournament

        if "_delete" in request.POST:
            context['action'] = "_delete"

            self.preview_template = "dashboard/previewObjsDelete.html"

            def format_callback(obj):
                return '%s: %s' % (capfirst(obj._meta.verbose_name), obj)


            ps = form.cleaned_data['jurors']
            collector = NestedObjects(using='default')  # or specific database
            collector.collect(ps)
            to_delete = collector.nested(format_callback)

            context['objs']=to_delete

        else:

            self.preview_template = "jury/jurorAssignPreview.html"

            jurors = []

            for jur in form.cleaned_data['jurors'].prefetch_related(
                                                        'attendee__active_user__user',
                                                        ):
                person = {"full_name": jur.attendee.full_name,
                          'conflicting': list(map(lambda x: x['name'], jur.conflicting.values("name"))),
                          'local': bool(jur.local),
                          'possible_chair': bool(jur.possible_chair),
                          'experience': jur.experience,
                          'availability': list(map(lambda x:x[0],jur.availability.all().values_list('order'))),
                          'availability_changed': []}

                if "_add_conflicting" in request.POST:
                    context['action'] = "_add_conflicting"
                    news = form.cleaned_data['conflicting']
                    person['conflicting_new']=[]
                    for new in news:
                        if new.name not in person['conflicting']:
                            person['conflicting_new'].append(new)

                if "_del_conflicting" in request.POST:
                    context['action'] = "_del_conflicting"
                    deles=form.cleaned_data['conflicting']
                    person['conflicting_del'] = []
                    person['conflicting_del_na'] = []
                    for dele in deles:
                        if dele.name in person['conflicting']:
                            person['conflicting'].remove(dele.name)
                            person['conflicting_del'].append(dele.name)
                        else:
                            person['conflicting_del_na'].append(dele.name)

                if "_set_parameters" in request.POST:
                    context['action'] = "_set_parameters"
                    ind_set = form.cleaned_data['local_set']
                    ind = form.cleaned_data['local']
                    if ind_set:
                        if person['local'] != ind:
                            person['local'] = ind
                            person['local_changed']=True

                    pc_set = form.cleaned_data['possible_chair_set']
                    pc = form.cleaned_data['possible_chair']
                    if pc_set:
                        if person['possible_chair'] != pc:
                            person['possible_chair'] = pc
                            person['possible_chair_changed'] = True

                    ex_set = form.cleaned_data['experience_set']
                    ex = form.cleaned_data['experience']
                    if ex_set:
                        if person['experience'] != ex:
                            person['experience'] = ex
                            person['experience_changed'] = True

                    for r in form.round_forms:
                        r_set=form.cleaned_data["round_%d_set"%r.order]
                        r_val=form.cleaned_data["round_%d"%r.order]
                        if r_set:
                            if r_val:
                                if r.order not in person['availability']:
                                    person['availability'].append(r.order)
                                    person['availability_changed'].append(r.order)
                            else:
                                if r.order in person['availability']:
                                    person['availability'].remove(r.order)
                                    person['availability_changed'].append(r.order)



                jurors.append(person)

            context['jurors']=jurors

    @method_decorator(permission_required('jury.change_juror'))
    def done(self, request, cleaned_data):

        ps = cleaned_data['jurors']

        if 'action' not in request.POST:
            ps.delete()

        elif request.POST['action'] == '_add_conflicting':
            news = cleaned_data['conflicting']
            for att in ps:
                att.conflicting.add(*news)
        elif request.POST['action'] == '_del_conflicting':
            news = cleaned_data['conflicting']
            for att in ps:
                att.conflicting.remove(*news)


        elif request.POST['action'] == '_set_parameters':
            ind_set = cleaned_data['local_set']
            ind = cleaned_data['local']
            if ind_set:
                for j in ps:
                    j.local = ind
                    j.save()
            pc_set = cleaned_data['possible_chair_set']
            pc = cleaned_data['possible_chair']
            if pc_set:
                for j in ps:
                    j.possible_chair = pc
                    j.save()
            ex_set = cleaned_data['experience_set']
            ex = cleaned_data['experience']
            if ex_set:
                for j in ps:
                    j.experience = ex
                    j.save()
            for r in self.round_forms:
                r_set = cleaned_data["round_%d_set" % r.order]
                r_val = cleaned_data["round_%d" % r.order]
                if r_set:
                    if r_val:
                        for j in ps:
                            j.availability.add(r)
                    else:
                        for j in ps:
                            j.availability.remove(r)


        return redirect(reverse('jury:jurors')+"?"+request.GET.urlencode())

@method_decorator(login_required, name='__call__')
class RoundPreview(FormPreview):

    form_template = "jury/round.html"
    preview_template = "jury/roundPreview.html"

    def parse_params(self, request, round):
        trn=request.user.profile.tournament

        self.initials={}
        self.initialnv = {}

        self.round = get_object_or_404(Round, order=round, tournament=trn)

        fields = {}
        for fight in self.round.fight_set.all():
            cfield = forms.ModelChoiceField(queryset=Juror.objects.filter(availability=self.round).prefetch_related('attendee__active_user__user'),
                                            required=False)
            try:
                cfield.initial = fight.jurorsession_set.get(role__type=JurorRole.CHAIR).juror_id
            except:
                pass
            fields['fight_%s_chair' % fight.pk] = cfield

            jfield = forms.ModelMultipleChoiceField(
                queryset=Juror.objects.filter(availability=self.round).prefetch_related('attendee__active_user__user'),
                required=False)
            self.initials['fight_%s_juror' % fight.pk] = []
            try:
                jurors = fight.jurorsession_set.filter(role__type=JurorRole.JUROR)
                jfield.initial = list(jurors.values_list('juror_id',flat=True))
                self.initials['fight_%s_juror' % fight.pk] = list(map(lambda x: x.juror, jurors))
            except:
                pass

            fields['fight_%s_juror' % fight.pk] = jfield

            nvfield = forms.ModelMultipleChoiceField(
                queryset=Juror.objects.filter(availability=self.round).prefetch_related('attendee__active_user__user'),
                required=False)
            self.initialnv['fight_%s_nonvoting' % fight.pk] = []
            try:
                jurors = fight.jurorsession_set.filter(role__type=JurorRole.NONVOTING)
                nvfield.initial = list(jurors.values_list('juror_id', flat=True))
                self.initialnv['fight_%s_nonvoting' % fight.pk] = list(map(lambda x: x.juror, jurors))
            except:
                pass

            fields['fight_%s_nonvoting' % fight.pk] = nvfield

        self.form = type("RoundForm", (forms.Form,), fields)

    def get_context(self, request, form):

        trn = request.user.profile.tournament

        freeJ = Juror.objects.filter(attendee__tournament=trn, availability=self.round)\
            .exclude(fights__in=self.round.fight_set.all())\
            .prefetch_related("attendee__active_user__user")



        return {
                'round': self.round,
                'free_jurors': freeJ,
                'form': form,
                'stage_field': self.unused_name('stage'),
                'state': self.state,
               }

    def process_preview(self, request, form, context):

        plan = plan_from_db(self.round.tournament)

        aplan = async_plan_from_db(self.round.tournament)

        before_cost = plan_cost(aplan, Juror.objects.filter(attendee__tournament= self.round.tournament))

        grade_del=[]
        round = []
        conflicts = []

        plan_ro = []
        round_fights = {"fights": []}

        for fight in self.round.fight_set.all():

            f = {"room":fight.room.name}

            plan_fi = {'jurors':[]}
            fight_data = {"fight": fight, 'jurors': [], "nonvoting": []}

            if form.fields["fight_%s_chair" % fight.pk].initial:
                if (not form.cleaned_data["fight_%s_chair" % fight.pk]) or (form.cleaned_data["fight_%s_chair" % fight.pk].id != form.fields["fight_%s_chair" % fight.pk].initial):
                    old_chair_id = form.fields["fight_%s_chair" % fight.pk].initial
                    js = fight.jurorsession_set.get(juror_id=old_chair_id)
                    if js.grades.count() > 0:
                        grade_del.append((js.juror,
                                          js.grades.all()))

            if form.cleaned_data["fight_%s_chair"%fight.pk]:

                f['chair'] = form.cleaned_data["fight_%s_chair"%fight.pk]

                if check_conflict_origin(fight, f['chair']):
                    conflicts.append({'fight':fight,'juror':f['chair']})

                plan_fi['jurors'].append({'id': f['chair'].pk, "name": f['chair'].attendee.full_name})

                fight_data['jurors'].append(f['chair'])


            jnow_pk = set(form.cleaned_data['fight_%s_juror' % fight.pk].values_list("pk",flat=True))
            jold_pk = set(form.fields['fight_%s_juror' % fight.pk].initial)
            jrm_pk = jold_pk - jnow_pk
            for jrm in list(jrm_pk):
                js = fight.jurorsession_set.get(juror_id=jrm)
                if js.grades.count() > 0:
                    grade_del.append((js.juror,
                                      js.jurorgrade_set.all()))

            f['jurors'] = form.cleaned_data['fight_%s_juror'%fight.pk]

            for ju in f['jurors']:
                if check_conflict_origin(fight, ju):
                    conflicts.append({'fight':fight,'juror':ju})

                plan_fi['jurors'].append({'id': ju.pk, "name": ju.attendee.full_name})

                fight_data['jurors'].append(ju)


            nvnow_pk = set(form.cleaned_data['fight_%s_nonvoting' % fight.pk].values_list("pk", flat=True))
            nvold_pk = set(form.fields['fight_%s_nonvoting' % fight.pk].initial)
            nvrm_pk = nvold_pk - nvnow_pk
            for nvrm in list(nvrm_pk):
                js = fight.jurorsession_set.get(juror_id=nvrm)
                if js.grades.count() > 0:
                    grade_del.append((js.juror,
                                      js.jurorgrade_set.all()))

            f['nonvoting'] = form.cleaned_data['fight_%s_nonvoting' % fight.pk]

            for ju in f['nonvoting']:
                if check_conflict_origin(fight, ju):
                    conflicts.append({'fight':fight,'juror':ju})

            round.append(f)
            plan_ro.append(plan_fi)
            round_fights["fights"].append(fight_data)


        context['round']=round
        context['deletions']=grade_del
        context['conflicts']=conflicts

        if self.round.order-1 in plan:
            plan[self.round.order-1]=plan_ro
            aplan[self.round.order-1]=round_fights

        # check hard constraint of chair meet teams only twice

        chairmeets = {}

        for round in aplan:
            for f in round['fights']:
                chairs = list(filter(lambda j: j.possible_chair, f['jurors']))
                if len(chairs) == 0:
                    continue
                chair = chairs[0]
                fight_origins = list(
                    f["fight"].stage_set.get(order=1).attendees.all().values_list("origin_id", flat=True))
                if chair.pk not in chairmeets:
                    chairmeets[chair.pk] = fight_origins
                else:
                    chairmeets[chair.pk] += fight_origins

        meets_too_often=[]
        for chair, sees in chairmeets.items():
            #sees is list
            for see in list(set(sees)):
                if sees.count(see) > 2:
                    meets_too_often.append({'juror':Juror.objects.get(pk=chair),'team':Origin.objects.get(id=see)})

        context['chairMeets']=meets_too_often

        after_cost = plan_cost(aplan, Juror.objects.filter(attendee__tournament=self.round.tournament))

        jurors_at_least_once = Juror.objects.filter(attendee__tournament=self.round.tournament)

        assignment_sorted = assignments_light(plan, jurors_at_least_once)

        context['assignments']=assignment_sorted

        costs_diff=[]
        for key, val in before_cost.items():
            diff = {'name':key,'old':val,'new':after_cost[key]}
            diff['diff']=after_cost[key] - val
            costs_diff.append(diff)

        context['costs'] = costs_diff


    def done(self, request, cleaned_data):

        trn = request.user.profile.tournament

        for fight in self.round.fight_set.all():
            try:
                current_chairrole = fight.jurorsession_set.get(role__type=JurorRole.CHAIR)
                current_chairrole_juror = current_chairrole.juror
            except:
                current_chairrole = None
                current_chairrole_juror = None

            if cleaned_data["fight_%s_chair"%fight.pk]:
                new_juror = cleaned_data["fight_%s_chair"%fight.pk]
                if current_chairrole_juror != cleaned_data["fight_%s_chair"%fight.pk]:
                    #replace role with newly assigned
                    if current_chairrole:
                        current_chairrole.delete()

                    # clean up jurors other assignments
                    try:
                        JurorSession.objects.get(juror=new_juror, fight__round=self.round).delete()
                    except:
                        pass
                    JurorSession.objects.create(juror=new_juror, fight=fight, role=JurorRole.objects.get(type=JurorRole.CHAIR, tournament=trn))

            elif current_chairrole:
                current_chairrole.delete()

            #jurors

            jnow_pk = set(cleaned_data['fight_%s_juror' % fight.pk])
            jold_pk = set(self.initials['fight_%s_juror' % fight.pk])

            jrm_pk = jold_pk - jnow_pk
            jadd_pk = jnow_pk - jold_pk
            for jrm in list(jrm_pk):
                fight.jurorsession_set.get(juror=jrm).delete()

            for jadd in list(jadd_pk):
                try:
                    JurorSession.objects.get(juror=jadd, fight__round=self.round).delete()
                except:
                    pass

                JurorSession.objects.create(juror=jadd, fight=fight, role=JurorRole.objects.get(type=JurorRole.JUROR, tournament=trn))

            # nv jurors

            nvnow_pk = set(cleaned_data['fight_%s_nonvoting' % fight.pk])
            nvold_pk = set(self.initialnv['fight_%s_nonvoting' % fight.pk])

            nvrm_pk = nvold_pk - nvnow_pk
            nvadd_pk = nvnow_pk - nvold_pk
            for nvrm in list(nvrm_pk):
                fight.jurorsession_set.get(juror=nvrm).delete()

            for nvadd in list(nvadd_pk):
                try:
                    JurorSession.objects.get(juror=nvadd, fight__round=self.round).delete()
                except:
                    pass

                JurorSession.objects.create(juror=nvadd, fight=fight,
                                            role=JurorRole.objects.get(type=JurorRole.NONVOTING, tournament=trn))

        return redirect("jury:edit_round", round=self.round.order)
