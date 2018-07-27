import os
import zipfile
from datetime import datetime
from functools import partial

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.hashers import check_password
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, reverse
from django.template.defaultfilters import slugify
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_select2.forms import Select2Widget
from formtools.preview import FormPreview

from apps.account.models import Attendee, ParticipationRole
from apps.bank.models import Account, Payment
from apps.bank.utils import expected_fees
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

from .models import Application, AttendeeProperty, AttendeePropertyValue, Property
from .utils import application_propertyvalues, persons_data, update_property
from .views import TeamMgntPermMixin


@method_decorator(login_required, name='__call__')
@method_decorator(permission_required('registration.view_all_data'), name='__call__')
class AttendeePreview(ListPreview):

    form_template = "registration/overview.html"
    success_url = "registration:overview"

    def get_filters(self, request):
        trn = request.user.profile.tournament

        filters = [
            {"name": "Roles",
             "filter": "roles__in",
             "elements": trn.participationrole_set.all()},
            {'name': "Team",
             "elements": trn.team_set.all(),
             "filter": "team__in"},
        ]

        apoq = AttendeeProperty.objects.filter(tournament=trn).prefetch_related("required", "optional")
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

                filters.append({"name":ap.name,
                                "elements":[self.DirectSelector(1, "True"),],
                                "filter_func": partial(check,ap) ,
                                "filter_name":slugify(ap.name)
                })
            elif ap.type == Property.CHOICE:

                def check(ap, att):
                    try:
                        apv = att.attendeepropertyvalue_set.filter(property=ap).last()
                        val = apv.choices_value.first()
                        return val.id
                    except Exception as e:
                        print(e)
                        pass

                filters.append({"name":ap.name,
                                "elements":ap.propertychoice_set.all(),
                                "filter_func": partial(check,ap) ,
                                "filter_name":slugify(ap.name)
                })


        return filters

    def form_members(self):
        trn = self.request.user.profile.tournament
        template = forms.ModelChoiceField(queryset=trn.template_set.filter(type=Template.REGISTRATION), required=False,
                                          widget=Select2Widget())

        emails = forms.ModelChoiceField(
            queryset=trn.mailtemplates.filter(type=MailTemplate.REGISTRATION),
            required=False, widget=Select2Widget())

        download = forms.ModelChoiceField(queryset=trn.attendeeproperty_set.filter(type=AttendeeProperty.IMAGE), required=False, widget=Select2Widget)

        aps_forms = []
        extra_fields = {}

        apoq = AttendeeProperty.objects.filter(tournament=trn).prefetch_related("required", "optional")
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
                yield {"field":self.__getitem__("ap_%d" % ap.id),
                       "set_field":self.__getitem__("ap_%d_set" % ap.id),
                       "name":ap.name}

        return {"template":template,"emails":emails,"download":download,"aps_forms":aps_forms, 'get_aps_forms':get_aps_forms, **extra_fields}

    def preview_actions(self, request, form, context):

        if "_print" in request.POST:
            context['action'] = "_print"

            self.preview_template = "registration/attendees_preview.html"

            persons = []

            for att in form.cleaned_data['obj_list']:

                person = {"full_name": att.full_name, 'obj':att}
                persons.append(person)

            context['persons']=persons

        elif "_mail" in request.POST:
            context['action'] = "_mail"

            self.preview_template = "registration/attendees_mail_preview.html"

            c=[]

            for att in form.cleaned_data['obj_list']:
                c.append({"first_name":att.first_name,"last_name":att.last_name})

            srcs = render_template(form.cleaned_data["emails"].id, c)

            emails = []
            for idx, src in enumerate(srcs):
                emails.append({"email": form.cleaned_data['obj_list'][idx].active_user.user.email , "subject": src[0], "body": src[1]})

            context["srcs"] = emails

        elif "_download" in request.POST:
            context['action'] = "_download"

            self.preview_template = "registration/attendees_file_preview.html"

            c=[]

            ap = form.cleaned_data["download"]
            for att in form.cleaned_data['obj_list']:
                try:
                    apv = att.attendeepropertyvalue_set.filter(property=ap).last()
                    c.append({"full_name": att.full_name, 'obj':att, "url":apv.image_value.url.split("/")[-1], "image_id":apv.id})
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

            for att in form.cleaned_data['obj_list']:
                person = {"full_name": att.full_name, 'obj': att,"data":[]}

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
                                dat_p["changed"]=True
                                dat_p["value"]=True
                        else:
                            if old_val != False:
                                dat_p["changed"] = True
                                dat_p["value"] = False

                    person["data"].append(dat_p)

                persons.append(person)

            context['persons'] = persons

        elif "_mailto" in request.POST:

            context['action'] = "_mailto"

            self.preview_template = "registration/attendees_mailto_preview.html"

            persons = []

            for att in form.cleaned_data['obj_list']:

                person = {"full_name": "%s %s"%(att.first_name,att.last_name), "email":att.active_user.user.email}
                persons.append(person)

            context['persons']=persons

    def get_prefetch(self):
        return ['roles','groups','active_user__user','teammember_set__team__origin']

    def get_queryset(self):
        trn = self.request.user.profile.tournament
        return Attendee.objects.filter(tournament=trn).order_by("active_user__user__last_name")

    def get_context(self, request, form):
        context = super().get_context(request, form)
        att, aps = persons_data(self.obj_list.queryset, hidden=True)
        context["att_data"] = att
        #print(att)
        context["aps"] = aps

        return context

    def done_actions(self, request, cleaned_data):

        if request.POST['action'] == '_print':
            trn = request.user.profile.tournament
            template = cleaned_data['template']

            context = context_generator.registration(cleaned_data['obj_list'])

            fileprefix = "registration-%s-v" % slugify(template.name)

            pdf = Pdf.objects.create(name="%s%d" % (fileprefix, _get_next_pdfname(trn, fileprefix)), tournament=trn)

            res = render_to_pdf.delay(template.id, pdf.id, context=context)

            pdf.task_id = res.id
            pdf.save()

            pdf.tags.add(PdfTag.objects.get(tournament=trn, type=Template.REGISTRATION))

        elif request.POST['action'] == '_download':
            ap = cleaned_data["download"]

            response = HttpResponse(content_type='application/zip')
            zip_file = zipfile.ZipFile(response, 'w')
            for att in cleaned_data['obj_list']:
                try:
                    apv = att.attendeepropertyvalue_set.filter(property=ap).last()
                    img= apv.image_value
                    file= os.path.join(settings.MEDIA_ROOT,img.name)
                    zipname = os.path.join("%d-%s"%(ap.id,slugify(ap.name)), "%d-%s-%s"%(att.id,slugify(att.full_name),img.name.split("/")[-1]))

                    zip_file.write(file,zipname)
                except Exception as e:
                    print(e)
                    pass
            zip_file.close()
            response['Content-Disposition'] = 'attachment; filename={}'.format("images.zip")
            return response

        elif request.POST['action'] == '_set_parameters':

            for att in cleaned_data['obj_list']:

                for ap in self.aps_forms:
                    ap_set = cleaned_data["ap_%d_set" % ap.id]
                    ap_val = cleaned_data["ap_%d" % ap.id]
                    if ap_set:
                        try:
                            apv = att.attendeepropertyvalue_set.filter(property=ap).last()
                        except:
                            apv = None

                        update_property(request, ap, apv, ap_val, "attendee-property-%d", AttendeePropertyValue,
                            {"attendee": att, "author": request.user.profile}, copy_image=False, prelim=False)
                        
        elif request.POST['action'] == '_mailto':
            pass


@method_decorator(login_required, name='__call__')
class PayFeePreview(TeamMgntPermMixin, FormPreview):
    form_template = "registration/payment.html"
    preview_template = "registration/payment_preview.html"



    class MinusZero():
        id = 0

    def parse_params(self, request, s_team):
        team = get_object_or_404(Team, origin__slug=s_team, tournament=request.user.profile.tournament)

        self.team = team

        fields = {}

        accounts = Account.objects.filter(owners__tournament=team.tournament, owners=request.user.profile.active).distinct()
        if accounts.count() > 0:
            account = forms.ModelChoiceField(accounts, required=False)
            fields["account"]=account

        new_account_name = forms.CharField(max_length=100, label="if wanted, new account name", required=False)
        fields["new_account"] = new_account_name

        def clean(self):
            cleaned_data = super(self.__class__, self).clean()
            #print(cleaned_data)
            if cleaned_data.get("account",None) == None and cleaned_data['new_account']=='':
                raise forms.ValidationError("You have to choose an Account or enter a new name")

        fields["clean"] = clean

        fees = expected_fees(team)
        for fee in fees:
            chk = forms.BooleanField(required=False, initial=True, label="%s : %.2f €"%(fee["name"],fee["amount"]) )

            ep = None
            if fee['type'] == Payment.TEAM:
                ep = Payment.objects.filter(sender__in=accounts, ref_type=fee["type"], ref_team=team).first()
            elif fee['type'] == Payment.ROLE:
                ep = Payment.objects.filter(sender__in=accounts, ref_type=fee["type"], ref_role=fee["role"], ref_attendee=fee["attendee"]).first()
            elif fee['type'] == Payment.PROPERTY:
                ep = Payment.objects.filter(sender__in=accounts, ref_type=fee["type"], ref_property=fee["property"],ref_attendee=fee["attendee"]).first()
            if ep:
                chk.help_text="already invoiced to account %d %s"%(ep.sender.id, ep.sender)
                chk.initial=False

            fields["fee_%s_%d_%d_%d"%(fee["type"],fee.get("attendee",self.MinusZero()).id,fee.get("role",self.MinusZero()).id,fee.get("property",self.MinusZero()).id)] = chk

        self.form = type("FeeForm", (forms.Form,), fields)

    def process_preview(self, request, form, context):

        if "account" in form.cleaned_data:
            context["account"] = form.cleaned_data["account"]
        else:
            context["account"] = {'owners':self.team.get_managers(),'team':self.team,'name':form.cleaned_data["new_account"]}

        ifees = []
        fsum = 0
        fees = expected_fees(self.team)
        for fee in fees:
            if form.cleaned_data["fee_%s_%d_%d_%d" % (fee["type"], fee.get("attendee", self.MinusZero()).id, fee.get("role", self.MinusZero()).id,
                                        fee.get("property", self.MinusZero()).id)]:
                ifees.append(fee)
                fsum += fee["amount"]

        context["fees"] = ifees
        context["fees_sum"] = fsum

    def done(self, request, cleaned_data):

        if "account" in cleaned_data:
            account = cleaned_data["account"]
        else:
            account = Account.objects.create(team=self.team,name=cleaned_data["new_account"])
            account.owners.add(*self.team.get_managers())

        fees = expected_fees(self.team)
        for fee in fees:
            if cleaned_data["fee_%s_%d_%d_%d" % (
                fee["type"], fee.get("attendee", self.MinusZero()).id, fee.get("role", self.MinusZero()).id,
                fee.get("property", self.MinusZero()).id)]:

                py = Payment.objects.create(sender=account,created_by=request.user.profile.active,amount=fee["amount"], reference=fee["name"],
                                       ref_type=fee["type"], receiver=self.team.tournament.bank_default_account, due_at=self.team.tournament.bank_default_due)
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


@method_decorator(login_required, name='__call__')
class ApplyPossibleJurorPreview(FormPreview):

    form_template = "registration/apply_possiblejuror.html"
    preview_template = "registration/apply_possiblejuror_preview.html"

    def parse_params(self, request, t_slug):
        tournament = get_object_or_404(Tournament, slug=t_slug, registration_open__lt=timezone.now(),
                                       registration_close__gt=timezone.now())
        self.tournament = tournament

        experience = forms.ChoiceField(choices=Juror.EXPERIENCES, required=False)

        self.form = type("JurorForm", (forms.Form,), {'experience':experience})

    def process_preview(self, request, form, context):

        context.update(application_propertyvalues(self.tournament,ParticipationRole.objects.get(type=ParticipationRole.JUROR, tournament=self.tournament),request.user.profile))

    def done(self, request, cleaned_data):

        PossibleJuror.objects.get_or_create(person=request.user.profile, tournament=self.tournament, experience=cleaned_data["experience"])

        if self.tournament.registration_notifications.count() > 0:
            send_mail('%s new possible juror application: %s' % (self.tournament.name, request.user.username),
                      '%s %s (%s, %s) applied to %s as possible juror' % (
                      request.user.first_name, request.user.last_name, request.user.username, request.user.email,
                      self.tournament.name), settings.EMAIL_FROM,
                      self.tournament.registration_notifications.all().values_list("active_user__user__email", flat=True),
                      fail_silently=False, )

        return redirect("registration:applications")

@method_decorator(login_required, name='__call__')
class ApplyWtihRolePreview(FormPreview):

    form_template = "registration/apply_participationrole.html"
    preview_template = "registration/apply_participationrole_preview.html"

    def parse_params(self, request, t_slug, role=None):
        tournament = get_object_or_404(Tournament, slug=t_slug, registration_open__lt=timezone.now(),
                                       registration_close__gt=timezone.now())
        self.tournament = tournament

        try:
            initial = tournament.participationrole_set.get(id=role)
        except:
            initial = None

        roles = forms.ModelChoiceField(queryset=ParticipationRole.objects.filter(tournament=tournament).exclude(type__in=[ParticipationRole.TEAM_LEADER, ParticipationRole.TEAM_MANAGER, ParticipationRole.STUDENT]),required=True,
                                                widget=Select2Widget(), initial=initial)

        self.form = type("RoleForm", (forms.Form,), {'role':roles})

    def process_preview(self, request, form, context):

        context["role"] = form.cleaned_data["role"]
        context["tournament"] = self.tournament
        context.update(application_propertyvalues(self.tournament, form.cleaned_data["role"], request.user.profile))

    def done(self, request, cleaned_data):

        Application.objects.create(applicant=request.user.profile, tournament=self.tournament,
                                   participation_role=cleaned_data["role"])

        messages.add_message(request, messages.SUCCESS,
                             "Applied for role %s in tournament %s" % (cleaned_data["role"], self.tournament))

        if self.tournament.registration_notifications.count() > 0:
            send_mail('%s new role application: %s' % (self.tournament.name, request.user.username),
                      '%s %s (%s, %s) applied to %s with role %s' % (
                      request.user.first_name, request.user.last_name, request.user.username, request.user.email,
                      self.tournament.name, cleaned_data["role"].name), settings.EMAIL_FROM,
                      self.tournament.registration_notifications.all().values_list("active_user__user__email", flat=True),
                      fail_silently=False, )

        return redirect("registration:applications")

@method_decorator(login_required, name='__call__')
class ApplyTeamManager(FormPreview):

    form_template = "registration/apply_team.html"
    preview_template = "registration/apply_team_preview.html"

    def parse_params(self, request, t_slug):
        tournament = get_object_or_404(Tournament, slug=t_slug, registration_open__lt=timezone.now(),
                                       registration_close__gt=timezone.now())
        self.tournament = tournament

        name = forms.ModelChoiceField(queryset=Origin.objects.filter(tournament=tournament), required=False)
        new_name = forms.CharField(max_length=300, required=False)

        def clean(self):
            cleaned_data = super(self.__class__, self).clean()
            #print(cleaned_data)
            if cleaned_data["name"] == None and cleaned_data['new_name']=='':
                raise forms.ValidationError("You have to choose a Team or enter a new name")

            if cleaned_data["new_name"]!="" and Origin.objects.filter(tournament=self.tournament, name=cleaned_data["new_name"]).exists():
                raise forms.ValidationError("Team %s alredy registered." % (cleaned_data["new_name"]))

        self.form = type("TeamForm", (forms.Form,), {'name':name, "new_name":new_name,"clean":clean,"tournament":tournament})

    def get_context(self, request, form):
        context = super().get_context(request, form)
        context["tournament"] = self.tournament

        return context

    def process_preview(self, request, form, context):

        origin = None
        if "_newteam" in request.POST:
            origin = form.cleaned_data["new_name"]
            context['action'] = "_new_name"
        else:
            origin = form.cleaned_data["name"].name
            context['action'] = "_name"

        context["origin"] = origin
        context.update(application_propertyvalues(self.tournament, ParticipationRole.objects.get(tournament=self.tournament, type=ParticipationRole.TEAM_MANAGER), request.user.profile))

    def done(self, request, cleaned_data):

        if request.POST['action'] == '_new_name':
            origin = Origin.objects.create(tournament=self.tournament, from_registration=True,
                                       name=cleaned_data["new_name"])
        else:
            origin = cleaned_data["name"]

        Application.objects.create(applicant=request.user.profile, tournament=self.tournament,
                                   participation_role=ParticipationRole.objects.get(tournament=self.tournament,
                                                                                    type=ParticipationRole.TEAM_MANAGER),
                                   origin=origin)

        messages.add_message(request, messages.SUCCESS, "Applied for team %s in tournament %s" % (origin, self.tournament))

        if self.tournament.registration_notifications.count() > 0:
            send_mail('%s new team application: %s' % (self.tournament.name, origin.name),
                      '%s %s (%s, %s) applied to %s with team %s' % (
                      request.user.first_name, request.user.last_name, request.user.username, request.user.email,
                      self.tournament.name, origin.name), settings.EMAIL_FROM,
                      self.tournament.registration_notifications.all().values_list("active_user__user__email", flat=True),
                      fail_silently=False, )
        return redirect("registration:applications")

@method_decorator(login_required, name='__call__')
class ApplyTeamMember(FormPreview):

    form_template = "registration/apply_teammember.html"
    preview_template = "registration/apply_teammember_preview.html"

    def parse_params(self, request, t_slug, role=None, visitor=None):
        tournament = get_object_or_404(Tournament, slug=t_slug, registration_open__lt=timezone.now(),
                                       registration_close__gt=timezone.now())
        self.tournament = tournament

        try:
            initial = tournament.teamrole_set.get(id=role)
        except:
            initial = None

        team = forms.ModelChoiceField(queryset=Team.objects.filter(tournament=tournament))
        password = forms.CharField(widget=forms.PasswordInput)
        #print("visitor:")
        #print(visitor)


        error_messages = {'invalid_login': "Please enter a correct password for team %(team)s.",
                          'inactive': "This account is inactive.", }

        #print(role)

        def clean_role(self):
            data = self.cleaned_data['role']
            #print("in clean")
            #print(data)
            return data

        def clean(self):
            password = self.cleaned_data.get('password')

            team = self.cleaned_data.get("team")

            if team and password:
                valid = check_password(password, team.join_password)

                if not valid:
                    raise forms.ValidationError(self.error_messages['invalid_login'], code='invalid_login',
                        params={'team': team}, )

            return self.cleaned_data

        if not visitor:
            role = forms.ModelChoiceField(queryset=TeamRole.objects.filter(tournament=tournament).exclude(type=TeamRole.ASSOCIATED), initial=initial)
            self.form = type("TeamForm", (forms.Form,),
                             {'team': team, "password": password, "clean": clean, "tournament": tournament,
                              "role": role, "error_messages": error_messages})
            #print("use tm form")
        else:
            assro = TeamRole.objects.filter(tournament=tournament,type=TeamRole.ASSOCIATED)
            vis = forms.CharField(initial="Visitor", label="Role", disabled=True, required=False)
            self.form = type("VisitorForm", (forms.Form,),
                             {'team': team, "password": password, "clean": clean, "clean_role":clean_role, "tournament": tournament,
                              "role": vis, "error_messages": error_messages})
            #print("use vis form")


    def get_context(self, request, form):
        context = super().get_context(request, form)
        context["tournament"] = self.tournament

        return context

    def process_preview(self, request, form, context):

        context["role"] = form.cleaned_data["role"]
        context["origin"] = form.cleaned_data["team"].origin

        if type(form.cleaned_data["role"]) == str:
            #application as visitor
            context.update(
                application_propertyvalues(self.tournament, ParticipationRole.objects.get(tournament=self.tournament, type=ParticipationRole.VISITOR),
                                           request.user.profile))
        else:
            context.update(application_propertyvalues(self.tournament, form.cleaned_data["role"].participation_roles.first(), request.user.profile))

    def done(self, request, cleaned_data):

        team = cleaned_data["team"]

        if type(cleaned_data["role"]) == str:
            prole = ParticipationRole.objects.get(tournament=self.tournament, type=ParticipationRole.VISITOR)
            trole = TeamRole.objects.filter(tournament=self.tournament, type=TeamRole.ASSOCIATED).first()
        else:
            prole = cleaned_data["role"].participation_roles.first()
            trole = cleaned_data["role"]
        Application.objects.create(applicant=request.user.profile, tournament=self.tournament,
                                   participation_role=prole,
                                   team=team,
                                   team_role=trole)
        messages.add_message(request, messages.SUCCESS,
                             "Applied for team %s in tournament %s" % (team.origin, self.tournament))

        if team.notify_applications:
            send_mail('%s applied to be a member of your team %s' % (request.user.username, team.origin.name),
                      '%s %s (%s, %s) applied to team %s with role %s' % (
                      request.user.first_name, request.user.last_name, request.user.username, request.user.email,
                      team.origin.name, trole), settings.EMAIL_FROM,
                      team.teammember_set.filter(attendee__roles__type=ParticipationRole.TEAM_MANAGER).values_list(
                          "attendee__active_user__user__email", flat=True), fail_silently=False, )

        return redirect("registration:applications")
