from django import forms
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import slugify
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.text import capfirst
from django_downloadview import ObjectDownloadView
from django_select2.forms import Select2MultipleWidget, Select2Widget
from formtools.preview import FormPreview
from unidecode import unidecode

from apps.account.models import ActiveUser, Attendee, ParticipationRole
from apps.dashboard.forms import ModelDeleteListField
from apps.dashboard.messages import Message
from apps.jury.models import Juror, JurorRole, PossibleJuror
from apps.plan.models import (
    Fight,
    FightRole,
    Room,
    Round,
    Stage,
    StageAttendance,
    TeamPlaceholder,
)
from apps.printer import context_generator
from apps.printer.models import Pdf, PdfTag, Template
from apps.printer.tasks import render_to_pdf
from apps.printer.utils import _get_next_pdfname
from apps.registration.models import AttendeeProperty
from apps.registration.utils import assign_teammanager
from apps.result.utils import _ranking
from apps.team.models import Team, TeamMember, TeamRole
from apps.tournament.models import (
    Origin,
    ScheduleTemplate,
    TemplateAttendance,
    TemplateFight,
    TemplateRoom,
    TemplateRound,
)
from apps.tournament.utils import (
    _is_superior_user,
    _more_perm_than_group,
    _more_perm_than_role,
)

from .utils import _normal_capitalisation


@method_decorator(login_required, name="__call__")
@method_decorator(permission_required("plan.import_curiie"), name="__call__")
class CuriiePreview(FormPreview):

    form_template = "plan/curiie.html"
    preview_template = "plan/curiiePreview.html"

    def _dissect_currie(self, tournament, csv, default):
        lines = csv.split("\n")

        teams = {}

        teams[default] = {"m": [], "t": [], "name": default, "miss": []}

        jurors = {}

        spellct = []

        for line in lines:
            line = line.strip()

            # ignore comments
            if len(line) > 0:
                if line[0] == "#":
                    continue

            f = line.split(";")
            # print(f)
            if len(f) >= 4:
                orig = f[3].strip()
                if orig == "None" or orig == "":
                    orig = default
                name = "%s %s" % (f[0], f[1])
                slug = "%s-%s-%s" % (
                    tournament.slug,
                    slugify(orig),
                    slugify(unidecode(name)),
                )
                cap = _normal_capitalisation(name)
                attend = False
                user = False

                try:
                    att = Attendee.objects.get(
                        active_user__user__username=slug, tournament=tournament
                    )
                    attend = True
                except Exception as e:
                    pass

                try:
                    us = ActiveUser.objects.get(active_user__user__username=slug)
                    user = True
                except:
                    pass

                if orig not in teams and orig != "None":
                    teams[orig] = {"m": [], "t": [], "name": orig, "miss": []}
                if f[2].lower() == "m":
                    teams[orig]["m"].append((name, cap, attend, user, slug, f[0], f[1]))
                if f[2].lower() == "t" or f[2].lower() == "l":
                    teams[orig]["t"].append((name, cap, attend, user, slug, f[0], f[1]))

                if f[2].lower() == "i":
                    j = {
                        "name": name,
                        "lastname": f[1],
                        "firstname": f[0],
                        "list": [[default, False]],
                        "loc": True,
                        "slug": slug,
                    }

                    j["spelling"] = _normal_capitalisation(j["name"])
                    j["attendee"] = attend
                    j["user"] = user

                    if orig != default:
                        j["list"] = [[orig, False]]
                        j["loc"] = False

                    jurors["%s %s" % (f[0], f[1])] = j

        maxTn = len(max(teams.values(), key=lambda x: len(x["m"]))["m"])
        for t in teams:
            if len(teams[t]["m"]) < maxTn:
                teams[t]["miss"] = range(maxTn - len(teams[t]["m"]))
            if len(teams[t]["m"]) == 0:
                spellct.append(t)

        for j in jurors:
            for c in jurors[j]["list"]:
                if c[0] in spellct:
                    c[1] = True

        return (teams, jurors)

    def _create_attendee(self, username, first_name, last_name, tournament):

        user = None
        try:
            user = User.objects.create_user(
                username, first_name=first_name, last_name=last_name
            )
        except:
            user = User.objects.get(username=username)

        auser = ActiveUser.objects.get_or_create(user=user)[0]

        attendee = Attendee.objects.get_or_create(
            active_user=auser, tournament=tournament
        )[0]

        return attendee

    def done(self, request, cleaned_data):
        # Do something with the cleaned_data, then redirect
        # to a "success" page.
        trn = request.user.profile.tournament
        (teams, jurors) = self._dissect_currie(
            trn, cleaned_data["input"], cleaned_data["default"]
        )

        memr, cre = TeamRole.objects.get_or_create(tournament=trn, type=TeamRole.MEMBER)
        leadr, cre = TeamRole.objects.get_or_create(
            tournament=trn, type=TeamRole.LEADER
        )

        prstudent, cre = ParticipationRole.objects.get_or_create(
            tournament=trn, type=ParticipationRole.STUDENT
        )
        prjuror, cre = ParticipationRole.objects.get_or_create(
            tournament=trn, type=ParticipationRole.JUROR
        )

        for t in teams:
            origin, cre = Origin.objects.get_or_create(name=t, tournament=trn)

            team, cre = Team.objects.get_or_create(origin=origin, tournament=trn)

            for me in teams[t]["m"]:
                attnd = self._create_attendee(me[4], me[5], me[6], trn)
                TeamMember.objects.get_or_create(attendee=attnd, team=team, role=memr)
                attnd.roles.add(prstudent)

            for tl in teams[t]["t"]:
                attnd = self._create_attendee(tl[4], tl[5], tl[6], trn)
                TeamMember.objects.get_or_create(attendee=attnd, team=team, role=leadr)
                attnd.roles.add(prjuror)

                ju = Juror.objects.get_or_create(attendee=attnd)[0]
                if not ju.conflicting.filter(pk=origin.pk).exists():
                    ju.conflicting.add(origin)
                    ju.save()

                for r in Round.selectives.filter(tournament=trn):
                    ju.availability.add(r)

        for j in jurors:
            att = self._create_attendee(
                jurors[j]["slug"], jurors[j]["firstname"], jurors[j]["lastname"], trn
            )

            att.roles.add(prjuror)

            ju = Juror.objects.get_or_create(attendee=att)[0]

            ju.experience = Juror.EXPERIENCE_HIGH

            for ori in jurors[j]["list"]:
                ori = Origin.objects.get(name=ori[0], tournament=trn)
                if not ju.conflicting.filter(pk=ori.pk).exists():
                    ju.conflicting.add(ori)
            # ju.save()

            if not jurors[j]["loc"]:
                for r in Round.selectives.filter(tournament=trn):
                    ju.availability.add(r)
            else:
                ju.local = True

            ju.save()

        return redirect("plan:persons")

    def process_preview(self, request, form, context):

        (teams, jurors) = self._dissect_currie(
            request.user.profile.tournament,
            form.cleaned_data["input"],
            form.cleaned_data["default"],
        )

        context["teams"] = sorted(teams.values(), key=lambda x: x["name"])
        context["jurors"] = sorted(jurors.values(), key=lambda x: x["lastname"])
        context["default_c"] = form.cleaned_data["default"]


@method_decorator(login_required, name="__call__")
@method_decorator(permission_required("account.view_all_persons"), name="__call__")
class PersonsPreview(FormPreview):

    form_template = "plan/persons.html"
    preview_template = "dashboard/previewObjsDelete.html"

    def parse_params(self, request):
        trn = request.user.profile.tournament

        self.filters = [
            {
                "name": "Roles",
                "filter": "roles__in",
                "elements": trn.participationrole_set.all(),
            },
            {"name": "Groups", "elements": trn.groups.all(), "filter": "groups__in"},
            {"name": "Team", "elements": trn.team_set.all(), "filter": "team__in"},
        ]

        self._filters = {}
        self._excludes = {}

        for fname in [x["filter"] for x in self.filters]:
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

        person = ModelDeleteListField(
            queryset=Attendee.objects.filter(tournament=trn, **self._filters)
            .exclude(ex_query)
            .distinct()
            .order_by("active_user__user__last_name")
            .prefetch_related(
                "roles", "groups", "active_user__user", "teammember_set__team__origin"
            )
        )

        allowedros = [
            r.id
            for r in trn.participationrole_set.all()
            if _more_perm_than_role(request.user, r)
        ]

        roles = forms.ModelMultipleChoiceField(
            queryset=ParticipationRole.objects.filter(id__in=allowedros),
            required=False,
            widget=Select2MultipleWidget(),
        )

        allowedgrs = [
            gr.id for gr in trn.groups.all() if _more_perm_than_group(request.user, gr)
        ]

        groups = forms.ModelMultipleChoiceField(
            queryset=Group.objects.filter(id__in=allowedgrs),
            required=False,
            widget=Select2MultipleWidget(),
        )

        team = forms.ModelChoiceField(
            queryset=Team.objects.filter(tournament=trn),
            required=False,
            widget=Select2Widget(),
        )

        origin = forms.ModelChoiceField(
            queryset=Origin.objects.filter(tournament=trn),
            required=False,
            widget=Select2Widget(),
        )

        template = forms.ModelChoiceField(
            queryset=trn.template_set.filter(type=Template.PERSONS),
            required=False,
            widget=Select2Widget(),
        )

        conflicting = forms.ModelChoiceField(
            queryset=trn.attendeeproperty_set.filter(
                type=AttendeeProperty.CONFLICT_ORIGINS
            ),
            required=False,
            widget=Select2Widget,
        )

        self.form = type(
            "PersonsForm",
            (forms.Form,),
            {
                "persons": person,
                "roles": roles,
                "groups": groups,
                "template": template,
                "team": team,
                "conflicting": conflicting,
                "origin": origin,
            },
        )

    def get_context(self, request, form):

        trn = request.user.profile.tournament

        filters = []

        for fil in self.filters:
            f = {
                "name": fil["name"],
                "elements": fil["elements"],
                "link_name": fil["filter"],
            }

            # f['active'] = self.filter.get(f['link_name'], None)

            filter_rest = "&".join(
                [
                    "&".join(["in_%s=%s" % (f, g) for g in self._filters[f]])
                    for f in self._filters
                    if f != fil["filter"]
                ]
            )

            exclude_rest = "&".join(
                [
                    "&".join(["ex_%s=%s" % (f, g) for g in self._excludes[f]])
                    for f in self._excludes
                    if f != fil["filter"]
                ]
            )

            f["link_rest"] = "&".join([filter_rest, exclude_rest])

            f["in_actives"] = self._filters.get(fil["filter"], [])
            f["ex_actives"] = self._excludes.get(fil["filter"], [])

            filters.append(f)

        return {
            "filters": filters,
            "form": form,
            "stage_field": self.unused_name("stage"),
            "state": self.state,
        }

    def process_preview(self, request, form, context):

        trn = request.user.profile.tournament

        if "_delete" in request.POST:
            self.preview_template = "dashboard/previewObjsDelete.html"

            context["action"] = "_delete"

            def format_callback(obj):
                return "%s: %s" % (capfirst(obj._meta.verbose_name), obj)

            ps = form.cleaned_data["persons"]
            if ps.filter(active_user=request.user.profile).exists():
                context["warning"] = "You are deleteing yourself from the tournament!"
            ps = [p for p in ps if _is_superior_user(request.user, p)]
            collector = NestedObjects(using="default")  # or specific database
            collector.collect(ps)
            to_delete = collector.nested(format_callback)

            context["objs"] = to_delete

        elif "_juror" in request.POST:

            self.preview_template = "plan/jurorCreatePreview.html"

            jurors = []
            news = form.cleaned_data["persons"]

            conflict_field = form.cleaned_data["conflicting"]

            for new in news:
                ori = ""
                try:
                    ori = new.teammember_set.first().team.origin
                except:
                    pass

                if conflict_field:
                    try:
                        apv = new.attendeepropertyvalue_set.filter(
                            property=conflict_field
                        ).last()
                        conflicting = set(apv.conflict_origins.all()) | {ori}
                    except:
                        conflicting = {ori}
                else:
                    conflicting = {ori}

                if Juror.objects.filter(attendee=new).exists():
                    old_confl = set(Juror.objects.get(attendee=new).conflicting.all())

                    jurors.append(
                        {
                            "new": False,
                            "name": new.full_name,
                            "conflicting": list(old_confl | conflicting),
                            "origin": ori,
                            "experience": Juror.objects.get(attendee=new).experience,
                        }
                    )
                else:
                    try:
                        pj = new.active_user.possiblejuror_set.get(
                            tournament=trn, approved_by__isnull=False
                        )
                        exp = pj.experience
                    except:
                        exp = Juror.EXPERIENCE_LOW
                        pass

                    jurors.append(
                        {
                            "new": True,
                            "name": new.full_name,
                            "origin": ori,
                            "conflicting": list(conflicting),
                            "experience": exp,
                        }
                    )

            context["jurors"] = jurors
            context["action"] = "_juror"

        else:

            self.preview_template = "plan/personAssignPreview.html"

            persons = []

            for att in form.cleaned_data["persons"].prefetch_related(
                "active_user__user",
            ):
                person = {
                    "full_name": att.full_name,
                    "roles": list(map(lambda x: x["name"], att.roles.values("name"))),
                    "groups": list(map(lambda x: x["name"], att.groups.values("name"))),
                    "superior": _is_superior_user(request.user, att),
                }

                person["teams"] = att.team_set.all().prefetch_related("origin")

                if "_add_roles" in request.POST:
                    context["action"] = "_add_roles"
                    newroles = form.cleaned_data["roles"]
                    person["roles_new"] = []
                    for newrole in newroles:
                        if newrole.name not in person["roles"]:
                            person["roles_new"].append(newrole)

                if "_del_roles" in request.POST:
                    context["action"] = "_del_roles"
                    delroles = form.cleaned_data["roles"]
                    person["roles_del"] = []
                    person["roles_del_na"] = []
                    if person["superior"]:
                        for delrole in delroles:
                            if delrole.name in person["roles"]:
                                person["roles"].remove(delrole.name)
                                person["roles_del"].append(delrole.name)
                            else:
                                person["roles_del_na"].append(delrole.name)

                if "_add_groups" in request.POST:
                    context["action"] = "_add_groups"
                    news = form.cleaned_data["groups"]
                    # TODO: check that you can only assign permissions you already have
                    person["groups_new"] = []
                    for new in news:
                        if new.name not in person["groups"]:
                            person["groups_new"].append(new)

                if "_del_groups" in request.POST:
                    context["action"] = "_del_groups"
                    deles = form.cleaned_data["groups"]
                    person["groups_del"] = []
                    person["groups_del_na"] = []
                    if person["superior"]:
                        for dele in deles:
                            if dele.name in person["groups"]:
                                person["groups"].remove(dele.name)
                                person["groups_del"].append(dele.name)
                            else:
                                person["groups_del_na"].append(dele.name)

                if "_print" in request.POST:
                    context["action"] = "_print"

                if "_team" in request.POST:
                    context["action"] = "_team"
                    team = form.cleaned_data["team"]
                    person["team_new"] = None
                    if team not in person["teams"]:
                        person["team_new"] = team

                if "_manager" in request.POST:
                    context["action"] = "_manager"
                    origin = form.cleaned_data["origin"]
                    person["team_new"] = None
                    if origin not in person["teams"]:
                        person["team_new"] = origin

                persons.append(person)

            context["persons"] = persons

    @method_decorator(permission_required("account.change_attendee"))
    def done(self, request, cleaned_data):

        ps = cleaned_data["persons"]

        if "action" not in request.POST:
            ps.model.objects.filter(id__in=ps.values("id")).delete()

        elif request.POST["action"] == "_add_roles":
            news = cleaned_data["roles"]
            for att in ps:
                att.roles.add(*news)
        elif request.POST["action"] == "_del_roles":
            news = cleaned_data["roles"]
            for att in ps:
                if _is_superior_user(request.user, att):
                    att.roles.remove(*news)

        elif request.POST["action"] == "_add_groups":
            news = cleaned_data["groups"]
            for att in ps:
                # TODO: only add if you have perm yourself
                att.groups.add(*news)
        elif request.POST["action"] == "_del_groups":
            news = cleaned_data["groups"]
            for att in ps:
                if _is_superior_user(request.user, att):
                    att.groups.remove(*news)

        elif request.POST["action"] == "_team":
            assorole = TeamRole.objects.get(
                tournament=request.user.profile.tournament, type=TeamRole.ASSOCIATED
            )
            for att in ps:
                if not TeamMember.objects.filter(
                    team=cleaned_data["team"], attendee=att
                ).exists():
                    TeamMember.objects.create(
                        team=cleaned_data["team"], attendee=att, role=assorole
                    )

        elif request.POST["action"] == "_manager":
            for att in ps:
                assign_teammanager(cleaned_data["origin"], att)

        elif request.POST["action"] == "_print":
            trn = request.user.profile.tournament
            template = cleaned_data["template"]

            context = context_generator.persons(ps)

            fileprefix = "persons-%s-v" % slugify(template.name)

            pdf = Pdf.objects.create(
                name="%s%d" % (fileprefix, _get_next_pdfname(trn, fileprefix)),
                tournament=trn,
            )

            res = render_to_pdf.delay(template.id, pdf.id, context=context)

            pdf.task_id = res.id
            pdf.save()

            pdf.tags.add(PdfTag.objects.get(tournament=trn, type=Template.PERSONS))

        elif request.POST["action"] == "_juror":

            conflict_field = cleaned_data["conflicting"]

            for att in ps:

                ju, cre = Juror.objects.get_or_create(attendee=att)

                if cre:

                    try:
                        # TODO: hat if member of 2 teams
                        ori = {att.teammember_set.first().team.origin}
                    except:
                        ori = set()

                    if conflict_field:
                        try:
                            apv = att.attendeepropertyvalue_set.filter(
                                property=conflict_field
                            ).last()
                            conflicting = set(apv.conflict_origins.all()) | ori
                        except:
                            conflicting = ori
                    else:
                        conflicting = ori

                    ju.conflicting.set(conflicting)

                    try:
                        pj = att.active_user.possiblejuror_set.get(
                            tournament=att.tournament, approved_by__isnull=False
                        )
                        exp = pj.experience
                    except:
                        exp = Juror.EXPERIENCE_LOW

                    ju.experience = exp
                    ju.save()
                pj, cre = PossibleJuror.objects.get_or_create(
                    person=att.active_user, tournament=att.tournament
                )
                if cre:
                    pj.approved_by = request.user.profile
                    pj.approved_at = timezone.now()
                    pj.save()

        return redirect("plan:persons")


@method_decorator(login_required, name="__call__")
@method_decorator(permission_required("team.view_teams"), name="__call__")
class TeamsPreview(FormPreview):

    form_template = "plan/teams.html"
    preview_template = "dashboard/previewObjsDelete.html"

    def parse_params(self, request):
        trn = request.user.profile.tournament
        memvars = {}
        memvars["teams"] = ModelDeleteListField(
            queryset=Team.objects.filter(tournament=trn).prefetch_related(
                "teammember_set", "origin"
            )
        )

        if trn.aypt_limited_problems:
            memvars["problems"] = forms.ModelMultipleChoiceField(
                queryset=trn.problem_set.all(),
                widget=Select2MultipleWidget(),
                required=False,
            )
            memvars["prepared_problem"] = forms.ModelChoiceField(
                queryset=trn.attendeeproperty_set.filter(type=AttendeeProperty.PROBLEM),
                required=False,
                widget=Select2Widget,
            )

        memvars["space"] = forms.CharField(required=False)
        memvars["template"] = forms.ModelChoiceField(
            queryset=trn.template_set.filter(type=Template.TEAM),
            required=False,
            widget=Select2Widget(),
        )

        self.form = type("TeamsForm", (forms.Form,), memvars)

    def get_context(self, request, form):
        context = {
            "form": form,
            "stage_field": self.unused_name("stage"),
            "state": self.state,
        }
        if request.user.profile.tournament.aypt_limited_problems:
            context["problems"] = True
        return context

    def process_preview(self, request, form, context):

        if "_delete" in request.POST:

            def format_callback(obj):
                return "%s: %s" % (capfirst(obj._meta.verbose_name), obj)

            ps = form.cleaned_data["teams"]
            collector = NestedObjects(using="default")  # or specific database
            collector.collect(ps)
            to_delete = collector.nested(format_callback)

            context["objs"] = to_delete

        elif "_competing" in request.POST:

            self.preview_template = "plan/teamCompetePreview.html"

            teams = []
            nt = form.cleaned_data["teams"]

            for t in nt:

                teams.append({"name": t.origin.name, "competing": not t.is_competing})

            context["teams"] = teams
            context["action"] = "_competing"

        elif "_space" in request.POST:

            self.preview_template = "plan/teamCompetePreview.html"

            teams = []
            nt = form.cleaned_data["teams"]
            for t in nt:
                teams.append({"name": t.origin.name, "competing": t.is_competing})

            context["teams"] = teams
            context["action"] = "_space"

        elif "_print" in request.POST:
            self.preview_template = "plan/teamCompetePreview.html"

            teams = []
            nt = form.cleaned_data["teams"]

            for t in nt:
                teams.append({"name": t.origin.name, "competing": t.is_competing})

            context["teams"] = teams
            context["action"] = "_print"

        elif (
            "_problems" in request.POST
            and request.user.profile.tournament.aypt_limited_problems
        ):

            self.preview_template = "plan/teamCompetePreview.html"

            teams = []
            nt = form.cleaned_data["teams"]
            problems = form.cleaned_data["problems"]

            for t in nt:

                teams.append(
                    {
                        "name": t.origin.name,
                        "problems": problems,
                        "competing": t.is_competing,
                    }
                )

            context["teams"] = teams
            context["action"] = "_problems"

        elif (
            "_prepared" in request.POST
            and request.user.profile.tournament.aypt_limited_problems
        ):

            self.preview_template = "plan/teamCompetePreview.html"

            teams = []
            nt = form.cleaned_data["teams"]
            ap: AttendeeProperty = form.cleaned_data["prepared_problem"]
            trn = request.user.profile.tournament

            t: Team
            for t in nt:
                print("preview team", t)
                delp = t.aypt_prepared_problems.all()
                pr_nums = []
                for tm in t.members.all():
                    try:
                        pr_nums.append(
                            ap.attendeepropertyvalue_set.filter(attendee=tm)
                            .last()
                            .int_value
                        )
                    except:
                        pass
                problems = trn.problem_set.filter(number__in=pr_nums)
                print("problems:", problems)
                teams.append(
                    {
                        "name": t.origin.name,
                        "problems": problems,
                        "del_problems": delp,
                        "competing": t.is_competing,
                    }
                )

            context["teams"] = teams
            context["action"] = "_prepared"

    def done(self, request, cleaned_data):

        ps = cleaned_data["teams"]

        if "action" not in request.POST:
            if request.user.has_perm("team.delete_team"):
                ps.model.objects.filter(id__in=ps.values("id")).delete()

        elif request.POST["action"] == "_competing":
            nt = cleaned_data["teams"]
            for t in nt:
                t.is_competing = not t.is_competing
                t.save()

        elif request.POST["action"] == "_space":
            nt = cleaned_data["teams"]
            for t in nt:
                t.storage_link = cleaned_data["space"]
                t.save()

        elif request.POST["action"] == "_print":
            trn = request.user.profile.tournament
            template = cleaned_data["template"]

            context = context_generator.teams(ps)

            fileprefix = "teams-%s-v" % slugify(template.name)

            pdf = Pdf.objects.create(
                name="%s%d" % (fileprefix, _get_next_pdfname(trn, fileprefix)),
                tournament=trn,
            )

            res = render_to_pdf.delay(template.id, pdf.id, context=context)

            pdf.task_id = res.id
            pdf.save()

            pdf.tags.add(PdfTag.objects.get(tournament=trn, type=Template.TEAM))

        elif (
            request.POST["action"] == "_problems"
            and request.user.profile.tournament.aypt_limited_problems
        ):
            nt = cleaned_data["teams"]
            problems = cleaned_data["problems"]
            t: Team
            for t in nt:
                for p in t.aypt_prepared_problems.all():
                    if p not in problems:
                        t.aypt_prepared_problems.remove(p)
                t.aypt_prepared_problems.add(*problems)

        elif (
            request.POST["action"] == "_prepared"
            and request.user.profile.tournament.aypt_limited_problems
        ):
            nt = cleaned_data["teams"]
            ap: AttendeeProperty = cleaned_data["prepared_problem"]
            trn = request.user.profile.tournament
            t: Team
            for t in nt:
                t.aypt_prepared_problems.clear()

                pr_nums = []
                for tm in t.members.all():
                    try:
                        pr_nums.append(
                            ap.attendeepropertyvalue_set.filter(attendee=tm)
                            .last()
                            .int_value
                        )
                    except:
                        pass
                problems = trn.problem_set.filter(number__in=pr_nums)
                t.aypt_prepared_problems.add(*problems)
        return redirect("plan:teams")


@method_decorator(login_required, name="__call__")
@method_decorator(permission_required("plan.change_fight"), name="__call__")
class RoundPreview(FormPreview):

    form_template = "plan/round.html"
    preview_template = "plan/roundPreview.html"

    def parse_params(self, request, round_nr):

        trn = request.user.profile.tournament
        ro = get_object_or_404(Round, tournament=trn, order=round_nr)

        fields = {}
        for fight in ro.fight_set.all():
            st = fight.stage_set.first()
            for role in FightRole.ROLE_TYPE:
                initial = None
                try:
                    att = st.stageattendance_set.get(role__type=role[0])
                    initial = att.team_placeholder
                except Exception as e:
                    pass

                required = True
                if role[0] == "obs":
                    required = False
                f = forms.ModelChoiceField(
                    queryset=TeamPlaceholder.objects.filter(tournament=trn),
                    widget=forms.TextInput(),
                    initial=initial,
                    required=required,
                )
                fields["fight-%d-%s" % (fight.pk, role[0])] = f

        fields["tp"] = TeamPlaceholder.objects.filter(tournament=trn)

        def clean(self):
            cleaned_data = super(self.__class__, self).clean()

            all = set(map(lambda x: x["pk"], self.tp.values("pk")))

            new = []
            for k in cleaned_data:
                if cleaned_data[k]:
                    new.append(cleaned_data[k].pk)

            news = set(new)

            if len(new) != len(all):
                raise forms.ValidationError(
                    "The number of teams should match all the placeholder teams."
                )

            if news != all:
                raise forms.ValidationError("All teams must participate exactly once.")

        fields["clean"] = clean

        self.form = type("RoundForm", (forms.Form,), fields)

        self.round = ro

    def process_preview(self, request, form, context):

        fights = []
        for fi in self.round.fight_set.all():

            fight = {"room": fi.room.name, "roles": []}
            for role in FightRole.ROLE_TYPE:
                if form.cleaned_data["fight-%d-%s" % (fi.pk, role[0])]:
                    fight["roles"].append(
                        (role[1], form.cleaned_data["fight-%d-%s" % (fi.pk, role[0])])
                    )
            fights.append(fight)

        context["fights"] = fights
        context["round"] = self.round.order

        # check if Stage attendances can be safely deleted

        sas = StageAttendance.objects.filter(stage__fight__round=self.round)

    @method_decorator(transaction.atomic)
    def done(self, request, cleaned_data):

        return redirect("plan:placeholder")


@method_decorator(login_required, name="__call__")
@method_decorator(permission_required("plan.add_round"), name="__call__")
class TemplatePreview(FormPreview):

    form_template = "plan/template.html"
    preview_template = "plan/templatePreview.html"

    def parse_params(self, request, template_id):

        fields = {}

        rooms = TemplateRoom.objects.filter(template=template_id)
        for room in rooms:
            fields["room-%d" % (room.id,)] = forms.CharField(
                max_length=30,
                initial=room.name,
                label="Room %s (capacity %d)" % (room.name, room.capacity()),
            )

        self.form = type("TeamsForm", (forms.Form,), fields)

        self.template = ScheduleTemplate.objects.get(pk=template_id)

    def process_preview(self, request, form, context):

        phteams = TeamPlaceholder.objects.filter(
            tournament=request.user.profile.tournament
        )
        tpteams = list(
            sorted(
                list(
                    set(
                        TemplateAttendance.objects.filter(
                            fight__round__template=self.template
                        ).values_list("team", flat=True)
                    )
                )
            )
        )

        context["rounds"] = []
        for round in TemplateRound.objects.filter(template=self.template):
            ro = {"order": round.order, "fights": []}

            for fight in round.fights.all():
                fi = {"room": form.cleaned_data["room-%d" % (fight.room_id)], "att": []}

                for att in fight.templateattendance_set.all():
                    role = {
                        "role": att.get_type_display(),
                        "team": phteams[tpteams.index(att.team)],
                    }
                    fi["att"].append(role)

                ro["fights"].append(fi)

            ro["fights"] = sorted(ro["fights"], key=lambda x: x["room"])
            context["rounds"].append(ro)

    @method_decorator(permission_required("plan.add_round"))
    @method_decorator(transaction.atomic)
    def done(self, request, cleaned_data):

        trn = request.user.profile.tournament

        phteams = TeamPlaceholder.objects.filter(tournament=trn)

        msg = []
        if Round.objects.filter(tournament=trn).exists():
            msg = [Message(subject="Plan not empty", level_tag="error")]

        elif self.template.teams_nr() != phteams.count():
            msg = [Message(subject="Number of teams not matching", level_tag="error")]

        if len(msg) != 0:
            rounds = Round.selectives.filter(tournament=trn).order_by("order")
            scheds = ScheduleTemplate.objects.all()
            return render(
                request,
                "plan/overview.html",
                context={"rounds": rounds, "schedules": scheds, "messages": msg},
            )

        tpteams = list(
            sorted(
                list(
                    set(
                        TemplateAttendance.objects.filter(
                            fight__round__template=self.template
                        ).values_list("team", flat=True)
                    )
                )
            )
        )

        for round in TemplateRound.objects.filter(template=self.template):

            ro = Round.objects.create(
                tournament=trn, order=round.order, type=Round.SELECTIVE
            )

            for fight in round.fights.all():
                room = Room.objects.get_or_create(
                    tournament=trn, name=cleaned_data["room-%d" % (fight.room_id)]
                )[0]
                room.save()
                fi = Fight.objects.create(round=ro, room=room)

                tplat = list(fight.templateattendance_set.all())
                roleorder = tplat
                for i in range(len(tplat)):
                    st = Stage.objects.create(order=i + 1, fight=fi)
                    for idx, att in enumerate(tplat):
                        role = FightRole.objects.get(
                            tournament=trn, type=roleorder[idx].type
                        )
                        StageAttendance.objects.create(
                            stage=st,
                            team_placeholder=phteams[tpteams.index(att.team)],
                            role=role,
                        )
                    tplat = tplat[1:] + tplat[:1]

        Round.objects.create(
            tournament=trn,
            order=TemplateRound.objects.filter(template=self.template).count() + 1,
            type=Round.FINAL,
        )

        return redirect("plan:placeholder")


@method_decorator(login_required, name="__call__")
@method_decorator(permission_required("plan.change_final"), name="__call__")
class FinalPreview(FormPreview):

    form_template = "plan/final.html"
    preview_template = "plan/finalPreview.html"

    def parse_params(self, request):

        self.trn = request.user.profile.tournament

        rounds = Round.selectives.filter(tournament=self.trn).order_by("order")

        if rounds.count() == 0:
            return None

        self.fr = Round.finals.get(tournament=self.trn)

        if not self.fr.fight_set.exists():

            self.rank = _ranking(rounds, use_cache=False, internal=True)

            fields = {}
            best_all_won = True
            for team in self.rank[-1]:
                f = forms.ChoiceField(
                    choices=(("", "----"), (1, 1), (2, 2), (3, 3), (4, 4)),
                    required=False,
                )
                if team["rank"] <= 3:
                    f.initial = team["rank"]
                elif team["all_won"] and best_all_won:
                    f.initial = 4
                    best_all_won = False

                fields["team-%d" % team["pk"]] = f

            fields["ranking"] = self.rank[-1]
            fields["rounds"] = rounds

            def teams(self):
                return [
                    (self.__getitem__("team-%d" % team["pk"]), team)
                    for team in self.ranking
                ]

            def get_rounds(self):
                return self.rounds.values_list("order", flat=True)

            fields["get_teams"] = teams
            fields["get_rounds"] = get_rounds

            self.form = type("FinalForm", (forms.Form,), fields)
        else:

            self.form = type("FinalForm", (forms.Form,), {})

    def process_preview(self, request, form, context):

        teams = [None, None, None, None]
        # roles=[FightRole.REP,FightRole.OPP,FightRole.REV,FightRole.OBS]
        roles = ["Reporter", "Opponent", "Reviewer", "Observer"]
        for t in form.ranking:
            pos = form.cleaned_data["team-%d" % t["pk"]]
            if pos:
                teams[int(pos) - 1] = t

        if not teams[3]:
            teams = teams[:3]
            roles = roles[:3]

        teams = list(reversed(teams))

        stages = []
        for i in range(len(teams)):
            stage = []
            for idx, t in enumerate(teams):
                stage.append((t, roles[idx]))
            teams = teams[1:] + teams[:1]

            stages.append(stage)

        context["stages"] = stages

    @method_decorator(transaction.atomic)
    def done(self, request, cleaned_data):
        if not self.fr.fight_set.exists():

            teams = [None, None, None, None]
            roles = [FightRole.REP, FightRole.OPP, FightRole.REV, FightRole.OBS]
            # roles = ["Reporter", "Opponent", "Reviewer", "Observer"]
            for t in self.rank[-1]:
                pos = cleaned_data["team-%d" % t["pk"]]
                if pos:
                    teams[int(pos) - 1] = get_object_or_404(Team, pk=t["pk"])

            if not teams[3]:
                teams = teams[:3]
                roles = roles[:3]

            teams = list(reversed(teams))
            room = Room.objects.filter(tournament=self.trn)[0]
            fi = Fight.objects.create(round=self.fr, room=room)

            for i in range(len(teams)):
                st = Stage.objects.create(fight=fi, order=i + 1)

                for idx, t in enumerate(teams):
                    StageAttendance.objects.create(
                        stage=st,
                        team=t,
                        role=FightRole.objects.get(
                            tournament=self.trn, type=roles[idx]
                        ),
                    )
                teams = teams[1:] + teams[:1]

        return redirect("jury:edit_round", round=self.fr.order)
