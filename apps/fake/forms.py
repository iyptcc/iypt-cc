from django import forms


class PersonForm(forms.Form):
    teams = forms.IntegerField(min_value=1)
    team_members = forms.IntegerField(min_value=2)
    indep_jur = forms.IntegerField(min_value=0)
    local_jur = forms.IntegerField(min_value=0)
    f_ass = forms.IntegerField(min_value=0)


class ImportForm(forms.Form):
    input = forms.CharField(widget=forms.Textarea)
