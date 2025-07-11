from django import forms


class GenerateForm(forms.Form):
    teams = forms.IntegerField(min_value=3)
    rounds = forms.IntegerField(min_value=1)
    simulation = forms.IntegerField(min_value=1, initial=5000)


class ImportForm(forms.Form):
    input = forms.CharField(widget=forms.Textarea)
