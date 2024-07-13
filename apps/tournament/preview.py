from django import forms
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django_select2.forms import Select2Widget
from formtools.preview import FormPreview

from apps.account.models import ActiveUser
from apps.jury.models import JurorOccupation
from apps.registration.models import ApplicationQuestion, AttendeeProperty
from apps.team.models import TeamRole
from apps.tournament.models import Problem, Tournament


@method_decorator(login_required, name="__call__")
@method_decorator(permission_required("tournament.add_problem"), name="__call__")
class ProblemImportPreview(FormPreview):

    form_template = "tournament/problemImport.html"
    preview_template = "tournament/problem_preview.html"

    def process_preview(self, request, form, context):

        problems = []

        data = form.cleaned_data["input"]
        for line in data.split("\n"):
            problem = {}
            parts = line.split(";")
            problem["number"] = int(parts[0])
            problem["title"] = parts[1]
            problem["description"] = ";".join(parts[2:])
            prob = Problem.objects.filter(
                tournament=request.user.profile.tournament, number=int(parts[0])
            )
            if prob.exists():
                problem["exists"] = True
            problems.append(problem)

        context["problems"] = problems

    def done(self, request, cleaned_data):

        data = cleaned_data["input"]
        for line in data.split("\n"):
            parts = line.split(";")
            prob = Problem.objects.filter(
                tournament=request.user.profile.tournament, number=int(parts[0])
            )
            if prob.exists():
                prob = prob.get()
                prob.title = parts[1]
                prob.description = ";".join(parts[2:])
                prob.save()
            else:
                Problem.objects.create(
                    tournament=request.user.profile.tournament,
                    number=int(parts[0]),
                    title=parts[1],
                    description=";".join(parts[2:]),
                )

        return redirect("tournament:problems")


@method_decorator(login_required, name="__call__")
@method_decorator(permission_required("tournament.add_origin"), name="__call__")
class OriginImportPreview(FormPreview):

    form_template = "tournament/originImport.html"
    preview_template = "tournament/origin_preview.html"

    def parse_params(self, request):

        self.request = request

        atts = self.request.user.profile.attendee_set.all()
        trns = []
        print(atts)
        for att in atts:
            if att.has_permission("tournament.change_origin"):
                trns.append(att.tournament.id)
            print(trns)

        tournament = forms.ModelChoiceField(
            Tournament.objects.filter(id__in=trns), required=False, widget=Select2Widget
        )

        managers = forms.BooleanField(
            label="Import managers", initial=True, required=False
        )

        membervars = {"tournament": tournament, "managers": managers}
        self.form = type("ObjsForm", (forms.Form,), membervars)

    def process_preview(self, request, form, context):

        origins = []

        trn = form.cleaned_data["tournament"]

        ex_origins = request.user.profile.tournament.origin_set

        for o in trn.origin_set.all():

            ori = {
                "name": o.name,
                "alpha2iso": o.alpha2iso,
                "slug": o.slug,
                "flag": o.flag,
                "flag_pdf": o.flag_pdf,
            }

            if form.cleaned_data["managers"]:
                try:
                    managers = []
                    managers_tm = (
                        o.team_set.first().teammember_set.filter(manager=True).all()
                    )  # .values("attendee__active_user",flat=True)
                    for m in managers_tm:
                        managers.append(m.attendee.active_user)
                except AttributeError:
                    managers = []

                ori.update(
                    {
                        "possible_managers": o.possible_managers.all(),
                        "managers": managers,
                    }
                )
            ex_origin = ex_origins.filter(name=o.name)
            if ex_origin.exists():
                ori["exists"] = True
                if form.cleaned_data["managers"]:
                    ori["ex_managers"] = ex_origin.first().possible_managers.all()
            origins.append(ori)
        context["origins"] = origins

    def done(self, request, cleaned_data):

        trn = cleaned_data["tournament"]

        ex_origins = request.user.profile.tournament.origin_set

        for o in trn.origin_set.all():
            ex_origin = ex_origins.filter(name=o.name)

            if cleaned_data["managers"]:
                managers = o.possible_managers.all()

                try:
                    real_managers = []
                    real_managers_tm = (
                        o.team_set.first().teammember_set.filter(manager=True).all()
                    )
                    for m in real_managers_tm:
                        real_managers.append(m.attendee.active_user)
                except AttributeError:
                    real_managers = []

            if ex_origin.exists():
                new_origin = ex_origin.first()
            else:
                o.pk = None
                o.tournament = request.user.profile.tournament
                o.from_registration = False
                o.save()
                new_origin = o

            if cleaned_data["managers"]:
                if len(managers) > 0:
                    new_origin.possible_managers.add(*managers)

                if len(real_managers) > 0:
                    new_origin.possible_managers.add(*real_managers)

        return redirect("tournament:origins")


@method_decorator(login_required, name="__call__")
@method_decorator(
    permission_required("registration.add_applicationquestion"), name="__call__"
)
class ADImportPreview(FormPreview):

    form_template = "tournament/originImport.html"
    preview_template = "tournament/data_preview.html"

    def parse_params(self, request):

        self.request = request

        atts = self.request.user.profile.attendee_set.all()
        trns = []
        print(atts)
        for att in atts:
            if att.has_permission("registration.change_applicationquestion"):
                trns.append(att.tournament.id)
            print(trns)

        tournament = forms.ModelChoiceField(
            Tournament.objects.filter(id__in=trns), required=False, widget=Select2Widget
        )

        membervars = {"tournament": tournament}
        self.form = type("ObjsForm", (forms.Form,), membervars)

    def process_preview(self, request, form, context):

        ad = []

        trn: Tournament
        trn = form.cleaned_data["tournament"]
        ctrn = request.user.profile.tournament
        rolemap = {}
        for pr in trn.participationrole_set.all():
            try:
                newrole = ctrn.participationrole_set.get(name__icontains=pr.name)
            except Exception as e:
                print(e)
                newrole = None
            rolemap[pr] = newrole
        context["map"] = rolemap
        for a in trn.attendeeproperty_set.all():

            o = {
                "name": a.name,
                "type": a.type,
                "user_property": a.user_property,
                "data_utilisation": a.data_utilisation,
                "edit_multi": a.edit_multi,
                "hidden": a.hidden,
                "manager_confirmed": a.manager_confirmed,
                "id": a.id,
            }

            # required, optional, required_if, apply_required
            o["required"] = [rolemap[r] for r in a.required.all()]
            o["optional"] = [rolemap[r] for r in a.optional.all()]
            o["apply_required"] = [rolemap[r] for r in a.apply_required.all()]
            # print(a.required_if)
            if a.required_if:
                o["required_if"] = a.required_if.name

            ad.append(o)

        context["object_list"] = ad

    def done(self, request, cleaned_data):

        trn = cleaned_data["tournament"]
        ctrn = request.user.profile.tournament
        rolemap = {}
        for pr in trn.participationrole_set.all():
            try:
                newrole = ctrn.participationrole_set.get(name__icontains=pr.name)
            except Exception as e:
                print(e)
                newrole = None
            rolemap[pr] = newrole

        idmap = {}
        for a in trn.attendeeproperty_set.all():
            ap = AttendeeProperty.objects.create(
                tournament=ctrn,
                name=a.name,
                type=a.type,
                user_property=a.user_property,
                data_utilisation=a.data_utilisation,
                edit_multi=a.edit_multi,
                hidden=a.hidden,
                manager_confirmed=a.manager_confirmed,
            )
            idmap[a.id] = ap.id

            for r in a.required.all():
                newrole = rolemap[r]
                if newrole is not None:
                    ap.required.add(newrole)

            for r in a.optional.all():
                newrole = rolemap[r]
                if newrole is not None:
                    ap.optional.add(newrole)

            for r in a.apply_required.all():
                newrole = rolemap[r]
                if newrole is not None:
                    ap.apply_required.add(newrole)

        for a in trn.attendeeproperty_set.all():
            if a.required_if:
                ap = AttendeeProperty.objects.get(id=idmap[a.id])
                depap = AttendeeProperty.objects.get(id=idmap[a.required_if.id])
                ap.required_if = depap
                ap.save()

        return redirect("tournament:properties")


@method_decorator(login_required, name="__call__")
@method_decorator(permission_required("jury.change_juroroccupation"), name="__call__")
class OccupationImportPreview(FormPreview):

    form_template = "tournament/originImport.html"
    preview_template = "tournament/occupation_preview.html"

    def parse_params(self, request):

        self.request = request

        atts = self.request.user.profile.attendee_set.all()
        trns = []
        print(atts)
        for att in atts:
            if att.has_permission("jury.change_juroroccupation"):
                trns.append(att.tournament.id)
            print(trns)

        tournament = forms.ModelChoiceField(
            Tournament.objects.filter(id__in=trns), required=False, widget=Select2Widget
        )

        membervars = {"tournament": tournament}
        self.form = type("ObjsForm", (forms.Form,), membervars)

    def process_preview(self, request, form, context):

        trn: Tournament
        trn = form.cleaned_data["tournament"]

        context["object_list"] = trn.juroroccupation_set.all()

    def done(self, request, cleaned_data):

        trn = cleaned_data["tournament"]
        ctrn = request.user.profile.tournament

        for occ in trn.juroroccupation_set.all():
            JurorOccupation.objects.create(tournament=ctrn, name=occ.name)

        return redirect("tournament:joccupations")


@method_decorator(login_required, name="__call__")
@method_decorator(
    permission_required("registration.change_applicationquestion"), name="__call__"
)
class AQImportPreview(FormPreview):

    form_template = "tournament/originImport.html"
    preview_template = "tournament/aq_preview.html"

    def parse_params(self, request):

        self.request = request

        atts = self.request.user.profile.attendee_set.all()
        trns = []
        print(atts)
        for att in atts:
            if att.has_permission("registration.change_applicationquestion"):
                trns.append(att.tournament.id)
            print(trns)

        tournament = forms.ModelChoiceField(
            Tournament.objects.filter(id__in=trns), required=False, widget=Select2Widget
        )

        membervars = {"tournament": tournament}
        self.form = type("ObjsForm", (forms.Form,), membervars)

    def process_preview(self, request, form, context):

        aq = []

        trn: Tournament
        trn = form.cleaned_data["tournament"]
        ctrn = request.user.profile.tournament
        rolemap = {}
        for pr in trn.participationrole_set.all():
            try:
                newrole = ctrn.participationrole_set.get(name__icontains=pr.name)
            except Exception as e:
                print(e)
                newrole = None
            rolemap[pr] = newrole
        context["map"] = rolemap

        for role in trn.participationrole_set.all():
            for a in role.applicationquestion_set.all():

                aq.append(a)

                # if a.required_if:
                #    o["required_if"] = a.required_if.name

                # ad.append(o)

        context["object_list"] = aq

    def done(self, request, cleaned_data):

        trn = cleaned_data["tournament"]
        ctrn = request.user.profile.tournament
        rolemap = {}
        for pr in trn.participationrole_set.all():
            try:
                newrole = ctrn.participationrole_set.get(name__icontains=pr.name)
            except Exception as e:
                print(e)
                newrole = None
            rolemap[pr] = newrole

        idmap = {}
        for role in trn.participationrole_set.all():
            for a in role.applicationquestion_set.all():
                if rolemap[a.role] is None:
                    continue

                aq = ApplicationQuestion.objects.create(
                    role=rolemap[a.role],
                    name=a.name,
                    short_name=a.short_name,
                    help_text=a.help_text,
                    type=a.type,
                    active=a.active,
                )
                idmap[a.id] = aq.id

            for a in role.applicationquestion_set.all():
                if a.required_if:
                    ap = ApplicationQuestion.objects.get(id=idmap[a.id])
                    depap = ApplicationQuestion.objects.get(id=idmap[a.required_if.id])
                    ap.required_if = depap
                    ap.save()

        return redirect("tournament:proles")
