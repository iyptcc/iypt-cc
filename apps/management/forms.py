from django import forms
from django_select2.forms import Select2MultipleWidget, Select2Widget

from apps.registration.models import PropertyChoice, UserProperty
from apps.tournament.models import Tournament


class TournamentEditForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = ['name', 'slug', 'groups']

        widgets = {
            'groups': Select2MultipleWidget()
        }

class SetPasswordForm(forms.Form):

    password = forms.CharField(label="Password",
        strip=False,
        widget=forms.PasswordInput,
        required=False,
        help_text="Leave empty for unusable password."
    )

class UDEditForm(forms.ModelForm):

    class Meta:
        model = UserProperty
        fields = ['name', 'type']

        widgets = {
            'type': Select2Widget(),
        }

class PropertyChoiceForm(forms.ModelForm):
    class Meta:
        model = PropertyChoice
        fields = ("name",)

PropertyChoiceFormSet = forms.inlineformset_factory(UserProperty,PropertyChoice, PropertyChoiceForm, extra=2)
