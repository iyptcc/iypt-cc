from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import Group
from django.core import serializers
from django.core.cache import caches
from django.core.serializers import pyyaml as pyyamlserializer
from django.db import IntegrityError, transaction
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_list_or_404, get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.account.models import ParticipationRole
from apps.dashboard.delete import ConfirmedDeleteView
from apps.printer.models import DefaultTemplate, Template
from apps.registration.models import AttendeeProperty
from apps.team.models import TeamRole

from .forms import (ADEditForm, BankSettingsForm, GroupEditForm, JurySettingsForm, PropertyChoiceFormSet,
                    RegistrationSettingsForm, RoleEditForm, TemplateSettingsForm, TournamentForm, TRoleEditForm)
from .models import Origin, Phase, Problem, Tournament
from .utils import _more_perm_than_group


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('tournament.change_tournament', raise_exception=False), name='dispatch')
class Overview(UpdateView):

    template_name = "tournament/overview.html"

    form_class = TournamentForm

    success_url = reverse_lazy("tournament:overview")

    def get_object(self, queryset=None):
        return self.request.user.profile.tournament


@method_decorator(permission_required('printer.change_defaulttemplate', raise_exception=False), name='dispatch')
class TemplateSettings(View):
    def get(self,request):
        form = TemplateSettingsForm(request.user.profile.tournament)

        return render(request, "tournament/overview.html",context={"form":form})

    def post(self, request):
        trn = request.user.profile.tournament
        form = TemplateSettingsForm(trn, request.POST)

        if form.is_valid():

            for type in Template.TYPE:
                if "default_template_%s"%type[0] in form.cleaned_data and form.cleaned_data["default_template_%s"%type[0]]:
                    try:
                        dt = DefaultTemplate.objects.get(tournament=trn, type=type[0])
                        dt.template = form.cleaned_data["default_template_%s"%type[0]]
                        dt.save()
                    except:
                        DefaultTemplate.objects.create(tournament=trn, template=form.cleaned_data["default_template_%s"%type[0]], type=type[0])

            messages.add_message(request, messages.SUCCESS, "Settings updated")

        return render(request, "tournament/overview.html", context={"form": form})

class RegistrationSettings(UpdateView):

    template_name = "tournament/overview.html"

    form_class = RegistrationSettingsForm

    success_url = reverse_lazy("tournament:registration")

    def get_object(self, queryset=None):
        return self.request.user.profile.tournament

class JurySettings(UpdateView):

    template_name = "tournament/overview.html"

    form_class = JurySettingsForm

    success_url = reverse_lazy("tournament:jury")

    def get_object(self, queryset=None):
        return self.request.user.profile.tournament

class BankSettings(UpdateView):

    template_name = "tournament/overview.html"

    form_class = BankSettingsForm

    success_url = reverse_lazy("tournament:bank")

    def get_object(self, queryset=None):
        return self.request.user.profile.tournament


@method_decorator(login_required, name='dispatch')
class ProblemView(ListView):

    template_name = "tournament/problemList.html"

    def get_queryset(self):
        return Problem.objects.filter(tournament=self.request.user.profile.tournament).order_by('number')



@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('tournament.change_problem', raise_exception=False), name='dispatch')
class ProblemChange(UpdateView):

    model = Problem
    fields = ["number", "title", "description"]

    success_url = reverse_lazy("tournament:problems")

    def get_object(self, queryset=None):
        obj = Problem.objects.get(id=self.kwargs['id'], tournament=self.request.user.profile.tournament)
        return obj

    def post(self, request, *args, **kwargs):
        # clear all caches
        caches['results'].clear()

        return super().post(request, *args, **kwargs)




@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('tournament.add_problem', raise_exception=False), name='dispatch')
class ProblemCreate(CreateView):

    model = Problem
    fields = ["number","title","description"]

    success_url = reverse_lazy("tournament:problems")

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        try:
            validation = super(ProblemCreate, self).form_valid(form)
            # clear all caches
            caches['results'].clear()
            return validation
        except IntegrityError:
            messages.add_message(self.request, messages.ERROR, "Problem number %d already exists"%form.instance.number)
            return redirect("tournament:problems")


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('tournament.delete_problem',raise_exception=False),name='dispatch')
class ProblemDelete(ConfirmedDeleteView):

    redirection = "tournament:problems"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(Problem, tournament=request.user.profile.tournament, id=kwargs["id"])
        return obj


@method_decorator(login_required, name='dispatch')
class OriginView(ListView):

    template_name = "tournament/originList.html"

    def get_queryset(self):
        return Origin.objects.filter(tournament=self.request.user.profile.tournament)

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('tournament.change_origin', raise_exception=False), name='dispatch')
class OriginChange(UpdateView):

    model = Origin
    fields = ["name", "alpha2iso","flag","short","flag_pdf"]

    success_url = reverse_lazy("tournament:origins")

    def get_object(self, queryset=None):
        obj = Origin.objects.get(id=self.kwargs['id'], tournament=self.request.user.profile.tournament)
        return obj

    def post(self, request, *args, **kwargs):
        # clear all caches
        caches['results'].clear()

        return super().post(request, *args, **kwargs)


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('tournament.add_origin', raise_exception=False), name='dispatch')
class OriginCreate(CreateView):

    model = Origin
    fields = ["name", "alpha2iso","flag"]

    success_url = reverse_lazy("tournament:origins")

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        try:
            validation = super(OriginCreate, self).form_valid(form)
            # clear all caches
            caches['results'].clear()
            return validation
        except IntegrityError:
            messages.add_message(self.request, messages.ERROR, "Origin %s already exists"%form.instance.name)
            return redirect("tournament:origins")


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('tournament.delete_origin',raise_exception=False),name='dispatch')
class OriginDelete(ConfirmedDeleteView):

    redirection = "tournament:origins"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(Origin, tournament=request.user.profile.tournament, id=kwargs["id"])
        return obj

@method_decorator(login_required, name='dispatch')
class AttendeeDataView(ListView):

    template_name = "tournament/dataList.html"

    def get_queryset(self):
        return AttendeeProperty.objects.filter(tournament=self.request.user.profile.tournament)

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('tournament.change_attendee_data', raise_exception=False), name='dispatch')
class ADChange(UpdateView):

    model = AttendeeProperty

    #form_class = ADEditForm

    success_url = reverse_lazy("tournament:properties")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return ADEditForm(self.request.user.profile.tournament, **self.get_form_kwargs())

    def get_context_data(self, **kwargs):
        context = super(ADChange, self).get_context_data(**kwargs)
        if self.request.POST:
            context['choices'] = PropertyChoiceFormSet(self.request.POST, instance=self.object)
        else:
            context['choices'] = PropertyChoiceFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        choices = context['choices']
        with transaction.atomic():
            self.object = form.save()
        if choices.is_valid():
            choices.instance = self.object
            choices.save()
        return super(ADChange, self).form_valid(form)

    def get_object(self, queryset=None):
        obj = AttendeeProperty.objects.get(id=self.kwargs['id'], tournament=self.request.user.profile.tournament)
        return obj

    def post(self, request, *args, **kwargs):
        # clear all caches
        #caches['results'].clear()

        return super().post(request, *args, **kwargs)

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('tournament.change_attendee_data', raise_exception=False), name='dispatch')
class ADCreate(CreateView):

    model = AttendeeProperty

    #form_class = ADEditForm

    success_url = reverse_lazy("tournament:properties")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return ADEditForm(self.request.user.profile.tournament, **self.get_form_kwargs())

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        try:
            validation = super(ADCreate, self).form_valid(form)
            # clear all caches
            return validation
        except IntegrityError:
            messages.add_message(self.request, messages.ERROR, "Attribute %s already exists"%form.instance.name)
            return redirect("tournament:properties")

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('tournament.delete_attendee_data',raise_exception=False),name='dispatch')
class ADDelete(ConfirmedDeleteView):

    redirection = "tournament:properties"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(AttendeeProperty, tournament=request.user.profile.tournament, id=kwargs["id"])
        return obj

@method_decorator(permission_required('tournament.change_attendee_data', raise_exception=False), name='dispatch')
class ADMove(View):
    def post(self, request, id,direction):
        obj = get_object_or_404(AttendeeProperty,id=self.kwargs['id'], tournament=self.request.user.profile.tournament)
        if direction=='up':
            obj.up()
        if direction=='down':
            obj.down()

        return redirect("tournament:properties")


@method_decorator(login_required, name='dispatch')
class PhasesView(ListView):

    template_name = "tournament/phases.html"

    def get_queryset(self):
        return Phase.objects.filter(tournament=self.request.user.profile.tournament)


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('tournament.add_phase', raise_exception=False), name='dispatch')
class PhaseCreate(CreateView):

    model = Phase
    fields = ["name","duration","linked"]

    success_url = reverse_lazy("tournament:phases")

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        try:
            return super(PhaseCreate, self).form_valid(form)
        except IntegrityError:
            messages.add_message(self.request, messages.ERROR, "Role of type %s already exists"%form.instance.get_type_display())
            return redirect("tournament:phases")

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('tournament.change_phase', raise_exception=False), name='dispatch')
class PhaseChange(UpdateView):

    model = Phase
    fields = ["name", "duration", "linked"]

    success_url = reverse_lazy("tournament:phases")

    def get_object(self, queryset=None):
        obj = Phase.objects.get(id=self.kwargs['id'], tournament=self.request.user.profile.tournament)
        return obj

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('tournament.delete_phase',raise_exception=False),name='dispatch')
class PhaseDelete(ConfirmedDeleteView):

    redirection = "tournament:phases"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(Phase, tournament=request.user.profile.tournament, id=kwargs["id"])
        return obj

@method_decorator(permission_required('tournament.change_phase', raise_exception=False), name='dispatch')
class PhaseMove(View):
    def post(self, request, id,direction):
        obj = get_object_or_404(Phase,id=self.kwargs['id'], tournament=self.request.user.profile.tournament)
        if direction=='up':
            obj.up()
        if direction=='down':
            obj.down()

        return redirect("tournament:phases")


@method_decorator(login_required, name='dispatch')
class RolesView(ListView):

    template_name = "tournament/rolesList.html"

    def get_queryset(self):
        return ParticipationRole.objects.filter(tournament=self.request.user.profile.tournament)


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('account.add_participationrole', raise_exception=False), name='dispatch')
class RoleCreate(CreateView):

    model = ParticipationRole
    fields = ["name","type","groups"]

    success_url = reverse_lazy("tournament:proles")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return RoleEditForm(self.request.user.profile.tournament, **self.get_form_kwargs())

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        try:
            return super(RoleCreate, self).form_valid(form)
        except IntegrityError:
            messages.add_message(self.request, messages.ERROR, "Role of type %s already exists"%form.instance.get_type_display())
            return redirect("tournament:proles")

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('account.change_participationrole', raise_exception=False), name='dispatch')
class RoleChange(UpdateView):

    model = ParticipationRole
    fields = ["name", "type", "groups"]

    success_url = reverse_lazy("tournament:proles")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return RoleEditForm(self.request.user.profile.tournament, **self.get_form_kwargs())

    def get_object(self, queryset=None):
        obj = ParticipationRole.objects.get(id=self.kwargs['id'], tournament=self.request.user.profile.tournament)
        return obj

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('account.delete_participationrole',raise_exception=False),name='dispatch')
class RoleDelete(ConfirmedDeleteView):

    redirection = "tournament:proles"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(ParticipationRole, tournament=request.user.profile.tournament, id=kwargs["id"])
        return obj

@method_decorator(login_required, name='dispatch')
class TRolesView(ListView):

    template_name = "tournament/trolesList.html"

    def get_queryset(self):
        return TeamRole.objects.filter(tournament=self.request.user.profile.tournament)


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('team.add_teamrole', raise_exception=False), name='dispatch')
class TRoleCreate(CreateView):

    model = TeamRole
    fields = ["name","type","participation_roles"]

    success_url = reverse_lazy("tournament:troles")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return TRoleEditForm(self.request.user.profile.tournament, **self.get_form_kwargs())

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        try:
            return super(TRoleCreate, self).form_valid(form)
        except IntegrityError:
            messages.add_message(self.request, messages.ERROR, "Team Role of type %s already exists"%form.instance.get_type_display())
            return redirect("tournament:troles")

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('team.change_teamrole', raise_exception=False), name='dispatch')
class TRoleChange(UpdateView):

    model = TeamRole
    fields = ["name", "type","participation_roles"]

    success_url = reverse_lazy("tournament:troles")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return TRoleEditForm(self.request.user.profile.tournament, **self.get_form_kwargs())

    def get_object(self, queryset=None):
        obj = TeamRole.objects.get(id=self.kwargs['id'], tournament=self.request.user.profile.tournament)
        return obj

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('team.delete_teamrole',raise_exception=False),name='dispatch')
class TRoleDelete(ConfirmedDeleteView):

    redirection = "tournament:troles"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(TeamRole, tournament=request.user.profile.tournament, id=kwargs["id"])
        return obj

@method_decorator(login_required, name='dispatch')
class GroupsView(ListView):

    template_name = "tournament/groupsList.html"

    def get_queryset(self):
        groups = self.request.user.profile.tournament.groups.all()
        gr = []
        for g in groups:
            if _more_perm_than_group(self.request.user, g):
                gr.append((g,True))
            else:
                gr.append((g, False))
        return gr

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('auth.add_group', raise_exception=False), name='dispatch')
class GroupCreate(CreateView):

    model = Group

    success_url = reverse_lazy("tournament:pgroups")

    form_class = GroupEditForm

    def get_form(self, form_class=None):
        return GroupEditForm(self.request.user.profile.active, **self.get_form_kwargs())

    def form_valid(self, form):
        g = form.save(commit=False)
        try:
            g.save()
            self.request.user.profile.tournament.groups.add(g)
        except IntegrityError:
            messages.add_message(self.request, messages.ERROR, "Group of name %s already exists"%form.instance.name)
        form.save()
        return redirect("tournament:pgroups")

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('auth.change_group', raise_exception=False), name='dispatch')
class GroupChange(UpdateView):

    model = Group

    def get_form(self, form_class=None):
        return GroupEditForm(self.request.user.profile.active, **self.get_form_kwargs())

    success_url = reverse_lazy("tournament:pgroups")

    def get_object(self, queryset=None):
        obj = self.request.user.profile.tournament.groups.get(id=self.kwargs['id'])
        if obj.tournament_set.count() > 1:
            raise Group.DoesNotExist("It is a shared group")
        if not _more_perm_than_group(self.request.user, obj):
            raise Group.DoesNotExist("Not enough permissions")

        return obj

class MultiSerializer(pyyamlserializer.Serializer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current = None
        self.objects = []

    def start_serialization(self):
        pass

    pass

class DumpView(View):
    def get(self, request):
        serializer = MultiSerializer()
        serializer.serialize(TeamRole.objects.filter(tournament=request.user.profile.tournament), fields=("name","type","participation_roles","members_min","members_max"))
        serializer.serialize(ParticipationRole.objects.filter(tournament=request.user.profile.tournament), fields=("name","type","groups","fee","manager_approvable"))
        serializer.serialize(Tournament.objects.filter(pk=request.user.profile.tournament.id))
        serializer.serialize(AttendeeProperty.objects.filter(tournament=request.user.profile.tournament))
        serializer.serialize(DefaultTemplate.objects.filter(tournament=request.user.profile.tournament))
        serializer.serialize(Problem.objects.filter(tournament=request.user.profile.tournament))
        serializer.serialize(request.user.profile.tournament.groups.all())
        data = serializer.getvalue()

        for obj in serializers.deserialize("yaml", data):
            print(obj)

        return render(request,"tournament/dump.html",context={"yaml":data})
