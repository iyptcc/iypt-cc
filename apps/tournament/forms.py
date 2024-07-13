import pytz
from django import forms
from django.contrib.auth.models import Group, Permission
from django_select2.forms import Select2MultipleWidget, Select2Widget
from pytz import timezone

from apps.account.models import ActiveUser, ApiUser, Attendee, ParticipationRole
from apps.bank.models import Account
from apps.dashboard.datetimefield import DateTimeFieldNonTZ
from apps.dashboard.datetimepicker import DateTimePicker
from apps.postoffice.models import DefaultTemplate as DefaultMailTemplate
from apps.postoffice.models import Template as MailTemplate
from apps.printer.models import DefaultTemplate, FileServer, Pdf, Template
from apps.registration.models import (
    ApplicationQuestion,
    AttendeeProperty,
    Property,
    PropertyChoice,
)
from apps.team.models import TeamRole

from ..virtual.models import BBBInstance
from .models import Origin, Tournament
from .utils import _more_perm_than_group


class FileImportForm(forms.Form):

    input = forms.CharField(widget=forms.Textarea)


class GroupEditForm(forms.ModelForm):

    def __init__(self, attendee, *args, **kwargs):
        super(GroupEditForm, self).__init__(*args, **kwargs)
        ids = []
        allperm = list(attendee.active_user.user.get_all_permissions())
        for p in allperm:
            pp = p.split(".")
            ids.append(
                Permission.objects.get(
                    content_type__app_label=pp[0], codename=".".join(pp[1:])
                ).id
            )

        print(ids)
        self.fields["permissions"].queryset = Permission.objects.filter(
            pk__in=ids
        ).prefetch_related("content_type")

    class Meta:
        model = Group
        fields = ["name", "permissions"]

        widgets = {"permissions": Select2MultipleWidget()}


class ApiUserEditForm(forms.ModelForm):

    def __init__(self, attendee, *args, **kwargs):
        super(ApiUserEditForm, self).__init__(*args, **kwargs)
        ids = []
        for g in attendee.tournament.groups.all():
            if _more_perm_than_group(attendee.active_user.user, g):
                ids.append(g.id)
        self.fields["groups"].queryset = Group.objects.filter(pk__in=ids)

    class Meta:
        model = ApiUser
        fields = ["username", "groups"]

        widgets = {"groups": Select2MultipleWidget()}


class ADEditForm(forms.ModelForm):

    def __init__(self, trn, *args, **kwargs):
        super(ADEditForm, self).__init__(*args, **kwargs)
        self.fields["required"].queryset = ParticipationRole.objects.filter(
            tournament=trn
        )
        self.fields["optional"].queryset = ParticipationRole.objects.filter(
            tournament=trn
        )
        self.fields["apply_required"].queryset = ParticipationRole.objects.filter(
            tournament=trn
        )
        self.fields["required_if"].queryset = AttendeeProperty.objects.filter(
            tournament=trn, type=Property.BOOLEAN
        )

    class Meta:
        model = AttendeeProperty
        fields = [
            "name",
            "type",
            "required",
            "optional",
            "edit_deadline",
            "user_property",
            "edit_multi",
            "apply_required",
            "hidden",
            "data_utilisation",
            "required_if",
            "manager_confirmed",
        ]

        widgets = {
            "type": Select2Widget(),
            "required": Select2MultipleWidget(),
            "optional": Select2MultipleWidget(),
            "apply_required": Select2MultipleWidget(),
            "required_if": Select2Widget(),
        }


class AQEditForm(forms.ModelForm):

    def __init__(self, trn, *args, **kwargs):
        super(AQEditForm, self).__init__(*args, **kwargs)
        try:
            self.fields["required_if"].queryset = ApplicationQuestion.objects.filter(
                role=self.instance.role, type=ApplicationQuestion.BOOLEAN
            )
        except:
            self.fields["required_if"].queryset = ApplicationQuestion.objects.none()

    class Meta:
        model = ApplicationQuestion
        fields = ["name", "short_name", "type", "help_text", "required_if", "active"]

        widgets = {
            "type": Select2Widget(),
        }


class OriginForm(forms.ModelForm):
    class Meta:
        model = Origin
        fields = [
            "name",
            "alpha2iso",
            "flag",
            "timezone",
            "short",
            "flag_pdf",
            "publish_participation",
            "possible_managers",
        ]

        widgets = {"possible_managers": Select2MultipleWidget()}

    def __init__(self, actuser, *args, **kwargs):
        super(OriginForm, self).__init__(*args, **kwargs)

        mgr_ids = set()
        atts = actuser.attendee_set.all()
        for att in atts:
            if att.has_permission("account.view_all_persons"):
                newau = set(
                    att.tournament.attendee_set.all().values_list(
                        "active_user__id", flat=True
                    )
                )
                mgr_ids.update(newau)
        self.fields["possible_managers"].queryset = ActiveUser.objects.filter(
            id__in=mgr_ids
        )

        tzs = [(None, "-----")] + [(a, a) for a in pytz.all_timezones]
        self.fields["timezone"] = forms.ChoiceField(
            choices=tzs, required=False, widget=Select2Widget()
        )
        self.fields["timezone"].initial = self.instance.timezone


class PropertyChoiceForm(forms.ModelForm):
    class Meta:
        model = PropertyChoice
        fields = ("name",)


PropertyChoiceFormSet = forms.inlineformset_factory(
    AttendeeProperty, PropertyChoice, PropertyChoiceForm, extra=2
)


class RoleEditForm(forms.ModelForm):

    def __init__(self, trn, *args, **kwargs):
        super(RoleEditForm, self).__init__(*args, **kwargs)
        self.fields["groups"].queryset = trn.groups.all()
        self.fields["approvable_by"].queryset = trn.participationrole_set.all()
        # self.fields['optional'].queryset = ParticipationRole.objects.filter(tournament=trn)

        opts = {"format": "YYYY-MM-DDTHH:mmZZ", "sideBySide": True}
        try:
            tz = trn.timezone
            if not tz == None:
                opts["timeZone"] = tz
        except:
            pass

        self.fields["application_deadline"].widget = DateTimePicker(
            format="%Y-%m-%dT%H:%M%z", options=opts
        )

    class Meta:
        model = ParticipationRole
        fields = [
            "name",
            "type",
            "groups",
            "approvable_by",
            "global_limit",
            "attending",
            "require_possiblejuror",
            "application_deadline",
            "virtual_room_role",
            "virtual_name_tag",
            "virtual_show_team",
        ]

        widgets = {
            "type": Select2Widget(),
            "virtual_room_role": Select2Widget(),
            "groups": Select2MultipleWidget(),
            "approvable_by": Select2MultipleWidget(),
        }

        field_classes = {"application_deadline": DateTimeFieldNonTZ}


class TRoleEditForm(forms.ModelForm):

    def __init__(self, trn, *args, **kwargs):
        super(TRoleEditForm, self).__init__(*args, **kwargs)
        self.fields["participation_roles"].queryset = ParticipationRole.objects.filter(
            tournament=trn
        )
        # self.fields['optional'].queryset = ParticipationRole.objects.filter(tournament=trn)

    class Meta:
        model = TeamRole
        fields = ["name", "type", "participation_roles", "members_min", "members_max"]

        widgets = {
            "type": Select2Widget(),
            "participation_roles": Select2MultipleWidget(),
        }


class TemplateSettingsForm(forms.Form):

    def __init__(self, tournament, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for type in Template.TYPE:
            self.fields["default_template_%s" % type[0]] = forms.ModelChoiceField(
                Template.objects.filter(tournament=tournament, type=type[0]),
                label="Default %s template" % type[1],
                required=False,
            )
            try:
                tp = DefaultTemplate.objects.get(
                    tournament=tournament, type=type[0]
                ).template
                self.fields["default_template_%s" % type[0]].initial = tp
            except Exception as e:
                pass


class MailTemplateSettingsForm(forms.Form):

    def __init__(self, tournament, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for type in MailTemplate.TYPE:
            self.fields["default_mail_template_%s" % type[0]] = forms.ModelChoiceField(
                MailTemplate.objects.filter(tournament=tournament, type=type[0]),
                label="Default %s template" % type[1],
                required=False,
            )
            try:
                tp = DefaultMailTemplate.objects.get(
                    tournament=tournament, type=type[0]
                ).template
                self.fields["default_mail_template_%s" % type[0]].initial = tp
            except Exception as e:
                pass


class RegistrationSettingsForm(forms.ModelForm):

    class Meta:

        model = Tournament

        fields = [
            "registration_open",
            "registration_close",
            "registration_notifications",
            "registration_apply_team",
            "registration_apply_newteam",
            "registration_teamleaderjurors_required",
            "registration_teamleaderjurors_required_guest",
            "possiblejuror_ask_experience",
            "possiblejuror_ask_occupation",
            "possiblejuror_ask_remark",
            "possiblejuror_reapply",
        ]

        field_classes = {
            "registration_open": DateTimeFieldNonTZ,
            "registration_close": DateTimeFieldNonTZ,
        }

        widgets = {"registration_notifications": Select2MultipleWidget()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        opts = {"format": "YYYY-MM-DDTHH:mmZZ", "sideBySide": True}
        try:
            tz = self.instance.timezone
            if not tz == None:
                opts["timeZone"] = tz
        except:
            pass

        for field in self.fields.values():
            if isinstance(field, DateTimeFieldNonTZ):
                field.widget = DateTimePicker(format="%Y-%m-%dT%H:%M%z", options=opts)

        self.fields["registration_notifications"].queryset = Attendee.objects.filter(
            tournament=self.instance
        ).prefetch_related("active_user__user")
        self.fields["registration_notifications"].required = False


class FeedbackSettingsForm(forms.ModelForm):

    class Meta:

        model = Tournament

        fields = ["feedback_permitted_roles", "feedback_locked_by_assistants"]

        widgets = {"feedback_permitted_roles": Select2MultipleWidget()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["feedback_permitted_roles"].queryset = TeamRole.objects.filter(
            tournament=self.instance
        )
        self.fields["feedback_permitted_roles"].required = False


class ScrubExceptForm(forms.Form):
    attendeproperty = forms.ModelMultipleChoiceField(
        AttendeeProperty.objects.none(), required=False, widget=Select2MultipleWidget()
    )
    applicationquestion = forms.ModelMultipleChoiceField(
        ApplicationQuestion.objects.none(),
        required=False,
        widget=Select2MultipleWidget(),
    )

    def __init__(self, trn, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["attendeproperty"].queryset = AttendeeProperty.objects.filter(
            tournament=trn
        )
        self.fields["applicationquestion"].queryset = (
            ApplicationQuestion.objects.filter(role__tournament=trn)
        )


class BankSettingsForm(forms.ModelForm):

    class Meta:

        model = Tournament

        fields = [
            "bank_default_account",
            "bank_default_due",
            "bank_default_contingency_days",
            "bank_expected_fee",
            "bank_generate_invoice",
        ]

        field_classes = {
            "bank_default_due": DateTimeFieldNonTZ,
        }

        widgets = {"bank_default_account": Select2Widget()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        opts = {"format": "YYYY-MM-DDTHH:mmZZ", "sideBySide": True}
        try:
            tz = self.instance.timezone
            if not tz == None:
                opts["timeZone"] = tz
        except:
            pass

        for field in self.fields.values():
            if isinstance(field, DateTimeFieldNonTZ):
                field.widget = DateTimePicker(format="%Y-%m-%dT%H:%M%z", options=opts)

        self.fields["bank_default_account"].queryset = Account.objects.filter(
            owners__tournament=self.instance
        ).distinct()
        self.fields["bank_default_account"].required = False


class TournamentForm(forms.ModelForm):

    class Meta:

        model = Tournament

        fields = [
            "allowed_rejections",
            "timezone",
            "logo",
            "draw_wide",
            "date_start",
            "date_end",
            "aypt_limited_problems",
            "oypt_multiple_oppositions",
            "fight_room_guest_policy",
            "fight_room_public_role",
            "results_help_html",
            "public_clock",
        ]

        widgets = {
            "date_start": DateTimePicker(
                format="%Y-%m-%d", options={"format": "YYYY-MM-DD"}
            ),
            "date_end": DateTimePicker(
                format="%Y-%m-%d", options={"format": "YYYY-MM-DD"}
            ),
            "fight_room_guest_policy": Select2Widget(),
            "fight_room_public_role": Select2Widget(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["allowed_rejections"].label = (
            "Allowed rejections without 0.2 presentation penalty"
        )
        self.fields["allowed_rejections"].min_value = 0

        tzs = [(None, "-----")] + [(a, a) for a in pytz.all_timezones]
        self.fields["timezone"] = forms.ChoiceField(
            choices=tzs, required=False, widget=Select2Widget()
        )
        self.fields["timezone"].initial = self.instance.timezone


class JurySettingsForm(forms.ModelForm):

    class Meta:

        model = Tournament

        fields = [
            "publish_juror_availability",
            "publish_juror_conflicting",
            "publish_partial_grades",
            "jury_opt_weight_assignmentbalance",
            "jury_opt_weight_expassignmentbalance",
            "jury_opt_weight_teamandchairmeettwice",
            "jury_opt_weight_teamandjurormeetmultiple",
            "jury_opt_weight_jurysamecountry",
            "jury_opt_weight_bias",
            "jury_chair_maximum_meet_origin",
            "jurors_enter_grades",
            "fa_show_grades",
            "room_show_grades",
            "grading_sheet_pdf",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["grading_sheet_pdf"].queryset = Pdf.objects.filter(
            tournament=self.instance
        )


class BBBForm(forms.ModelForm):
    class Meta:
        model = BBBInstance
        fields = ("name", "api_url")

    new_secret = forms.CharField(required=False, widget=forms.widgets.PasswordInput)


class FileServerForm(forms.ModelForm):
    class Meta:
        model = FileServer
        fields = ("name", "hostname", "port", "username", "fingerprint")

    new_password = forms.CharField(required=False, widget=forms.widgets.PasswordInput)
