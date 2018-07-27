from django import forms
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import slugify
from django.utils.decorators import method_decorator
from django.utils.text import capfirst
from django_select2.forms import Select2MultipleWidget, Select2Widget
from formtools.preview import FormPreview
from unidecode import unidecode

from apps.account.models import ActiveUser, Attendee
from apps.dashboard.forms import ModelDeleteListField
from apps.jury.models import Juror
from apps.plan.models import Fight, FightRole, Room, Round, Stage, StageAttendance, TeamPlaceholder
from apps.result.utils import _ranking
from apps.team.models import Team, TeamMember, TeamRole
from apps.tournament.models import (ScheduleTemplate, TemplateAttendance, TemplateFight, TemplateRoom, TemplateRound,
                                    Tournament)


@method_decorator(login_required, name='__call__')
@method_decorator(permission_required('auth.change_user'), name='__call__')
class UserPreview(FormPreview):

    form_template = "management/users.html"
    preview_template = "dashboard/previewObjsDelete.html"

    def parse_params(self, request):

        self.filters = [
            {"name": "Tournament",
             "filter": "tournaments__in",
             "elements": Tournament.objects.all()
             }
        ]

        #    {"name": "Roles",
        #     "filter": "roles__in",
        #     "elements": trn.participationrole_set.all()},
        #    {'name': "Groups",
        #     "elements": trn.groups.all(),
        #     "filter": "groups__in"},
        #    {'name': "Team",
        #     "elements": trn.team_set.all(),
        #     "filter": "team__in"},
        #]

        self._filters = {}
        self._excludes = {}

        for fname in [x['filter'] for x in self.filters]:
            try:
                inarg = request.GET.getlist("in_%s" % fname, None)
                if len(inarg) > 0:
                    self._filters[fname] = list(map(int, inarg))
                exarg = request.GET.getlist("ex_%s" % fname, None)
                if len(exarg) > 0:
                    self._excludes[fname] = list(map(int, exarg))
            except:
                pass

        ex_query = Q()

        for k in self._excludes:
            ex_query |= Q(**{k: self._excludes[k]})

        person = ModelDeleteListField(queryset=ActiveUser.objects.filter(**self._filters).prefetch_related("tournaments")
                                      .exclude(ex_query)
                                      .order_by("user__last_name")
                                      .prefetch_related('user',"attendee_set"))

        tournaments = forms.ModelMultipleChoiceField(queryset=Tournament.objects.all(),required=False,
                                                     widget=Select2MultipleWidget())
        #groups = forms.ModelMultipleChoiceField(queryset=trn.groups.all(),required=False,
        #                                        widget=Select2MultipleWidget())

        self.form = type("PersonsForm", (forms.Form,), {'persons':person,'tournaments':tournaments})

    def get_context(self, request, form):

        filters = []

        for fil in self.filters:
            f = {'name': fil['name'],
                 "elements": fil['elements'],
                 "link_name": fil['filter']}

            filter_rest = "&".join(["&".join(["in_%s=%s" % (f, g) for g in self._filters[f]])
                                    for f in self._filters if f != fil['filter']])

            exclude_rest = "&".join(["&".join(["ex_%s=%s" % (f, g) for g in self._excludes[f]])
                                     for f in self._excludes if f != fil['filter']])

            f['link_rest'] = "&".join([filter_rest, exclude_rest])

            f["in_actives"] = self._filters.get(fil['filter'], [])
            f["ex_actives"] = self._excludes.get(fil['filter'], [])

            filters.append(f)

        return {
            'filters': filters,
            'form': form,
            'stage_field': self.unused_name('stage'),
            'state': self.state,
        }

    def process_preview(self, request, form, context):

        def format_callback(obj):
            return '%s: %s' % (capfirst(obj._meta.verbose_name), obj)

        if "_delete" in request.POST:
            context['action'] = "_delete"


            ps = list(map(lambda x: x.user ,form.cleaned_data['persons']))
            collector = NestedObjects(using='default')  # or specific database
            collector.collect(ps)
            to_delete = collector.nested(format_callback)

            context['objs']=to_delete

        else:

            self.preview_template = "management/userAssignPreview.html"

            persons = []
            delobjects = []

            for user in form.cleaned_data['persons'].prefetch_related(
                                                        'user',
                                                        ):
                person = {"full_name": "%s %s"%(user.user.first_name, user.user.last_name),
                          'tournaments': list(user.tournaments.values_list("name",flat=True)),
                          'username': user.user.username,
                          }

                if "_add_tournaments" in request.POST:
                    context['action'] = "_add_tournaments"
                    news=form.cleaned_data['tournaments']
                    person['tournaments_new']=[]
                    for new in news:
                        if new.name not in person['tournaments']:
                            person['tournaments_new'].append(new)

                if "_del_tournaments" in request.POST:
                    context['action'] = "_del_tournaments"
                    deles=form.cleaned_data['tournaments']
                    person['tournaments_del'] = []
                    person['tournaments_del_na'] = []

                    delatt = Attendee.objects.filter(active_user=user, tournament__in=deles)
                    delobjects+=list(delatt)

                    for dele in deles:
                        if dele.name in person['tournaments']:
                            person['tournaments'].remove(dele.name)
                            person['tournaments_del'].append(dele.name)
                        else:
                            person['tournaments_del_na'].append(dele.name)

                persons.append(person)

            context['persons']=persons

            collector = NestedObjects(using='default')  # or specific database
            collector.collect(delobjects)
            to_delete = collector.nested(format_callback)

            context['objs'] = to_delete

    @method_decorator(permission_required('plan.change_attendee'))
    def done(self, request, cleaned_data):

        ps = cleaned_data['persons']

        if 'action' not in request.POST:
            for auser in ps:
                auser.user.delete()

        elif request.POST['action'] == '_add_tournaments':
            news = cleaned_data['tournaments']
            for user in ps:
                for new in news:
                    Attendee.objects.get_or_create(active_user=user, tournament=new)
        elif request.POST['action'] == '_del_tournaments':
            news = cleaned_data['tournaments']
            for user in ps:
                Attendee.objects.filter(active_user=user, tournament__in=news).delete()

        return redirect('management:users')
