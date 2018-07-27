import pytz
from django import forms
from django.contrib.auth.models import Group, Permission
from django_select2.forms import Select2MultipleWidget, Select2Widget
from pytz import timezone

from apps.account.models import Attendee, ParticipationRole
from apps.bank.models import Account
from apps.dashboard.datetimefield import DateTimeFieldNonTZ
from apps.dashboard.datetimepicker import DateTimePicker
from apps.printer.models import DefaultTemplate, Template
from apps.registration.models import AttendeeProperty, Property, PropertyChoice
from apps.team.models import TeamRole

from .models import Tournament


class GroupEditForm(forms.ModelForm):

    def __init__(self,attendee, *args, **kwargs):
        super(GroupEditForm, self).__init__(*args, **kwargs)
        ids = []
        allperm = list(attendee.active_user.user.get_all_permissions())
        for p in allperm:
            pp = p.split(".")
            ids.append(Permission.objects.get(content_type__app_label=pp[0], codename=".".join(pp[1:])).id)

        print(ids)
        self.fields['permissions'].queryset = Permission.objects.filter(pk__in=ids).prefetch_related("content_type")


    class Meta:
        model = Group
        fields = ['name', 'permissions']

        widgets = {
            'permissions': Select2MultipleWidget()
        }

class ADEditForm(forms.ModelForm):

    def __init__(self,trn, *args, **kwargs):
        super(ADEditForm, self).__init__(*args, **kwargs)
        self.fields['required'].queryset = ParticipationRole.objects.filter(tournament=trn)
        self.fields['optional'].queryset = ParticipationRole.objects.filter(tournament=trn)
        self.fields['apply_required'].queryset = ParticipationRole.objects.filter(tournament=trn)
        self.fields['required_if'].queryset = AttendeeProperty.objects.filter(tournament=trn, type=Property.BOOLEAN)

    class Meta:
        model = AttendeeProperty
        fields = ['name', 'type', 'required','optional','edit_deadline', 'user_property', 'apply_required',"hidden", "data_utilisation", 'required_if', 'manager_confirmed']

        widgets = {
            'type': Select2Widget(),
            'required': Select2MultipleWidget(),
            'optional': Select2MultipleWidget(),
            'apply_required': Select2MultipleWidget(),
            'required_if': Select2Widget(),
        }

class PropertyChoiceForm(forms.ModelForm):
    class Meta:
        model = PropertyChoice
        fields = ("name",)

PropertyChoiceFormSet = forms.inlineformset_factory(AttendeeProperty,PropertyChoice, PropertyChoiceForm, extra=2)

class RoleEditForm(forms.ModelForm):

    def __init__(self,trn, *args, **kwargs):
        super(RoleEditForm, self).__init__(*args, **kwargs)
        self.fields['groups'].queryset = trn.groups.all()
        self.fields['approvable_by'].queryset = trn.participationrole_set.all()
        #self.fields['optional'].queryset = ParticipationRole.objects.filter(tournament=trn)

    class Meta:
        model = ParticipationRole
        fields = ['name', 'type', 'groups','approvable_by','global_limit', 'attending']

        widgets = {
            'type': Select2Widget(),
            'groups': Select2MultipleWidget(),
            'approvable_by': Select2MultipleWidget(),
        }

class TRoleEditForm(forms.ModelForm):

    def __init__(self,trn, *args, **kwargs):
        super(TRoleEditForm, self).__init__(*args, **kwargs)
        self.fields['participation_roles'].queryset = ParticipationRole.objects.filter(tournament=trn)
        #self.fields['optional'].queryset = ParticipationRole.objects.filter(tournament=trn)

    class Meta:
        model = TeamRole
        fields = ['name', 'type', 'participation_roles', 'members_min', 'members_max']

        widgets = {
            'type': Select2Widget(),
            'participation_roles': Select2MultipleWidget(),
        }

class TemplateSettingsForm(forms.Form):

    def __init__(self, tournament, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for type in Template.TYPE:
            self.fields["default_template_%s"%type[0]] = forms.ModelChoiceField(
                Template.objects.filter(tournament=tournament, type=type[0]), label="Default %s template"%type[1], required=False)
            try:
                tp = DefaultTemplate.objects.get(tournament=tournament, type=type[0]).template
                self.fields["default_template_%s"%type[0]].initial = tp
            except Exception as e:
                pass

class RegistrationSettingsForm(forms.ModelForm):

    class Meta:

        model = Tournament

        fields = ['registration_open', 'registration_close', 'registration_notifications', 'registration_apply_team', "registration_apply_newteam", "registration_teamleaderjurors_required", "registration_teamleaderjurors_required_guest"]

        field_classes = {'registration_open': DateTimeFieldNonTZ,
                         'registration_close': DateTimeFieldNonTZ,}

        widgets = {"registration_notifications": Select2MultipleWidget()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)

        opts = {"format": "YYYY-MM-DDTHH:mmZZ", "sideBySide": True}
        try:
            tz = self.instance.timezone
            if not tz == None:
                opts["timeZone"] = tz
        except:
            pass

        for field in self.fields.values():
            if isinstance(field,DateTimeFieldNonTZ):
                field.widget = DateTimePicker(format='%Y-%m-%dT%H:%M%z', options=opts)


        self.fields["registration_notifications"].queryset = Attendee.objects.filter(tournament=self.instance).prefetch_related("active_user__user")
        self.fields["registration_notifications"].required = False

class BankSettingsForm(forms.ModelForm):

    class Meta:

        model = Tournament

        fields = ['bank_default_account', 'bank_default_due']

        field_classes = {'bank_default_due': DateTimeFieldNonTZ,}

        widgets = {"bank_default_account": Select2Widget()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)

        opts = {"format": "YYYY-MM-DDTHH:mmZZ", "sideBySide": True}
        try:
            tz = self.instance.timezone
            if not tz == None:
                opts["timeZone"] = tz
        except:
            pass

        for field in self.fields.values():
            if isinstance(field,DateTimeFieldNonTZ):
                field.widget = DateTimePicker(format='%Y-%m-%dT%H:%M%z', options=opts)


        self.fields["bank_default_account"].queryset = Account.objects.filter(owners__tournament=self.instance)
        self.fields["bank_default_account"].required = False


class TournamentForm(forms.ModelForm):

    class Meta:

        model = Tournament

        fields = ['allowed_rejections', 'timezone','logo', 'draw_wide']

        field_classes = {}


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["allowed_rejections"].label = "Allowed rejections without 0.2 presentation penalty"
        self.fields["allowed_rejections"].min_value=0

        tzs = [(None,"-----")]+[(a,a) for a in pytz.all_timezones]
        self.fields["timezone"] = forms.ChoiceField(choices=tzs, required=False, widget=Select2Widget())
        self.fields["timezone"].initial = self.instance.timezone

class JurySettingsForm(forms.ModelForm):

    class Meta:

        model = Tournament

        fields = ['jury_opt_weight_assignmentbalance', 'jury_opt_weight_expassignmentbalance','jury_opt_weight_teamandchairmeettwice','jury_opt_weight_teamandjurormeetmultiple','jury_opt_weight_jurysamecountry','jury_opt_weight_bias']
