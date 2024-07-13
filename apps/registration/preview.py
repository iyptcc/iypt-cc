import os
import zipfile
from datetime import timedelta
from functools import partial

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.hashers import check_password, make_password
from django.core import mail
from django.core.files.storage import FileSystemStorage
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.template.defaultfilters import slugify
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_select2.forms import Select2Widget
from formtools.preview import FormPreview
from formtools.wizard.views import SessionWizardView, WizardView

from apps.account.models import Attendee, ParticipationRole
from apps.bank.models import Account, Payment
from apps.bank.utils import expected_fees
from apps.dashboard.forms import ModelDeleteListField
from apps.dashboard.preview import ListPreview
from apps.jury.models import Juror, PossibleJuror
from apps.postoffice.models import Template as MailTemplate
from apps.postoffice.utils import render_template
from apps.printer import context_generator
from apps.printer.models import Pdf, PdfTag, Template
from apps.printer.tasks import render_to_pdf
from apps.printer.utils import _get_next_pdfname
from apps.team.models import Team, TeamRole
from apps.tournament.models import Origin, Tournament

from .forms import ApplyRoleForm, ApplyRoleQuestionForm
from .models import (
    Application,
    ApplicationQuestion,
    ApplicationQuestionValue,
    AttendeeProperty,
    AttendeePropertyValue,
    Property,
)
from .utils import (
    accept_teammanager,
    application_propertyvalues,
    field_for_property,
    field_for_question,
    get_members,
    persons_data,
    update_property,
)
from .views import TeamMgntPermMixin


@method_decorator(login_required, name="__call__")
@method_decorator(permission_required("registration.view_all_data"), name="__call__")
class AttendeePreview(ListPreview):

    form_template = "registration/overview.html"
    success_url = "registration:overview"

    def get_filters(self, request):
        trn = request.user.profile.tournament

        filters = [
            {
                "name": "Roles",
                "filter": "roles__in",
                "elements": trn.participationrole_set.all(),
            },
            {"name": "Team", "elements": trn.team_set.all(), "filter": "team__in"},
        ]

        apoq = AttendeeProperty.objects.filter(tournament=trn).prefetch_related(
            "required", "optional"
        )
        for ap in apoq:
            if ap.type == Property.BOOLEAN:

                def check(ap, att):
                    try:
                        apv = att.attendeepropertyvalue_set.filter(property=ap).last()
                        val = getattr(apv, apv.field_name[ap.type])
                        return int(val)
                    except Exception as e:
                        print(e)
                        pass

                filters.append(
                    {
                        "name": ap.name,
                        "elements": [
                            self.DirectSelector(1, "True"),
                        ],
                        "filter_func": partial(check, ap),
                        "filter_name": slugify(ap.name),
                    }
                )
            elif ap.type == Property.CHOICE:

                def check(ap, att):
                    try:
                        apv = att.attendeepropertyvalue_set.filter(property=ap).last()
                        val = apv.choices_value.first()
                        return val.id
                    except Exception as e:
                        print(e)
                        pass

                filters.append(
                    {
                        "name": ap.name,
                        "elements": ap.propertychoice_set.all(),
                        "filter_func": partial(check, ap),
                        "filter_name": slugify(ap.name),
                    }
                )

        return filters

    def form_members(self):
        trn = self.request.user.profile.tournament
        template = forms.ModelChoiceField(
            queryset=trn.template_set.filter(type=Template.REGISTRATION),
            required=False,
            widget=Select2Widget(),
        )

        emails = forms.ModelChoiceField(
            queryset=trn.mailtemplates.filter(type=MailTemplate.REGISTRATION),
            required=False,
            widget=Select2Widget(),
        )

        download = forms.ModelChoiceField(
            queryset=trn.attendeeproperty_set.filter(type=AttendeeProperty.IMAGE),
            required=False,
            widget=Select2Widget,
        )

        aps_forms = []
        extra_fields = {}

        apoq = AttendeeProperty.objects.filter(tournament=trn).prefetch_related(
            "required", "optional"
        )
        for ap in apoq:
            if ap.type == Property.BOOLEAN:
                bf = forms.BooleanField(required=False)
                bf_set = forms.BooleanField(required=False)
                extra_fields["ap_%d" % ap.id] = bf
                extra_fields["ap_%d_set" % ap.id] = bf_set
                aps_forms.append(ap)

        self.aps_forms = aps_forms

        def get_aps_forms(self):
            for ap in self.aps_forms:
                yield {
                    "field": self.__getitem__("ap_%d" % ap.id),
                    "set_field": self.__getitem__("ap_%d_set" % ap.id),
                    "name": ap.name,
                }

        return {
            "template": template,
            "emails": emails,
            "download": download,
            "aps_forms": aps_forms,
            "get_aps_forms": get_aps_forms,
            **extra_fields,
        }

    def preview_actions(self, request, form, context):

        if "_print" in request.POST:
            context["action"] = "_print"

            self.preview_template = "registration/attendees_preview.html"

            persons = []

            for att in form.cleaned_data["obj_list"]:

                person = {"full_name": att.full_name, "obj": att}
                persons.append(person)

            context["persons"] = persons

        elif "_mail" in request.POST:
            context["action"] = "_mail"

            self.preview_template = "registration/attendees_mail_preview.html"

            ctx = context_generator.registration(form.cleaned_data["obj_list"])

            srcs = render_template(
                form.cleaned_data["emails"].id,
                ctx["persons"],
                global_context={"properties": ctx["properties"]},
            )

            emails = []
            for idx, src in enumerate(srcs):
                emails.append(
                    {
                        "email": form.cleaned_data["obj_list"][
                            idx
                        ].active_user.user.email,
                        "subject": src["subject"],
                        "body": src["body"],
                    }
                )

            context["srcs"] = emails

        elif "_download" in request.POST:
            context["action"] = "_download"

            self.preview_template = "registration/attendees_file_preview.html"

            c = []

            ap = form.cleaned_data["download"]
            for att in form.cleaned_data["obj_list"]:
                try:
                    apv = att.attendeepropertyvalue_set.filter(property=ap).last()
                    c.append(
                        {
                            "full_name": att.full_name,
                            "obj": att,
                            "url": apv.image_value.url.split("/")[-1],
                            "image_id": apv.id,
                        }
                    )
                except:
                    pass
            context["persons"] = c

        elif "_set_parameters" in request.POST:
            context["action"] = "_set_parameters"
            self.preview_template = "registration/attendees_set_preview.html"

            persons = []

            aps = []
            for ap in form.aps_forms:
                aps.append(ap.name)

            context["change_aps"] = aps

            for att in form.cleaned_data["obj_list"]:
                person = {"full_name": att.full_name, "obj": att, "data": []}

                for ap in form.aps_forms:
                    ap_set = form.cleaned_data["ap_%d_set" % ap.id]
                    ap_val = form.cleaned_data["ap_%d" % ap.id]

                    try:
                        apv = att.attendeepropertyvalue_set.filter(property=ap).last()
                        old_val = getattr(apv, apv.field_name[ap.type])
                    except Exception as e:
                        print("errror from val")
                        print(e)
                        old_val = None

                    dat_p = {"changed": False, "value": old_val}

                    if ap_set:
                        print("set ap")
                        if ap_val:
                            print("val true")
                            if old_val != True:
                                dat_p["changed"] = True
                                dat_p["value"] = True
                        else:
                            if old_val != False:
                                dat_p["changed"] = True
                                dat_p["value"] = False

                    person["data"].append(dat_p)

                persons.append(person)

            context["persons"] = persons

        elif "_mailto" in request.POST:

            context["action"] = "_mailto"

            self.preview_template = "registration/attendees_mailto_preview.html"

            persons = []

            for att in form.cleaned_data["obj_list"]:

                person = {
                    "full_name": "%s %s" % (att.first_name, att.last_name),
                    "email": att.active_user.user.email,
                }
                persons.append(person)

            context["persons"] = persons

    def get_prefetch(self):
        return ["roles", "groups", "active_user__user", "teammember_set__team__origin"]

    def get_queryset(self):
        trn = self.request.user.profile.tournament
        return Attendee.objects.filter(tournament=trn).order_by(
            "active_user__user__last_name"
        )

    def get_context(self, request, form):
        context = super().get_context(request, form)
        att, aps = persons_data(self.obj_list.queryset, hidden=True)
        context["att_data"] = att
        # print(att)
        context["aps"] = aps

        return context

    def done_actions(self, request, cleaned_data):

        if request.POST["action"] == "_print":
            trn = request.user.profile.tournament
            template = cleaned_data["template"]

            context = context_generator.registration(cleaned_data["obj_list"])

            fileprefix = "registration-%s-v" % slugify(template.name)

            pdf = Pdf.objects.create(
                name="%s%d" % (fileprefix, _get_next_pdfname(trn, fileprefix)),
                tournament=trn,
            )

            res = render_to_pdf.delay(template.id, pdf.id, context=context)

            pdf.task_id = res.id
            pdf.save()

            pdf.tags.add(PdfTag.objects.get(tournament=trn, type=Template.REGISTRATION))

        elif request.POST["action"] == "_download":
            ap = cleaned_data["download"]

            response = HttpResponse(content_type="application/zip")
            zip_file = zipfile.ZipFile(response, "w")
            for att in cleaned_data["obj_list"]:
                try:
                    apv = att.attendeepropertyvalue_set.filter(property=ap).last()
                    img = apv.image_value
                    file = os.path.join(settings.MEDIA_ROOT, img.name)
                    zipname = os.path.join(
                        "%d-%s" % (ap.id, slugify(ap.name)),
                        "%d-%s-%s"
                        % (att.id, slugify(att.full_name), img.name.split("/")[-1]),
                    )

                    zip_file.write(file, zipname)
                except Exception as e:
                    print(e)
                    pass
            zip_file.close()
            response["Content-Disposition"] = "attachment; filename={}".format(
                "images.zip"
            )
            return response

        elif request.POST["action"] == "_mail":

            ctx = context_generator.registration(cleaned_data["obj_list"])

            srcs = render_template(
                cleaned_data["emails"].id,
                ctx["persons"],
                global_context={"properties": ctx["properties"]},
            )

            emails = []

            for idx, src in enumerate(srcs):
                emails.append(
                    mail.EmailMessage(
                        src["subject"],
                        src["body"],
                        "cc@iypt.org",
                        [cleaned_data["obj_list"][idx].active_user.user.email],
                    )
                )

            with mail.get_connection() as connection:
                connection.send_messages(emails)

        elif request.POST["action"] == "_set_parameters":

            for att in cleaned_data["obj_list"]:

                for ap in self.aps_forms:
                    ap_set = cleaned_data["ap_%d_set" % ap.id]
                    ap_val = cleaned_data["ap_%d" % ap.id]
                    if ap_set:
                        try:
                            apv = att.attendeepropertyvalue_set.filter(
                                property=ap
                            ).last()
                        except:
                            apv = None

                        update_property(
                            request,
                            ap,
                            apv,
                            ap_val,
                            "attendee-property-%d",
                            AttendeePropertyValue,
                            {"attendee": att, "author": request.user.profile},
                            copy_image=False,
                            prelim=False,
                        )

        elif request.POST["action"] == "_mailto":
            pass


@method_decorator(login_required, name="__call__")
class TeamOverviewPreview(TeamMgntPermMixin, FormPreview):

    form_template = "registration/team.html"
    preview_template = "registration/team_preview.html"

    def parse_params(self, request, s_team):
        self.team = Team.objects.get(
            origin__slug=s_team, tournament=request.user.profile.tournament
        )

        join_password = forms.CharField(
            widget=forms.PasswordInput,
            max_length=100,
            label="Join Password (leave blank to keep existing password)",
            required=False,
        )
        notify_applications = forms.BooleanField(
            initial=self.team.notify_applications, required=False
        )

        self.oldpw = self.team.join_password

        membervars = {
            "join_password": join_password,
            "notify_applications": notify_applications,
        }
        self.obj_list = ModelDeleteListField(
            queryset=self.team.teammember_set.all(), required=False
        )

        aps_forms = []
        extra_fields = {}

        apoq = AttendeeProperty.objects.filter(
            tournament=self.team.tournament, hidden=False, edit_multi=True
        ).prefetch_related("required", "optional")
        for ap in apoq:
            bf_set = forms.BooleanField(required=False)
            bf = None
            if ap.type in [
                Property.INT,
                Property.STRING,
                Property.DATETIME,
                Property.DATE,
                # Property.IMAGE,
                # Property.PDF,
                Property.TEXT,
                # Property.GENDER,
                Property.BOOLEAN,
                Property.BOOLEAN_TRUE,
                # Property.PREFERRED_NAME,
                # Property.PREFERRED_NAME_SHORT,
                # Property.CHOICE,
                # Property.MULTIPLE_CHOICE,
                # Property.CONFLICT_ORIGINS,
                # Property.COUNTRY,
                # Property.PROBLEM
            ]:
                bf = field_for_property(ap)
            if bf is not None:
                extra_fields["ap_%d" % ap.id] = bf
                extra_fields["ap_%d_set" % ap.id] = bf_set
                aps_forms.append(ap)

        self.aps_forms = aps_forms

        def get_aps_forms(self):
            for ap in self.aps_forms:
                yield {
                    "field": self.__getitem__("ap_%d" % ap.id),
                    "set_field": self.__getitem__("ap_%d_set" % ap.id),
                    "name": ap.name,
                }

        membervars.update(
            {"aps_forms": aps_forms, "get_aps_forms": get_aps_forms, **extra_fields}
        )

        membervars["obj_list"] = self.obj_list

        self.form = type("TeamForm", (forms.Form,), membervars)

    def get_context(self, request, form):
        context = super().get_context(request, form)

        members, aps, limits, missing = get_members(
            request.user.profile.tournament, self.team
        )
        fees = expected_fees(self.team)
        feesum = sum([0] + [f["amount"] for f in fees])

        context["team"] = self.team
        context["members"] = members
        context["limits"] = limits
        context["fees"] = fees
        context["fees_sum"] = feesum
        context["apname"] = aps
        context["att_data"] = {
            mem["id"]: {
                "data": mem["data"],
                "juror": mem["juror"],
                "possiblejuror": mem["possiblejuror"],
                "accepted": mem["accepted"],
            }
            for mem in members
        }
        context["data_logs"] = AttendeePropertyValue.objects.filter(
            attendee__team=self.team
        ).order_by("-creation")[:10]
        context["applications"] = Application.objects.filter(team=self.team)

        return context

    def process_preview(self, request, form, context):
        if "_save" in request.POST:
            context["action"] = "_save"

            context["notify"] = form.cleaned_data["notify_applications"]
            context["password"] = form.cleaned_data["join_password"]

        elif "_set_parameters" in request.POST:
            context["action"] = "_set_parameters"
            self.preview_template = "registration/team_set_preview.html"

            persons = []

            aps = []
            for ap in form.aps_forms:
                aps.append(ap.name)

            context["change_aps"] = aps

            for mem in form.cleaned_data["obj_list"]:
                att = mem.attendee
                person = {"full_name": att.full_name, "obj": att, "data": []}

                att_roles = set(att.roles.values_list("id", flat=True))

                for ap in form.aps_forms:
                    ap_set = form.cleaned_data["ap_%d_set" % ap.id]
                    ap_val = form.cleaned_data["ap_%d" % ap.id]

                    required = set(ap.required.all().values_list("id", flat=True))
                    optional = set(ap.optional.all().values_list("id", flat=True))

                    if len(att_roles & required) or len(att_roles & optional):

                        try:
                            apv = att.attendeepropertyvalue_set.filter(
                                property=ap
                            ).last()
                            old_val = getattr(apv, apv.field_name[ap.type])
                        except Exception as e:
                            print("errror from val")
                            print(e)
                            old_val = None

                        dat_p = {"changed": False, "value": old_val}

                        if ap_set:
                            print("set ap")
                            if old_val != ap_val:
                                dat_p["changed"] = True
                            else:
                                dat_p["changed"] = True
                            dat_p["value"] = ap_val

                    else:
                        dat_p = {"changed": False, "value": None}

                    person["data"].append(dat_p)

                persons.append(person)

            context["persons"] = persons

    def done(self, request, cleaned_data):

        if request.POST["action"] == "_save":
            self.team.notify_applications = cleaned_data["notify_applications"]
            if cleaned_data["join_password"] != "":
                self.team.join_password = make_password(cleaned_data["join_password"])
            self.team.save()

        elif request.POST["action"] == "_set_parameters":

            for mem in cleaned_data["obj_list"]:

                att = mem.attendee
                att_roles = set(att.roles.values_list("id", flat=True))

                for ap in self.aps_forms:
                    ap_set = cleaned_data["ap_%d_set" % ap.id]
                    ap_val = cleaned_data["ap_%d" % ap.id]

                    required = set(ap.required.all().values_list("id", flat=True))
                    optional = set(ap.optional.all().values_list("id", flat=True))

                    if len(att_roles & required) or len(att_roles & optional):
                        if ap_set:
                            try:
                                apv = att.attendeepropertyvalue_set.filter(
                                    property=ap
                                ).last()
                            except:
                                apv = None

                            update_property(
                                request,
                                ap,
                                apv,
                                ap_val,
                                "attendee-property-%d",
                                AttendeePropertyValue,
                                {"attendee": att, "author": request.user.profile},
                                copy_image=False,
                                prelim=False,
                            )

        return redirect(
            reverse("registration:team_overview", args=[self.team.origin.slug])
        )


@method_decorator(login_required, name="__call__")
class PayFeePreview(TeamMgntPermMixin, FormPreview):
    form_template = "registration/payment.html"
    preview_template = "registration/payment_preview.html"

    class MinusZero:
        id = 0

    def parse_params(self, request, s_team):
        team = get_object_or_404(
            Team, origin__slug=s_team, tournament=request.user.profile.tournament
        )

        self.team = team

        fields = {}

        accounts = Account.objects.filter(
            owners__tournament=team.tournament, owners=request.user.profile.active
        ).distinct()
        if accounts.count() > 0:
            account = forms.ModelChoiceField(accounts, required=False)
            fields["account"] = account

        new_account_name = forms.CharField(
            max_length=100, label="if wanted, new account name", required=False
        )
        fields["new_account"] = new_account_name

        def clean(self):
            cleaned_data = super(self.__class__, self).clean()
            # print(cleaned_data)
            if (
                cleaned_data.get("account", None) == None
                and cleaned_data["new_account"] == ""
            ):
                raise forms.ValidationError(
                    "You have to choose an Account or enter a new name"
                )

        fields["clean"] = clean

        fees = expected_fees(team)
        for fee in fees:
            chk = forms.BooleanField(
                required=False,
                initial=True,
                label="%s : %.2f €" % (fee["name"], fee["amount"]),
            )

            ep = None
            if fee["type"] == Payment.TEAM:
                ep = Payment.objects.filter(
                    sender__in=accounts, ref_type=fee["type"], ref_team=team
                ).first()
            elif fee["type"] == Payment.ROLE:
                ep = Payment.objects.filter(
                    sender__in=accounts,
                    ref_type=fee["type"],
                    ref_role=fee["role"],
                    ref_attendee=fee["attendee"],
                ).first()
            elif fee["type"] == Payment.PROPERTY:
                ep = Payment.objects.filter(
                    sender__in=accounts,
                    ref_type=fee["type"],
                    ref_property=fee["property"],
                    ref_attendee=fee["attendee"],
                ).first()
            if ep:
                chk.help_text = "already invoiced to account %d %s" % (
                    ep.sender.id,
                    ep.sender,
                )
                chk.initial = False

            fields[
                "fee_%s_%d_%d_%d"
                % (
                    fee["type"],
                    fee.get("attendee", self.MinusZero()).id,
                    fee.get("role", self.MinusZero()).id,
                    fee.get("property", self.MinusZero()).id,
                )
            ] = chk

        self.form = type("FeeForm", (forms.Form,), fields)

    def process_preview(self, request, form, context):

        if "account" in form.cleaned_data:
            context["account"] = form.cleaned_data["account"]
        else:
            context["account"] = {
                "owners": self.team.get_managers(),
                "team": self.team,
                "name": form.cleaned_data["new_account"],
            }

        ifees = []
        fsum = 0
        fees = expected_fees(self.team)
        for fee in fees:
            if form.cleaned_data[
                "fee_%s_%d_%d_%d"
                % (
                    fee["type"],
                    fee.get("attendee", self.MinusZero()).id,
                    fee.get("role", self.MinusZero()).id,
                    fee.get("property", self.MinusZero()).id,
                )
            ]:
                ifees.append(fee)
                fsum += fee["amount"]

        context["fees"] = ifees
        context["fees_sum"] = fsum

    def done(self, request, cleaned_data):

        if not request.user.profile.tournament.bank_expected_fee:
            messages.add_message(
                request, messages.ERROR, "Payment is handled by organisers"
            )
            return redirect("account:accounts")

        if "account" in cleaned_data:
            account = cleaned_data["account"]
        else:
            account = Account.objects.create(
                team=self.team, name=cleaned_data["new_account"]
            )
            account.owners.add(*self.team.get_managers())

        fees = expected_fees(self.team)
        for fee in fees:
            if cleaned_data[
                "fee_%s_%d_%d_%d"
                % (
                    fee["type"],
                    fee.get("attendee", self.MinusZero()).id,
                    fee.get("role", self.MinusZero()).id,
                    fee.get("property", self.MinusZero()).id,
                )
            ]:

                duedate = self.team.tournament.bank_default_due
                if (
                    duedate < timezone.now()
                    and self.team.tournament.bank_default_contingency_days is not None
                ):
                    duedate = timezone.now() + timedelta(
                        days=self.team.tournament.bank_default_contingency_days
                    )

                py = Payment.objects.create(
                    sender=account,
                    created_by=request.user.profile.active,
                    amount=fee["amount"],
                    reference=fee["name"],
                    ref_type=fee["type"],
                    receiver=self.team.tournament.bank_default_account,
                    due_at=duedate,
                )
                if fee["type"] == Payment.TEAM:
                    py.ref_team = self.team
                elif fee["type"] == Payment.ROLE:
                    py.ref_role = fee["role"]
                    py.ref_attendee = fee["attendee"]
                elif fee["type"] == Payment.PROPERTY:
                    py.ref_property = fee["property"]
                    py.ref_attendee = fee["attendee"]
                py.save()

        return redirect("account:accounts")


@method_decorator(login_required, name="__call__")
class ApplyPossibleJurorPreview(FormPreview):

    form_template = "registration/apply_possiblejuror.html"
    preview_template = "registration/apply_possiblejuror_preview.html"

    def parse_params(self, request, t_slug):
        tournament = get_object_or_404(
            Tournament,
            slug=t_slug,
            registration_open__lt=timezone.now(),
            registration_close__gt=timezone.now(),
        )
        self.tournament = tournament

        members = {}
        if tournament.possiblejuror_ask_experience:
            members["experience"] = forms.ChoiceField(
                choices=Juror.EXPERIENCES, required=True
            )
        if tournament.possiblejuror_ask_occupation:
            members["occupation"] = forms.ModelChoiceField(
                queryset=tournament.juroroccupation_set.all(), required=True
            )
        if tournament.possiblejuror_ask_remark:
            members["remark"] = forms.CharField(max_length=1000, required=False)

        self.form = type("JurorForm", (forms.Form,), members)

    def get_context(self, request, form):

        available = True
        if request.user.profile.possiblejuror_set.filter(
            tournament=self.tournament
        ).exists():
            # already a possible juror object
            print("is possible")
            if not self.tournament.possiblejuror_reapply:
                available = False

        return {
            "available": available,
            "form": form,
            "stage_field": self.unused_name("stage"),
            "state": self.state,
        }

    def process_preview(self, request, form, context):

        context.update(
            application_propertyvalues(
                self.tournament,
                ParticipationRole.objects.get(
                    type=ParticipationRole.JUROR, tournament=self.tournament
                ),
                request.user.profile,
            )
        )

        vals = {}
        for v in ["experience", "occupation", "remark"]:
            if v in form.cleaned_data:
                vals[v] = form.cleaned_data[v]

        context.update({"values": vals})

        if PossibleJuror.objects.filter(
            person=request.user.profile, tournament=self.tournament
        ).exists():
            context["applied"] = True

    def done(self, request, cleaned_data):

        available = True
        if request.user.profile.possiblejuror_set.filter(
            tournament=self.tournament
        ).exists():
            # already a possible juror object
            print("is possible")
            if not self.tournament.possiblejuror_reapply:
                available = False

        if available:
            pj = PossibleJuror.objects.get_or_create(
                person=request.user.profile, tournament=self.tournament
            )[0]

            pj.approved_at = None
            pj.approved_by = None

            for v in ["experience", "occupation", "remark"]:
                if v in cleaned_data:
                    pj.__setattr__(v, cleaned_data[v])

            pj.save()

            if self.tournament.registration_notifications.count() > 0:
                send_mail(
                    "%s new possible juror application: %s"
                    % (self.tournament.name, request.user.username),
                    "%s %s (%s, %s) applied to %s as possible juror"
                    % (
                        request.user.first_name,
                        request.user.last_name,
                        request.user.username,
                        request.user.email,
                        self.tournament.name,
                    ),
                    settings.EMAIL_FROM,
                    self.tournament.registration_notifications.all().values_list(
                        "active_user__user__email", flat=True
                    ),
                    fail_silently=False,
                )

        return redirect("registration:applications")


@method_decorator(login_required, name="dispatch")
class ApplyWithRoleWizard(SessionWizardView):

    file_storage = FileSystemStorage(
        location=os.path.join(settings.MEDIA_ROOT, "application-wizzard-tmp")
    )

    form_list = [("role", ApplyRoleForm), ("questions", ApplyRoleQuestionForm)]

    def get_template_names(self):
        TEMPLATES = {
            "role": "registration/apply_participationrole.html",
            "questions": "registration/apply_participationrole_preview.html",
        }
        return [TEMPLATES[self.steps.current]]

    def get_context_data(self, form, **kwargs):
        context = super(ApplyWithRoleWizard, self).get_context_data(form=form, **kwargs)
        if self.steps.current == "questions":
            role = self.get_cleaned_data_for_step(step="role")["role"]

            context["role"] = role
            context["tournament"] = get_object_or_404(
                Tournament,
                slug=self.kwargs["t_slug"],
                registration_open__lt=timezone.now(),
                registration_close__gt=timezone.now(),
            )

            context.update(
                application_propertyvalues(
                    context["tournament"], context["role"], self.request.user.profile
                )
            )
        return context

    def done(self, form_list, **kwargs):
        form_data = [form.cleaned_data for form in form_list]

        role = self.get_cleaned_data_for_step(step="role")["role"]

        tournament = get_object_or_404(
            Tournament,
            slug=self.kwargs["t_slug"],
            registration_open__lt=timezone.now(),
            registration_close__gt=timezone.now(),
        )

        app = Application.objects.create(
            applicant=self.request.user.profile,
            tournament=tournament,
            participation_role=role,
        )

        for qu in ApplicationQuestion.objects.filter(role=role, active=True):

            ans = form_data[1].get("question-%d" % qu.id, None)

            if ans is not None:
                params = {
                    ApplicationQuestionValue.field_name[qu.type]: ans,
                }
                ApplicationQuestionValue.objects.create(
                    question=qu, application=app, **params
                )

        messages.add_message(
            self.request,
            messages.SUCCESS,
            "Applied for role %s in tournament %s" % (role, tournament),
        )

        if tournament.registration_notifications.count() > 0:
            send_mail(
                "%s new role application: %s"
                % (tournament.name, self.request.user.username),
                "%s %s (%s, %s) applied to %s with role %s"
                % (
                    self.request.user.first_name,
                    self.request.user.last_name,
                    self.request.user.username,
                    self.request.user.email,
                    tournament.name,
                    role.name,
                ),
                settings.EMAIL_FROM,
                tournament.registration_notifications.all().values_list(
                    "active_user__user__email", flat=True
                ),
                fail_silently=False,
            )

        return redirect("registration:applications")

    def get_form_initial(self, step):
        if step == "role" and "role" in self.kwargs:
            try:
                initial = {
                    "role": ParticipationRole.objects.get(
                        tournament__slug=self.kwargs["t_slug"], id=self.kwargs["role"]
                    )
                }
                return initial
            except:
                pass
        else:
            return self.initial_dict.get(step, {})

    def get_form_kwargs(self, step):
        kwargs = {}
        kwargs["tournament"] = get_object_or_404(
            Tournament,
            slug=self.kwargs["t_slug"],
            registration_open__lt=timezone.now(),
            registration_close__gt=timezone.now(),
        )

        kwargs["activeuser"] = self.request.user.profile

        if step == "questions":
            d = self.get_cleaned_data_for_step(step="role")
            kwargs["role"] = d["role"]

        return kwargs


@method_decorator(login_required, name="__call__")
class ApplyTeamManager(FormPreview):

    form_template = "registration/apply_team.html"
    preview_template = "registration/apply_team_preview.html"

    def parse_params(self, request, t_slug):
        tournament = get_object_or_404(
            Tournament,
            slug=t_slug,
            registration_open__lt=timezone.now(),
            registration_close__gt=timezone.now(),
        )
        self.tournament = tournament

        name = forms.ModelChoiceField(
            queryset=Origin.objects.filter(tournament=tournament), required=False
        )
        new_name = forms.CharField(max_length=300, required=False)

        def clean(self):
            cleaned_data = super(self.__class__, self).clean()
            # print(cleaned_data)
            if cleaned_data["name"] == None and cleaned_data["new_name"] == "":
                raise forms.ValidationError(
                    "You have to choose a Team or enter a new name"
                )

            if (
                cleaned_data["new_name"] != ""
                and Origin.objects.filter(
                    tournament=self.tournament, name=cleaned_data["new_name"]
                ).exists()
            ):
                raise forms.ValidationError(
                    "Team %s alredy registered." % (cleaned_data["new_name"])
                )

        self.form = type(
            "TeamForm",
            (forms.Form,),
            {
                "name": name,
                "new_name": new_name,
                "clean": clean,
                "tournament": tournament,
            },
        )

    def get_context(self, request, form):
        context = super().get_context(request, form)
        context["tournament"] = self.tournament

        return context

    def process_preview(self, request, form, context):

        origin = None
        if "_newteam" in request.POST:
            origin = form.cleaned_data["new_name"]
            context["action"] = "_new_name"
        else:
            origin = form.cleaned_data["name"].name
            context["action"] = "_name"
            if (
                request.user.profile
                in form.cleaned_data["name"].possible_managers.all()
            ):
                context["allowed"] = True

        context["origin"] = origin
        context.update(
            application_propertyvalues(
                self.tournament,
                ParticipationRole.objects.get(
                    tournament=self.tournament, type=ParticipationRole.TEAM_MANAGER
                ),
                request.user.profile,
            )
        )

    def done(self, request, cleaned_data):

        if request.POST["action"] == "_new_name":
            origin = Origin.objects.create(
                tournament=self.tournament,
                from_registration=True,
                name=cleaned_data["new_name"],
            )
        else:
            origin = cleaned_data["name"]
            if request.user.profile in cleaned_data["name"].possible_managers.all():
                accept_teammanager(
                    request,
                    self.tournament,
                    origin,
                    True,
                    request.user.profile,
                    ParticipationRole.objects.get(
                        tournament=self.tournament, type=ParticipationRole.TEAM_MANAGER
                    ),
                )
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    "Your application for team %s in tournament %s was automatically accepted"
                    % (origin, self.tournament),
                )
                send_mail(
                    "Your team application for %s was automatically accepted"
                    % (origin.name),
                    "Team %s was directly accepted because you were a team manager last year. After setting a password, team members can apply to your team \n Please make sure to select the correct active tournament unter Profile > Tournament"
                    % (origin.name),
                    settings.EMAIL_FROM,
                    [request.user.email],
                    fail_silently=False,
                )
                return redirect("account:tournament")

        Application.objects.create(
            applicant=request.user.profile,
            tournament=self.tournament,
            participation_role=ParticipationRole.objects.get(
                tournament=self.tournament, type=ParticipationRole.TEAM_MANAGER
            ),
            origin=origin,
        )

        messages.add_message(
            request,
            messages.SUCCESS,
            "Applied for team %s in tournament %s" % (origin, self.tournament),
        )

        if self.tournament.registration_notifications.count() > 0:
            send_mail(
                "%s new team application: %s" % (self.tournament.name, origin.name),
                "%s %s (%s, %s) applied to %s with team %s"
                % (
                    request.user.first_name,
                    request.user.last_name,
                    request.user.username,
                    request.user.email,
                    self.tournament.name,
                    origin.name,
                ),
                settings.EMAIL_FROM,
                self.tournament.registration_notifications.all().values_list(
                    "active_user__user__email", flat=True
                ),
                fail_silently=False,
            )
        return redirect("registration:applications")


@method_decorator(login_required, name="__call__")
class ApplyTeamMember(FormPreview):

    form_template = "registration/apply_teammember.html"
    preview_template = "registration/apply_teammember_preview.html"

    def parse_params(self, request, t_slug, role=None, visitor=None):
        tournament = get_object_or_404(
            Tournament,
            slug=t_slug,
            registration_open__lt=timezone.now(),
            registration_close__gt=timezone.now(),
        )
        self.tournament = tournament

        try:
            initial = tournament.teamrole_set.get(id=role)
        except:
            initial = None

        team = forms.ModelChoiceField(
            queryset=Team.objects.filter(tournament=tournament)
        )
        password = forms.CharField(widget=forms.PasswordInput)
        # print("visitor:")
        # print(visitor)

        error_messages = {
            "invalid_login": "Please enter a correct password for team %(team)s.",
            "no_password": "Please ask your team manager to set a join password.",
            "inactive": "This account is inactive.",
        }

        # print(role)

        def clean_role(self):
            data = self.cleaned_data["role"]
            # print("in clean")
            # print(data)
            return data

        def clean(self):
            password = self.cleaned_data.get("password")

            team = self.cleaned_data.get("team")

            if team and password:
                if team.join_password is None:
                    raise forms.ValidationError(
                        self.error_messages["no_password"], code="no_password"
                    )

                valid = check_password(password, team.join_password)

                if not valid:
                    raise forms.ValidationError(
                        self.error_messages["invalid_login"],
                        code="invalid_login",
                        params={"team": team},
                    )

            return self.cleaned_data

        if not visitor:
            role = forms.ModelChoiceField(
                queryset=TeamRole.objects.filter(tournament=tournament).exclude(
                    type=TeamRole.ASSOCIATED
                ),
                initial=initial,
            )
            self.form = type(
                "TeamForm",
                (forms.Form,),
                {
                    "team": team,
                    "password": password,
                    "clean": clean,
                    "tournament": tournament,
                    "role": role,
                    "error_messages": error_messages,
                },
            )
            # print("use tm form")
        else:
            assro = TeamRole.objects.filter(
                tournament=tournament, type=TeamRole.ASSOCIATED
            )
            vis = forms.CharField(
                initial="Visitor", label="Role", disabled=True, required=False
            )
            self.form = type(
                "VisitorForm",
                (forms.Form,),
                {
                    "team": team,
                    "password": password,
                    "clean": clean,
                    "clean_role": clean_role,
                    "tournament": tournament,
                    "role": vis,
                    "error_messages": error_messages,
                },
            )
            # print("use vis form")

    def get_context(self, request, form):
        context = super().get_context(request, form)
        context["tournament"] = self.tournament

        return context

    def process_preview(self, request, form, context):

        context["role"] = form.cleaned_data["role"]
        context["origin"] = form.cleaned_data["team"].origin

        if type(form.cleaned_data["role"]) == str:
            # application as visitor
            context.update(
                application_propertyvalues(
                    self.tournament,
                    ParticipationRole.objects.get(
                        tournament=self.tournament, type=ParticipationRole.VISITOR
                    ),
                    request.user.profile,
                )
            )
        else:
            context.update(
                application_propertyvalues(
                    self.tournament,
                    form.cleaned_data["role"].participation_roles.first(),
                    request.user.profile,
                )
            )

    def done(self, request, cleaned_data):

        team = cleaned_data["team"]

        if type(cleaned_data["role"]) == str:
            prole = ParticipationRole.objects.get(
                tournament=self.tournament, type=ParticipationRole.VISITOR
            )
            trole = TeamRole.objects.filter(
                tournament=self.tournament, type=TeamRole.ASSOCIATED
            ).first()
        else:
            prole = cleaned_data["role"].participation_roles.first()
            trole = cleaned_data["role"]
        Application.objects.create(
            applicant=request.user.profile,
            tournament=self.tournament,
            participation_role=prole,
            team=team,
            team_role=trole,
        )
        messages.add_message(
            request,
            messages.SUCCESS,
            "Applied for team %s in tournament %s" % (team.origin, self.tournament),
        )

        if team.notify_applications:
            send_mail(
                "%s applied to be a member of your team %s"
                % (request.user.username, team.origin.name),
                "%s %s (%s, %s) applied to team %s with role %s"
                % (
                    request.user.first_name,
                    request.user.last_name,
                    request.user.username,
                    request.user.email,
                    team.origin.name,
                    trole,
                ),
                settings.EMAIL_FROM,
                team.teammember_set.filter(
                    attendee__roles__type=ParticipationRole.TEAM_MANAGER
                ).values_list("attendee__active_user__user__email", flat=True),
                fail_silently=False,
            )

        return redirect("registration:applications")
