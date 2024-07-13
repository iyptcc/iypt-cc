import json
from datetime import datetime

import xlsxwriter
import yaml
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import AccessMixin, UserPassesTestMixin
from django.core.mail import send_mail
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_list_or_404, get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView
from django_downloadview import ObjectDownloadView

from apps.account.models import Attendee, ParticipationRole
from apps.bank.utils import expected_fees
from apps.dashboard.delete import ConfirmedDeleteView
from apps.jury.models import Juror, PossibleJuror
from apps.team.models import Team, TeamMember, TeamRole
from apps.tournament.models import Origin, Tournament

from .forms import (
    AcceptMemberForm,
    AcceptRoleForm,
    AcceptTeamForm,
    ApplyForTeamForm,
    AttendeePropertyForm,
    DeclineRoleForm,
    DeclineTeamForm,
    EditMemberForm,
    TeamSettingsForm,
)
from .models import (
    Application,
    ApplicationQuestionValue,
    AttendeeProperty,
    AttendeePropertyValue,
    UserPropertyValue,
)
from .utils import (
    MyEncoder,
    accept_teammanager,
    application_propertyvalues,
    delete_teamrole,
    get_members,
    persons_data,
    update_property,
)
from .validators import (
    DataValidator,
    ExperiencedJurorValidator,
    TeamLeaderValidator,
    TeamManagerWaitValidator,
    TeamMemberValidator,
)


@method_decorator(login_required, name="dispatch")
class ApplicationsList(ListView):

    template_name = "registration/list.html"

    def get_queryset(self):
        return Application.objects.filter(applicant=self.request.user.profile)

    def get_context_data(self, **kwargs):
        context = super(ApplicationsList, self).get_context_data(**kwargs)

        context["tournaments"] = []
        for trn in Tournament.objects.filter(
            registration_open__lt=timezone.now(), registration_close__gt=timezone.now()
        ):
            apply = {"slug": trn.slug, "name": trn.name}
            apply["attendee"] = self.request.user.profile.attendee_set.filter(
                tournament=trn
            ).exists()
            apply["troles"] = (
                trn.teamrole_set.all().exclude(type=TeamRole.ASSOCIATED),
            )
            apply["manager_roles"] = trn.participationrole_set.filter(
                approvable_by__type=ParticipationRole.TEAM_MANAGER
            )
            prs = {}
            for pr in trn.participationrole_set.all():
                prs[pr.type] = pr.id
            apply["roles"] = prs
            trs = {}
            for tr in trn.teamrole_set.all():
                trs[tr.type] = tr.id
            apply["team_roles"] = trs
            if self.request.user.profile.tournament == trn:
                apply["active"] = True

            apply["disabled_actions"] = []
            apply["available_actions"] = []
            apply["finished_actions"] = []
            apply["wait_actions"] = []

            mgv = TeamManagerWaitValidator()
            tmv = TeamMemberValidator()
            tlv = TeamLeaderValidator()
            dav = DataValidator()
            pjv = ExperiencedJurorValidator()
            nodes = mgv.passed(activeuser=self.request.user.profile, tournament=trn)
            nodes.update(
                tmv.passed(activeuser=self.request.user.profile, tournament=trn)
            )
            nodes.update(
                tlv.passed(activeuser=self.request.user.profile, tournament=trn)
            )
            nodes.update(
                dav.passed(activeuser=self.request.user.profile, tournament=trn)
            )
            nodes.update(
                pjv.passed(activeuser=self.request.user.profile, tournament=trn)
            )
            for node, state in nodes.items():
                apply["%s_actions" % state].append(node)

            if not apply["attendee"]:
                apply["disabled_actions"] += [
                    "associate_experiencedjuror",
                    "associate_role",
                ]

            if apply["attendee"]:
                apply["proles"] = self.request.user.profile.attendee_set.get(
                    tournament=trn
                ).roles.all()

                real = False
                for role in apply["proles"]:
                    if role.attending:
                        real = True
                apply["attending_role"] = real

            if trn.logo:
                apply["logo"] = True

            apply["possible_juror"] = PossibleJuror.objects.filter(
                person=self.request.user.profile,
                approved_by__isnull=False,
                tournament=trn,
            ).exists()

            context["tournaments"].append(apply)

        context["upcomming"] = Tournament.objects.filter(
            registration_open__gt=timezone.now()
        )

        context["jurors"] = self.request.user.profile.possiblejuror_set.filter(
            approved_at__isnull=True
        )

        return context


@method_decorator(login_required, name="dispatch")
class WithdrawApplication(ConfirmedDeleteView):
    redirection = "registration:applications"

    def get_objects(self, request, *args, **kwargs):
        objs = get_list_or_404(
            Application, pk=kwargs["id"], applicant=self.request.user.profile
        )

        return objs


@method_decorator(login_required, name="dispatch")
class WithdrawPossible(ConfirmedDeleteView):
    redirection = "registration:applications"

    def get_objects(self, request, *args, **kwargs):
        objs = get_list_or_404(
            PossibleJuror,
            pk=kwargs["id"],
            person=self.request.user.profile,
            approved_at__isnull=True,
        )

        return objs


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("registration.accept_team"), name="dispatch")
class TeamApplicationsList(ListView):

    template_name = "registration/list_team_applications.html"

    def get_queryset(self):
        trn = self.request.user.profile.tournament

        return Application.objects.filter(tournament=trn, origin__isnull=False)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("registration.accept_team"), name="dispatch")
class TeamApplicationsAccept(View):

    def get(self, request, id):

        app = get_object_or_404(
            Application, id=id, tournament=request.user.profile.tournament
        )

        form = AcceptTeamForm(app)

        context = application_propertyvalues(
            app.tournament, app.participation_role, app.applicant
        )

        return render(
            request,
            "registration/accept_team_application.html",
            context={"form": form, **context},
        )

    def post(self, request, id):
        trn = request.user.profile.tournament

        app = get_object_or_404(Application, id=id, tournament=trn)

        form = AcceptTeamForm(app, request.POST)

        if form.is_valid():

            accept_teammanager(
                request,
                trn,
                app.origin,
                form.cleaned_data["competing"],
                app.applicant,
                app.participation_role,
            )

            app.handled_as = Application.ACCEPTED
            app.handled_at = timezone.now()
            app.handled_by = request.user.profile.active
            app.save()

            if form.cleaned_data["notify"]:
                send_mail(
                    "Your team application for %s was accepted" % (app.origin.name),
                    "Team %s was accepted. After setting a password, team members can apply to your team \n Please make sure to select the correct active tournament unter Profile > Tournament"
                    % (app.origin.name),
                    settings.EMAIL_FROM,
                    [app.applicant.user.email],
                    fail_silently=False,
                )

            return redirect("registration:list_team_applications")

        return render(
            request, "registration/accept_team_application.html", context={"form": form}
        )


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("registration.manage_team"), name="dispatch")
class ListManageableTeams(ListView):
    template_name = "registration/list_manageable_teams.html"

    def get_queryset(self):
        trn = self.request.user.profile.tournament

        if self.request.user.has_perm("registration.manage_all_teams"):
            tqs = Team.objects.filter(tournament=trn)
        else:
            tqs = [
                tm.team
                for tm in TeamMember.objects.filter(
                    attendee__tournament=trn,
                    attendee__active_user=self.request.user.profile,
                    manager=True,
                )
            ]

        teams = []
        apoq = AttendeeProperty.user_objects.filter(tournament=trn).prefetch_related(
            "required", "optional"
        )

        detailed = True
        if len(tqs) > 2:
            detailed = False

        for team in tqs:
            try:
                role = team.teammember_set.get(
                    attendee__active_user=self.request.user.profile
                ).role
            except:
                role = None
            members, aps, limits, missing = get_members(
                self.request.user.profile.tournament, team, apoq, detailed=detailed
            )

            teams.append(
                {
                    "team": team,
                    "role": role,
                    "members": members,
                    "limits": limits,
                    "missing": missing,
                    "is_competing": team.is_competing,
                    "detailed": detailed,
                }
            )
        return teams


class UserPassesTestMixinPreview(AccessMixin):
    """
    Deny a request with a permission error if the test_func() method returns
    False.
    """

    def test_func(self):
        raise NotImplementedError(
            "{0} is missing the implementation of the test_func() method.".format(
                self.__class__.__name__
            )
        )

    def get_test_func(self):
        """
        Override this method to use a different test_func method.
        """
        return self.test_func

    def dispatch(self, request, *args, **kwargs):
        user_test_result = self.get_test_func()()
        if not user_test_result:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def __call__(self, request, *args, **kwargs):
        self.request = request
        user_test_result = self.get_test_func()()
        if not user_test_result:
            return self.handle_no_permission()
        return super().__call__(request, *args, **kwargs)


class TeamMgntPermMixin(UserPassesTestMixinPreview):
    def test_func(self):
        if self.request.user.has_perm("registration.manage_all_teams"):
            return True
        try:
            # TODO: check for expired deadline
            team = Team.objects.get(
                origin__slug=self.request.resolver_match.kwargs["s_team"],
                tournament=self.request.user.profile.tournament,
            )
            if team.teammember_set.filter(
                manager=True, attendee__active_user=self.request.user.profile
            ).exists():
                return True
        except:
            return False

        return False


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("registration.manage_data"), name="dispatch")
class DataOverview(View):

    def get(self, request):
        tournament = request.user.profile.tournament

        att = Attendee.objects.get(
            tournament=tournament, active_user=request.user.profile
        )

        form = AttendeePropertyForm(att, read_profile=True, hidden=False)

        return render(
            request, "registration/data.html", context={"form": form, "attendee": att}
        )

    def post(self, request):

        tournament = request.user.profile.tournament

        att = Attendee.objects.get(
            tournament=tournament, active_user=request.user.profile
        )

        form = AttendeePropertyForm(att, True, False, request.POST, request.FILES)

        if form.is_valid():

            form.save(request)

            return redirect("registration:attendeeproperty")

        return render(
            request, "registration/data.html", context={"form": form, "attendee": att}
        )


@method_decorator(login_required, name="dispatch")
class FilePropertyView(ObjectDownloadView):
    attachment = False

    def get_object(self, queryset=None):
        if self.kwargs["typ"] == "a":
            try:
                if int(self.kwargs["user"]) != self.request.user.profile.active.id:
                    teams = Team.objects.filter(
                        members__id=self.kwargs["user"],
                        tournament=self.request.user.profile.tournament,
                    )
                    amgr = False
                    for team in teams:
                        if team.teammember_set.filter(
                            manager=True,
                            attendee__active_user=self.request.user.profile,
                        ).exists():
                            amgr = True
                    if self.request.user.has_perm("registration.manage_all_teams"):
                        pass
                    elif not amgr:
                        raise PermissionError()

                obj = AttendeePropertyValue.objects.get(
                    attendee_id=int(self.kwargs["user"]), id=self.kwargs["id"]
                )
                file = getattr(obj, obj.field_name[obj.property.type])
                return file
            except Exception as e:
                print(e)
                raise AttendeePropertyValue.DoesNotExist("Image does not exist")
        elif self.kwargs["typ"] == "u":
            try:
                obj = UserPropertyValue.objects.get(
                    user_id=int(self.kwargs["user"]), id=self.kwargs["id"]
                )
                if int(self.kwargs["user"]) != self.request.user.profile.id:
                    # applied as possible juror or is possible juror
                    try:
                        pJ = PossibleJuror.objects.get(
                            person_id=int(self.kwargs["user"]),
                            tournament=self.request.user.profile.tournament,
                            # approved_by__isnull=True,
                        )

                        Jrequired = AttendeeProperty.user_objects.get(
                            user_property=obj.property,
                            tournament=self.request.user.profile.tournament,
                            apply_required__type=ParticipationRole.JUROR,
                        )

                    except:
                        pJ = None
                        Jrequired = False

                    # applied with role
                    try:
                        rapp = Application.objects.filter(
                            applicant_id=int(self.kwargs["user"]),
                            tournament=self.request.user.profile.tournament,
                            origin__isnull=True,
                            team__isnull=True,
                        )

                        Rrequired = False
                        for r in rapp:
                            if AttendeeProperty.user_objects.filter(
                                user_property=obj.property,
                                tournament=self.request.user.profile.tournament,
                                apply_required=r.participation_role,
                            ).exists():
                                Rrequired = True
                        rapps = rapp.count()
                    except:
                        rapps = 0
                        Rrequired = False
                        pass

                    # apply teammanager
                    try:
                        tapp = Application.objects.filter(
                            applicant_id=int(self.kwargs["user"]),
                            tournament=self.request.user.profile.tournament,
                            origin__isnull=False,
                        )

                        Trequired = False
                        for r in tapp:
                            if AttendeeProperty.user_objects.filter(
                                user_property=obj.property,
                                tournament=self.request.user.profile.tournament,
                                apply_required=r.participation_role,
                            ).exists():
                                Trequired = True
                        tapps = tapp.count()
                    except:
                        tapps = 0
                        Trequired = False
                        pass

                    # apply teammmeber
                    try:
                        mapp = Application.objects.filter(
                            applicant_id=int(self.kwargs["user"]),
                            tournament=self.request.user.profile.tournament,
                            team__teammember__in=self.request.user.profile.active.teammember_set.filter(
                                manager=True
                            ),
                        )

                        Mrequired = False
                        for r in mapp:
                            if AttendeeProperty.user_objects.filter(
                                user_property=obj.property,
                                tournament=self.request.user.profile.tournament,
                                apply_required=r.participation_role,
                            ).exists():
                                Mrequired = True
                        mapps = mapp.count()
                    except:
                        mapps = 0
                        Mrequired = False
                        pass

                    if (
                        pJ
                        and Jrequired
                        and self.request.user.has_perm("registration.accept_juror")
                    ):
                        pass
                    elif (
                        rapps > 0
                        and Rrequired
                        and self.request.user.has_perm("registration.accept_role")
                    ):
                        pass
                    elif (
                        tapps > 0
                        and Trequired
                        and self.request.user.has_perm("registration.accept_team")
                    ):
                        pass
                    elif (
                        mapps > 0
                        and Mrequired
                        and self.request.user.has_perm("registration.manage_team")
                    ):
                        pass
                    else:
                        raise PermissionError()
                file = getattr(obj, obj.field_name[obj.property.type])
                return file
            except Exception as e:
                print(e)
                raise AttendeePropertyValue.DoesNotExist("Image does not exist")


class TournamentLogo(ObjectDownloadView):
    attachment = False

    def get_object(self, queryset=None):
        try:
            obj = Tournament.objects.get(slug=self.kwargs["t_slug"]).logo
            return obj
        except Exception as e:
            print(e)
            raise Tournament.DoesNotExist("Logo does not exist")


@method_decorator(login_required, name="dispatch")
class AssociateToTeam(View):

    def get(self, request, t_slug):
        tournament = get_object_or_404(
            Tournament,
            slug=t_slug,
            registration_open__lt=timezone.now(),
            registration_close__gt=timezone.now(),
        )

        form = ApplyForTeamForm(tournament)

        return render(
            request,
            "registration/apply_teammember.html",
            context={"form": form, "tournament": tournament},
        )

    def post(self, request, t_slug):
        tournament = get_object_or_404(
            Tournament,
            slug=t_slug,
            registration_open__lt=timezone.now(),
            registration_close__gt=timezone.now(),
        )

        form = ApplyForTeamForm(tournament, request.POST)

        if form.is_valid():

            team = form.cleaned_data["team"]

            Application.objects.create(
                applicant=request.user.profile,
                tournament=tournament,
                participation_role=request.user.profile.attendee_set.get(
                    tournament=tournament
                ).roles.first(),
                team=team,
                team_role=TeamRole.objects.get(
                    tournament=tournament, type=TeamRole.ASSOCIATED
                ),
            )
            messages.add_message(
                request,
                messages.SUCCESS,
                "Applied for association to team %s in tournament %s"
                % (team.origin, tournament),
            )

            if team.notify_applications:
                send_mail(
                    "%s applied to be an associate of your team %s"
                    % (request.user.username, team.origin.name),
                    "%s %s (%s, %s) applied to team %s with role %s"
                    % (
                        request.user.first_name,
                        request.user.last_name,
                        request.user.username,
                        request.user.email,
                        team.origin.name,
                        TeamRole.ASSOCIATED,
                    ),
                    settings.EMAIL_FROM,
                    team.teammember_set.filter(
                        role__type__in=[TeamRole.LEADER]
                    ).values_list("attendee__active_user__user__email", flat=True),
                    fail_silently=False,
                )

            return redirect("registration:applications")

        return render(
            request,
            "registration/apply_teammember.html",
            context={"form": form, "tournament": tournament},
        )


@method_decorator(login_required, name="dispatch")
class TeamMemberAccept(TeamMgntPermMixin, View):

    def get(self, request, s_team, id):

        app = get_object_or_404(
            Application,
            id=id,
            team__origin__slug=s_team,
            tournament=request.user.profile.tournament,
        )

        context = {}
        if app.team_role.type != TeamRole.ASSOCIATED:
            context = application_propertyvalues(
                app.tournament, app.participation_role, app.applicant
            )
        elif app.participation_role.type == ParticipationRole.VISITOR:

            vislimit = 100000
            if app.participation_role.global_limit != None:
                vislimit = app.participation_role.global_limit

            if (
                app.tournament.attendee_set.filter(
                    roles__type=ParticipationRole.VISITOR
                ).count()
                <= vislimit
            ):
                context = application_propertyvalues(
                    app.tournament, app.participation_role, app.applicant
                )
            else:
                messages.add_message(
                    request,
                    messages.ERROR,
                    "Total limit of %d visitors reached." % vislimit,
                )

                return redirect("registration:team_overview", s_team)

        form = AcceptMemberForm(app)

        return render(
            request,
            "registration/accept_team_member.html",
            context={"form": form, **context},
        )

    def post(self, request, s_team, id):
        trn = request.user.profile.tournament

        app = get_object_or_404(
            Application,
            id=id,
            team__origin__slug=s_team,
            tournament=request.user.profile.tournament,
        )

        form = AcceptMemberForm(app, request.POST)

        if form.is_valid():

            if app.participation_role.type == ParticipationRole.VISITOR:
                vislimit = 100000
                if app.participation_role.global_limit != None:
                    vislimit = app.participation_role.global_limit
                if (
                    app.tournament.attendee_set.filter(
                        roles__type=ParticipationRole.VISITOR
                    ).count()
                    > vislimit
                ):
                    messages.add_message(
                        request,
                        messages.ERROR,
                        "Total limit of %d visitors reached."
                        % app.participation_role.global_limit,
                    )

                    return redirect("registration:team_overview", s_team)

            att = Attendee.objects.get_or_create(
                tournament=trn, active_user=app.applicant
            )[0]

            teamrole = form.cleaned_data["role"]

            if not TeamMember.objects.filter(team=app.team, attendee=att).exists():
                TeamMember.objects.create(team=app.team, attendee=att, role=teamrole)
            else:
                tm = TeamMember.objects.get(team=app.team, attendee=att)
                tm.role = teamrole

            try:
                att.roles.add(*teamrole.participation_roles.all())
            except:
                messages.add_message(
                    request,
                    messages.WARNING,
                    "Teamleader Role has no Participation Role",
                )

            if app.participation_role.type == ParticipationRole.VISITOR:
                att.roles.add(app.participation_role)

            if app.team_role.type != TeamRole.ASSOCIATED or (
                app.team_role.type == TeamRole.ASSOCIATED
                and app.participation_role.type == ParticipationRole.VISITOR
            ):

                for ap in AttendeeProperty.user_objects.filter(
                    Q(tournament=trn), Q(apply_required=app.participation_role)
                ):

                    t = ap.user_property.type
                    up = ap.user_property

                    valueo = UserPropertyValue.objects.filter(
                        user=app.applicant, property=up
                    ).last()

                    if valueo:
                        value = getattr(valueo, valueo.field_name[t])
                        update_property(
                            request,
                            ap,
                            None,
                            value,
                            "attendee-property-%d",
                            AttendeePropertyValue,
                            {"attendee": att, "author": request.user.profile},
                            copy_image=True,
                        )

            app.handled_as = Application.ACCEPTED
            app.handled_at = timezone.now()
            app.handled_by = request.user.profile.active
            app.save()

            if form.cleaned_data["notify"]:
                send_mail(
                    "Your membership application for %s was accepted"
                    % (app.team.origin.name),
                    "You were accepted as member of team %s. \n Please make sure to select the correct active tournament unter Profile > Tournament"
                    % (app.team.origin.name),
                    settings.EMAIL_FROM,
                    [att.active_user.user.email],
                    fail_silently=False,
                )

            return redirect("registration:team_overview", s_team)

        return render(
            request, "registration/accept_team_member.html", context={"form": form}
        )


@method_decorator(login_required, name="dispatch")
class TeamMemberEdit(TeamMgntPermMixin, View):

    def get(self, request, s_team, id):

        tm = get_object_or_404(
            TeamMember,
            id=id,
            team__origin__slug=s_team,
            team__tournament=request.user.profile.tournament,
        )

        form = EditMemberForm(tm)

        return render(
            request, "registration/accept_team_member.html", context={"form": form}
        )

    def post(self, request, s_team, id):
        tm = get_object_or_404(
            TeamMember,
            id=id,
            team__origin__slug=s_team,
            team__tournament=request.user.profile.tournament,
        )

        form = EditMemberForm(tm, request.POST)

        if form.is_valid():

            teamrole = form.cleaned_data["role"]

            delete_teamrole(tm)

            tm.role = teamrole
            tm.manager = form.cleaned_data["manager"]
            tm.save()

            if tm.manager:
                tm.attendee.roles.add(
                    request.user.profile.tournament.participationrole_set.filter(
                        type=ParticipationRole.TEAM_MANAGER
                    ).first()
                )
            elif not tm.attendee.teammember_set.filter(manager=True).exists():
                tm.attendee.roles.remove(
                    request.user.profile.tournament.participationrole_set.filter(
                        type=ParticipationRole.TEAM_MANAGER
                    ).first()
                )
                # check other managements

            if "juror" in form.cleaned_data and form.cleaned_data["juror"] is True:
                tm.attendee.roles.add(
                    request.user.profile.tournament.participationrole_set.filter(
                        type=ParticipationRole.JUROR
                    ).first()
                )
            else:
                try:
                    tm.attendee.roles.remove(
                        request.user.profile.tournament.participationrole_set.filter(
                            type=ParticipationRole.JUROR
                        ).first()
                    )
                except Exception as e:
                    print(e)
                    pass
            tm.attendee.roles.add(*teamrole.participation_roles.all())

            return redirect("registration:team_overview", s_team)

        return render(
            request, "registration/accept_team_member.html", context={"form": form}
        )


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("registration.manage_all_teams"), name="dispatch")
class EditAttendeeData(View):

    def get(self, request, id):

        att = get_object_or_404(
            Attendee, id=id, tournament=request.user.profile.tournament
        )

        form = AttendeePropertyForm(att, read_profile=False, hidden=True)

        return render(
            request,
            "registration/attdata.html",
            context={"form": form, "attendee": att},
        )

    def post(self, request, id):

        att = get_object_or_404(
            Attendee, id=id, tournament=request.user.profile.tournament
        )

        form = AttendeePropertyForm(att, False, True, request.POST, request.FILES)

        if form.is_valid():

            form.save(request)

            return redirect("registration:overview")

        return render(
            request,
            "registration/attdata.html",
            context={"form": form, "attendee": att},
        )


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("registration.manage_data"), name="dispatch")
class EditTeamMemberData(TeamMgntPermMixin, View):

    def get(self, request, s_team, id):
        tournament = request.user.profile.tournament

        tm = get_object_or_404(
            TeamMember,
            id=id,
            team__origin__slug=s_team,
            team__tournament=request.user.profile.tournament,
        )

        att = tm.attendee

        form = AttendeePropertyForm(att, read_profile=False, hidden=False)

        return render(
            request,
            "registration/attdata.html",
            context={"form": form, "attendee": att},
        )

    def post(self, request, s_team, id):

        tournament = request.user.profile.tournament

        tm = get_object_or_404(
            TeamMember,
            id=id,
            team__origin__slug=s_team,
            team__tournament=request.user.profile.tournament,
        )

        att = tm.attendee

        form = AttendeePropertyForm(att, False, False, request.POST, request.FILES)

        if form.is_valid():

            form.save(request)

            return redirect("registration:team_overview", s_team)

        return render(
            request,
            "registration/attdata.html",
            context={"form": form, "attendee": att},
        )


@method_decorator(login_required, name="dispatch")
class TeamMemberDelete(TeamMgntPermMixin, ConfirmedDeleteView):

    def get_redirection(self, request, *args, **kwargs):
        return redirect("registration:team_overview", s_team=kwargs["s_team"])

    def get_objects(self, request, *args, **kwargs):
        tm = get_object_or_404(
            TeamMember,
            id=kwargs["id"],
            team__origin__slug=kwargs["s_team"],
            team__tournament=request.user.profile.tournament,
        )
        to_del = [tm]
        if tm.attendee.teammember_set.count() == 1 and set(
            tm.attendee.roles.all().values_list("id", flat=True)
        ) == set(tm.role.participation_roles.all().values_list("id", flat=True)):
            to_del.append(tm.attendee)
        return to_del

    def post(self, request, *args, **kwargs):
        redir = super().post(request, *args, **kwargs)
        try:
            tm = TeamMember.objects.get(
                id=kwargs["id"],
                team__origin__slug=kwargs["s_team"],
                team__tournament=request.user.profile.tournament,
            )
            delete_teamrole(tm)
        except:
            pass
        return redir


@method_decorator(login_required, name="dispatch")
class TeamMemberDecline(TeamMgntPermMixin, ConfirmedDeleteView):

    def get_redirection(self, request, *args, **kwargs):
        return redirect("registration:team_overview", s_team=kwargs["s_team"])

    def get_objects(self, request, *args, **kwargs):
        app = get_object_or_404(
            Application,
            id=kwargs["id"],
            team__origin__slug=kwargs["s_team"],
            tournament=request.user.profile.tournament,
        )
        to_del = [app]
        return to_del


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("registration.accept_role"), name="dispatch")
class RoleApplicationsList(ListView):

    template_name = "registration/list_role_applications.html"

    def get_queryset(self):
        trn = self.request.user.profile.tournament
        return Application.objects.filter(
            tournament=trn, origin__isnull=True, team__isnull=True
        )

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context["archive"] = Application.handled.filter(
            tournament=self.request.user.profile.tournament, handled_at__isnull=False
        ).order_by("-handled_at")
        context["roles"] = ParticipationRole.objects.filter(
            tournament=self.request.user.profile.tournament
        )
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("registration.accept_role"), name="dispatch")
class RoleApplicationQuestionDownload(View):

    def get(self, request, role_id):
        trn = request.user.profile.tournament
        role = get_object_or_404(ParticipationRole, tournament=trn, id=role_id)
        format = request.GET.get("format", "").lower()

        appls = Application.handled.filter(participation_role=role)
        if format == "xlsx":
            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = 'filename="data.xlsx"'

            workbook = xlsxwriter.Workbook(response)
            worksheet = workbook.add_worksheet()
            worksheet.write(0, 0, "First name")
            worksheet.write(0, 1, "Last name")
            worksheet.write(0, 2, "email")
            worksheet.write(0, 3, "status")
            for qi, q in enumerate(role.applicationquestion_set.all()):
                worksheet.write(0, 4 + qi, q.short_name)
            for row, a in enumerate(appls):
                worksheet.write(row + 1, 0, a.applicant.user.first_name)
                worksheet.write(row + 1, 1, a.applicant.user.last_name)
                worksheet.write(row + 1, 2, a.applicant.user.email)
                worksheet.write(row + 1, 3, a.handled_as)
                for qi, q in enumerate(role.applicationquestion_set.all()):
                    try:
                        worksheet.write(
                            row + 1,
                            4 + qi,
                            str(a.applicationquestionvalue_set.get(question=q)),
                        )
                    except:
                        pass
            workbook.close()

        else:  # format == 'json':
            response = HttpResponse(content_type="application/json")
            response["Content-Disposition"] = 'filename="data.json"'

            data = []
            for appl in Application.handled.filter(participation_role=role):
                appli = {}
                appli["id"] = appl.id
                appli["first_name"] = appl.applicant.user.first_name
                appli["last_name"] = appl.applicant.user.last_name
                appli["email"] = appl.applicant.user.email
                appli["handled_as"] = appl.handled_as
                appli["answers"] = []
                for ans in appl.applicationquestionvalue_set.all():
                    appli["answers"].append(
                        {
                            "question": {
                                "id": ans.question.id,
                                "name": ans.question.name,
                                "short_name": ans.question.short_name,
                            },
                            "answer": str(ans),
                        }
                    )
                data.append(appli)
            json.dump(data, response, cls=MyEncoder)

        return response


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("registration.accept_role"), name="dispatch")
class ApplicationFileView(ObjectDownloadView):
    attachment = False

    def get_object(self, queryset=None):
        try:
            obj = ApplicationQuestionValue.objects.get(
                id=self.kwargs["id"],
                application__tournament=self.request.user.profile.tournament,
            )
            file = getattr(obj, obj.field_name[obj.question.type])
            return file

        except Exception as e:
            raise AttendeePropertyValue.DoesNotExist("Image does not exist")


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("registration.accept_role"), name="dispatch")
class RoleApplicationsAccept(View):

    def get(self, request, id):

        view = False
        try:
            app = Application.objects.get(
                id=id, tournament=request.user.profile.tournament
            )
            form = AcceptRoleForm(app)
        except Application.DoesNotExist:
            try:
                app = Application.handled.get(
                    id=id,
                    tournament=self.request.user.profile.tournament,
                    handled_at__isnull=False,
                )
                form = forms.Form()
                view = True
            except:
                raise Http404("No matches the given query.")

        context = application_propertyvalues(
            app.tournament, app.participation_role, app.applicant
        )

        context["questions"] = app.applicationquestionvalue_set.all()
        context["view"] = view

        return render(
            request,
            "registration/accept_role_application.html",
            context={"form": form, **context},
        )

    def post(self, request, id):
        trn = request.user.profile.tournament

        app = get_object_or_404(Application, id=id, tournament=trn)

        form = AcceptRoleForm(app, request.POST)

        if form.is_valid():
            att = Attendee.objects.get_or_create(
                tournament=trn, active_user=app.applicant
            )[0]

            try:
                att.roles.add(form.cleaned_data["role"])
            except:
                pass

            for ap in AttendeeProperty.user_objects.filter(
                Q(tournament=trn), Q(apply_required=form.cleaned_data["role"])
            ):

                t = ap.user_property.type
                up = ap.user_property

                valueo = None
                valueo = UserPropertyValue.objects.filter(
                    user=app.applicant, property=up
                ).last()

                if valueo:
                    value = getattr(valueo, valueo.field_name[t])
                    update_property(
                        request,
                        ap,
                        None,
                        value,
                        "attendee-property-%d",
                        AttendeePropertyValue,
                        {"attendee": att, "author": request.user.profile},
                        copy_image=True,
                    )

            app.handled_as = Application.ACCEPTED
            app.handled_at = timezone.now()
            app.handled_by = request.user.profile.active
            app.save()

            if form.cleaned_data["notify"]:
                send_mail(
                    "Your application for %s with role %s was accepted"
                    % (app.tournament.name, app.participation_role.name),
                    "You now have the role %s in the tournament %s. \n Please make sure to select the correct active tournament unter Profile > Tournament"
                    % (app.participation_role.name, app.tournament.name),
                    settings.EMAIL_FROM,
                    [app.applicant.user.email],
                    fail_silently=False,
                )

            return redirect("registration:list_role_applications")

        return render(
            request, "registration/accept_role_application.html", context={"form": form}
        )


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("registration.accept_role"), name="dispatch")
class RoleApplicationsDecline(View):
    def get(self, request, id):

        app = get_object_or_404(
            Application, id=id, tournament=request.user.profile.tournament
        )

        form = DeclineRoleForm(app)

        return render(
            request,
            "registration/decline_role_application.html",
            context={"form": form},
        )

    def post(self, request, id):
        trn = request.user.profile.tournament

        app = get_object_or_404(Application, id=id, tournament=trn)

        form = DeclineRoleForm(app, request.POST)

        if form.is_valid():

            if form.cleaned_data["notify"]:
                send_mail(
                    "Your application for %s with role %s was declined"
                    % (app.tournament.name, app.participation_role.name),
                    "You do not have the role %s in the tournament %s because of: \n%s"
                    % (
                        app.participation_role.name,
                        app.tournament.name,
                        form.cleaned_data["decline_reason"],
                    ),
                    settings.EMAIL_FROM,
                    [app.applicant.user.email],
                    fail_silently=False,
                )

            app.handled_as = Application.DECLINED
            app.handled_at = timezone.now()
            app.handled_by = request.user.profile.active
            app.save()

            return redirect("registration:list_role_applications")

        return render(
            request,
            "registration/decline_role_application.html",
            context={"form": form},
        )


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("registration.accept_role"), name="dispatch")
class TeamApplicationsDecline(View):
    def get(self, request, id):

        app = get_object_or_404(
            Application, id=id, tournament=request.user.profile.tournament
        )

        form = DeclineTeamForm(app)

        return render(
            request,
            "registration/decline_role_application.html",
            context={"form": form},
        )

    def post(self, request, id):
        trn = request.user.profile.tournament

        app = get_object_or_404(Application, id=id, tournament=trn)

        form = DeclineTeamForm(app, request.POST)

        if form.is_valid():

            if form.cleaned_data["notify"]:
                send_mail(
                    "Your application for %s with team %s was declined"
                    % (app.tournament.name, app.origin.name),
                    "You do not manage the team %s in the tournament %s because of: \n %s"
                    % (
                        app.origin.name,
                        app.tournament.name,
                        form.cleaned_data["decline_reason"],
                    ),
                    settings.EMAIL_FROM,
                    [app.applicant.user.email],
                    fail_silently=False,
                )

            app.handled_as = Application.DECLINED
            app.handled_at = timezone.now()
            app.handled_by = request.user.profile.active
            app.save()

            return redirect("registration:list_role_applications")

        return render(
            request,
            "registration/decline_role_application.html",
            context={"form": form},
        )


@method_decorator(login_required, name="__call__")
@method_decorator(permission_required("registration.view_all_data"), name="dispatch")
class DataDownload(View):
    def get(self, request):
        trn = request.user.profile.tournament

        att, aps = persons_data(
            Attendee.objects.filter(tournament=trn).order_by(
                "active_user__user__last_name"
            ),
            hidden=True,
        )
        print(att)
        # print(att)
        print(aps)
        data = {"attendees": att, "properties": aps}
        format = request.GET.get("format", "").lower()

        if format == "xlsx":
            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = 'filename="data.xlsx"'

            workbook = xlsxwriter.Workbook(response)
            worksheet = workbook.add_worksheet()
            worksheet.write(0, 0, "First name")
            worksheet.write(0, 1, "Last name")
            worksheet.write(0, 2, "email")
            worksheet.write(0, 3, "Team")
            worksheet.write(0, 4, "Roles")
            for pi, p in enumerate(aps):
                worksheet.write(0, 5 + pi, p)
            for row, a in enumerate(att.values()):
                worksheet.write(row + 1, 0, a["attendee"].first_name)
                worksheet.write(row + 1, 1, a["attendee"].last_name)
                worksheet.write(row + 1, 2, a["attendee"].active_user.user.email)
                worksheet.write(
                    row + 1, 3, ", ".join(map(str, a["attendee"].team_set.all()))
                )
                worksheet.write(
                    row + 1, 4, ", ".join(map(str, a["attendee"].roles.all()))
                )
                for vi, v in enumerate(a["data"]):
                    worksheet.write(row + 1, vi + 5, v["value"])
            workbook.close()

        else:  # format == 'json':
            response = HttpResponse(content_type="application/json")
            response["Content-Disposition"] = 'filename="data.json"'
            json.dump(data, response, cls=MyEncoder)

        return response
