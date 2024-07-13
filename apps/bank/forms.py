from django import forms
from django_select2.forms import Select2MultipleWidget, Select2Widget

from apps.account.models import Attendee, ParticipationRole
from apps.dashboard.datetimefield import DateTimeFieldNonTZ
from apps.dashboard.datetimepicker import DateTimePicker
from apps.printer.models import Pdf, Template
from apps.registration.models import AttendeeProperty
from apps.team.models import Team
from apps.tournament.models import Tournament

from .models import Account, Payment, PropertyFee


class AccountForm(forms.ModelForm):

    class Meta:
        model = Account
        fields = ("owners", "team", "name")

        widgets = {"owners": Select2MultipleWidget, "team": Select2Widget}

    def __init__(self, trn, *args, **kwargs):
        team = None
        owners = []
        if "team" in kwargs:
            team = kwargs["team"]
            del kwargs["team"]
        if "owners" in kwargs:
            owners = kwargs["owners"]
            del kwargs["owners"]

        super().__init__(*args, **kwargs)

        self.tournament = trn

        self.fields["team"].queryset = Team.objects.filter(tournament=trn)
        self.fields["owners"].queryset = Attendee.objects.filter(
            tournament=trn
        ).prefetch_related("active_user__user")

        if team:
            self.fields["team"].initial = team
        if len(owners) > 0:
            self.fields["owners"].initial = owners

        initial = None
        if self.instance.pk:
            initial = self.instance.pdf_set.values_list("id", flat=True)
        self.fields["invoices"] = forms.ModelMultipleChoiceField(
            queryset=Pdf.objects.filter(tournament=trn, tags__type=Template.INVOICE),
            widget=Select2MultipleWidget,
            initial=initial,
            required=False,
        )

    def clean_invoices(self):
        inv = self.cleaned_data.get("invoices")
        if len(inv) > 0:
            try:
                self.invoices = Pdf.objects.filter(
                    pk__in=inv, tournament=self.tournament
                )
            except Pdf.DoesNotExist:
                raise forms.ValidationError("Sorry, that Invoices are not valid.")
        else:
            self.invoices = []
        return inv

    def save(self, commit=True):
        before = []
        if self.instance.pk:
            before = self.instance.pdf_set.all()
        instance = super(AccountForm, self).save(commit=commit)
        if commit:
            for i in self.invoices:
                i.invoice_account = instance
                i.save()
            for b in before:
                if b not in self.invoices:
                    b.invoice_account = None
                    b.save()
        return instance


class PaymentForm(forms.ModelForm):

    class Meta:
        model = Payment
        fields = ("sender", "receiver", "amount", "reference", "due_at")

    def __init__(self, trn, *args, **kwargs):
        sender = None
        amount = None
        reference = ""
        if "sender" in kwargs:
            sender = kwargs["sender"]
            del kwargs["sender"]
        if "amount" in kwargs:
            amount = kwargs["amount"]
            del kwargs["amount"]
        if "reference" in kwargs:
            reference = kwargs["reference"]
            del kwargs["reference"]

        super().__init__(*args, **kwargs)

        self.fields["sender"].queryset = (
            self.fields["sender"].queryset.filter(owners__tournament=trn).distinct()
        )
        self.fields["receiver"].queryset = (
            self.fields["receiver"].queryset.filter(owners__tournament=trn).distinct()
        )

        if sender:
            self.fields["sender"].initial = sender
        if amount:
            self.fields["amount"].initial = amount
        if reference:
            self.fields["reference"].initial = reference

        opts = {"format": "YYYY-MM-DDTHH:mmZZ", "sideBySide": True}
        try:
            opts["timeZone"] = trn.timezone
        except:
            pass

        dueinit = self.fields["due_at"].initial

        self.fields["due_at"] = DateTimeFieldNonTZ(
            widget=DateTimePicker(format="%Y-%m-%dT%H:%M%z", options=opts),
            required=False,
            initial=dueinit,
        )


class SettlementForm(forms.ModelForm):

    class Meta:
        model = Payment
        fields = ("amount",)

        help_texts = {
            "amount": "New Amount after settlement",
        }

    mark_as_settled = forms.BooleanField(
        required=False, widget=forms.CheckboxInput, initial=True
    )
    abort_reason = forms.CharField(required=False, max_length=300)


class TeamFeeForm(forms.ModelForm):

    class Meta:
        model = Tournament
        fields = ("fee_team",)


class RoleFeeForm(forms.ModelForm):

    class Meta:
        model = ParticipationRole
        fields = ("fee",)

    def save(self, commit=True):
        role = super().save(commit=False)
        if role.fee == 0:
            role.fee = None
        role.save()


class PropertyFeeForm(forms.ModelForm):

    class Meta:
        model = PropertyFee
        fields = ("name", "fee", "if_true", "if_not_true")

        widgets = {
            "if_true": Select2MultipleWidget,
            "if_not_true": Select2MultipleWidget,
        }

    def __init__(self, trn, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["if_true"].queryset = AttendeeProperty.objects.filter(
            tournament=trn, type__in=[AttendeeProperty.BOOLEAN]
        )
        self.fields["if_not_true"].queryset = AttendeeProperty.objects.filter(
            tournament=trn, type__in=[AttendeeProperty.BOOLEAN]
        )
