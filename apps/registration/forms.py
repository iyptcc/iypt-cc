from datetime import datetime

from django import forms
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import Group
from django.db.models import Q
from django_select2.forms import Select2MultipleWidget
from pytz import timezone

from apps.account.models import ActiveUser, ParticipationRole
from apps.jury.models import Juror
from apps.printer.models import Template
from apps.registration.models import AttendeeProperty, AttendeePropertyValue, Property, UserProperty, UserPropertyValue
from apps.team.models import Team, TeamRole
from apps.tournament.models import Origin, Tournament

from .utils import field_for_property, set_initial_from_valueobject, update_property


class AcceptTeamForm(forms.Form):

    origin = forms.CharField()
    name = forms.CharField(max_length=200, disabled=True)
    email = forms.EmailField(max_length=200, disabled=True)

    competing = forms.BooleanField(initial=True, required=False)

    notify = forms.BooleanField(required=False,label="Notify Applicant", initial=True)

    def __init__(self, application, *args, **kwargs):
        super(AcceptTeamForm, self).__init__(*args, **kwargs)

        self.fields["origin"].initial = application.origin.name
        self.fields["name"].initial = "%s %s" % (application.applicant.user.first_name, application.applicant.user.last_name)
        self.fields["email"].initial = application.applicant.user.email

class AcceptRoleForm(forms.Form):

    name = forms.CharField(disabled=True)
    email = forms.CharField(disabled=True)
    role = forms.ModelChoiceField(ParticipationRole.objects.none())

    notify = forms.BooleanField(required=False, label="Notify Applicant", initial=True)

    def __init__(self, application, *args, **kwargs):
        super(AcceptRoleForm, self).__init__(*args, **kwargs)

        self.fields["name"].initial = "%s %s"%(application.applicant.user.first_name, application.applicant.user.last_name,)
        self.fields["email"].initial = application.applicant.user.email
        #self.fields["leader"].queryset = Attendee.objects.filter(Q(tournament=application.tournament) | Q(id=application.applicant.id) )
        self.fields["role"].queryset = ParticipationRole.objects.filter(tournament=application.tournament)
        self.fields["role"].initial = application.participation_role

class DeclineRoleForm(forms.Form):

    name = forms.CharField(disabled=True)
    email = forms.CharField(disabled=True)
    role = forms.CharField(disabled=True)

    decline_reason = forms.CharField(widget=forms.Textarea)

    notify = forms.BooleanField(required=False, label="Notify Applicant", initial=True)

    def __init__(self, application, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["name"].initial = "%s %s"%(application.applicant.user.first_name, application.applicant.user.last_name,)
        self.fields["email"].initial = application.applicant.user.email
        #self.fields["leader"].queryset = Attendee.objects.filter(Q(tournament=application.tournament) | Q(id=application.applicant.id) )
        #self.fields["role"].queryset = ParticipationRole.objects.filter(tournament=application.tournament)
        self.fields["role"].initial = application.participation_role.get_type_display()

class DeclineTeamForm(forms.Form):

    origin = forms.CharField()
    name = forms.CharField(max_length=200, disabled=True)
    email = forms.EmailField(max_length=200, disabled=True)

    decline_reason = forms.CharField(widget=forms.Textarea)

    notify = forms.BooleanField(required=False, label="Notify Applicant", initial=True)

    def __init__(self, application, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["origin"].initial = application.origin.name
        self.fields["name"].initial = "%s %s" % (
        application.applicant.user.first_name, application.applicant.user.last_name)
        self.fields["email"].initial = application.applicant.user.email

class TeamSettingsForm(forms.ModelForm):

    class Meta:

        model = Team

        fields = ['join_password', 'notify_applications']

        widgets = {'join_password': forms.PasswordInput}

    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.oldpw = self.instance.join_password
        self.fields["join_password"].label="Join Password (leave blank to keep existing password)"

    def save(self, commit=True):
        team = super().save(commit=False)
        if team.join_password != "":
            team.join_password = make_password(team.join_password)
        else:
            team.join_password = self.oldpw
        if commit:
            team.save()

class ApplyForTeamForm(forms.Form):
    team = forms.ModelChoiceField(queryset=Team.objects.none())
    password = forms.CharField(widget=forms.PasswordInput)

    error_messages = {'invalid_login': "Please enter a correct password for team %(team)s.",
        'inactive': "This account is inactive.", }

    def __init__(self, tournament, *args, **kwargs):
        super(ApplyForTeamForm, self).__init__(*args, **kwargs)

        self.fields["team"].queryset = Team.objects.filter(tournament=tournament)

    def clean(self):
        password = self.cleaned_data.get('password')

        team = self.cleaned_data.get("team")

        if team and password:
            valid = check_password(password ,team.join_password)

            if not valid:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'team': team},
                )

        return self.cleaned_data

class AttendeePropertyForm(forms.Form):

    def __init__(self, attendee, read_profile=False, hidden=False, *args, **kwargs):
        super(AttendeePropertyForm, self).__init__(*args, **kwargs)

        self.hidden = hidden
        self.attendee = attendee

        if self.hidden:
            att_properties = AttendeeProperty.objects.filter(tournament=attendee.tournament)
        else:
            att_properties = AttendeeProperty.user_objects.filter(tournament=attendee.tournament)

        for ap in att_properties:
            if len(attendee.roles.all() & ap.required.all()):
                ls = "required"
            elif len(attendee.roles.all() & ap.optional.all()):
                ls = "optional"
            elif ap.hidden == True:
                ls = "hidden"
            else:
                continue

            try:
                dep_ap = ap.required_if
                depcheck = AttendeePropertyValue.objects.filter(attendee=attendee, property=dep_ap).last().bool_value
                if depcheck == True:
                    ls = "required, because %s is true"%dep_ap.name
            except:
                pass

            copied = ""
            valueo = None
            try:
                valueo = AttendeePropertyValue.unconfirmed.filter(attendee=attendee, property=ap).last()
                if (not valueo) and read_profile and ap.user_property:
                    valueo = UserPropertyValue.objects.filter(user=attendee.active_user,
                                                              property=ap.user_property).last()
                    copied = ", copied from profile"
            except:
                pass

            t = ap.type
            if ap.user_property:
                t = ap.user_property.type
                ls+=copied

            if ap.manager_confirmed:
                try:
                    valueconf = AttendeePropertyValue.objects.filter(attendee=attendee, property=ap).last()
                    if valueconf != valueo:
                        ls += ", confirmed value: %s"%getattr(valueconf, valueconf.field_name[t])
                except:
                    pass

            field = field_for_property(ap, ls)


            if valueo:
                if copied != "":
                    setattr(field, "copied_from_profile", True)
                set_initial_from_valueobject(field, t, valueo)

            self.fields["attendee-property-%d" % ap.id] = field


        #self.fields['first_name'].initial = activeUser.user.first_name
        #self.fields['last_name'].initial = activeUser.user.last_name

    def save(self, request):
        att = self.attendee
        if self.hidden:
            att_properties = AttendeeProperty.objects.filter(tournament=att.tournament)
        else:
            att_properties = AttendeeProperty.user_objects.filter(tournament=att.tournament)

        for ap in att_properties:
            if not (len(att.roles.all() & ap.required.all()) or len(att.roles.all() & ap.optional.all()) or ap.hidden==True):
                continue

            value = self.cleaned_data["attendee-property-%d" % ap.id]
            field = self.fields["attendee-property-%d" % ap.id]
            apv = None
            t = ap.type
            property = ap
            if ap.user_property:
                t = ap.user_property.type
                property = ap.user_property

            try:
                apv = AttendeePropertyValue.objects.filter(attendee=att, property=ap).last()
            except:
                pass

            copy_image =False
            if hasattr(field,"copied_from_profile"):
                if field.copied_from_profile != None:
                    copy_image = True

            prelim = False
            if ap.manager_confirmed and request.user.profile.active.roles.filter(type=ParticipationRole.STUDENT).exists():
                print("has to be confirmed")
                if not request.user.profile.active.teammember_set.filter(manager=True).exists():
                    print("create prelim save")
                    prelim = True
            update_property(request, ap, apv, value, "attendee-property-%d", AttendeePropertyValue,
                            {"attendee": att, "author": request.user.profile}, copy_image=copy_image, prelim=prelim)


class AcceptMemberForm(forms.Form):

    name = forms.CharField(max_length=200, disabled=True)
    email = forms.EmailField(max_length=200, disabled=True)
    role = forms.ModelChoiceField(TeamRole.objects.none())

    notify = forms.BooleanField(required=False, label="Notify Applicant", initial=True)

    def __init__(self, application, *args, **kwargs):
        super(AcceptMemberForm, self).__init__(*args, **kwargs)

        self.fields["name"].initial = "%s %s"%(application.applicant.user.first_name, application.applicant.user.last_name)
        self.fields["email"].initial = application.applicant.user.email
        self.fields["role"].queryset = TeamRole.objects.filter(tournament=application.tournament)
        self.fields["role"].initial = application.team_role

class EditMemberForm(forms.Form):

    name = forms.CharField(max_length=200, disabled=True)
    role = forms.ModelChoiceField(TeamRole.objects.none())
    manager = forms.BooleanField(required=False)

    def __init__(self, tm, *args, **kwargs):
        super(EditMemberForm, self).__init__(*args, **kwargs)

        self.fields["name"].initial = "%s %s"%(tm.attendee.first_name, tm.attendee.last_name)
        self.fields["role"].queryset = TeamRole.objects.filter(tournament=tm.attendee.tournament)
        self.fields["role"].initial = tm.role
        self.fields["manager"].initial = tm.manager
        try:
            if tm.role.type == TeamRole.LEADER:
                pj = tm.attendee.active_user.possiblejuror_set.get(tournament=tm.attendee.tournament)
                if pj.approved_by is not None:
                    jf = forms.BooleanField(required=False, label="Active as Juror")
                    jf.initial=tm.attendee.roles.filter(type=ParticipationRole.JUROR).exists()
                    self.fields["juror"] = jf
        except Exception as e:
            print(e)
            pass
