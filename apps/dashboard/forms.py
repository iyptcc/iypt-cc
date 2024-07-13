from django import forms
from django.contrib.auth.hashers import check_password


class ModelDeleteListField(forms.ModelMultipleChoiceField):
    widget = forms.CheckboxSelectMultiple

    def label_from_instance(self, obj):
        return obj


class SimpleloginForm(forms.Form):

    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput,
    )

    error_messages = {
        "invalid_login": "Please enter a correct password for %(tournament)s.",
        "inactive": "This account is inactive.",
    }

    def __init__(self, tournament, *args, **kwargs):
        super(SimpleloginForm, self).__init__(*args, **kwargs)

        self._tournament = tournament

    def get_tournament(self):
        return self._tournament.name

    def clean(self):
        password = self.cleaned_data.get("password")

        if password:
            valid = check_password(password, self._tournament.results_password)

            if not valid:
                raise forms.ValidationError(
                    self.error_messages["invalid_login"],
                    code="invalid_login",
                    params={"tournament": self.get_tournament()},
                )

        return self.cleaned_data
