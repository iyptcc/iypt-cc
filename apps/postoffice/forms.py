from codemirror2.widgets import CodeMirrorEditor
from django import forms

from .models import Template


class TemplateForm(forms.Form):

    subject = forms.CharField(max_length=1000)
    tname = forms.CharField()
    src = forms.CharField(widget=CodeMirrorEditor(options={'mode': 'jinja2','lineNumbers' : True}))
    type = forms.ChoiceField(choices=[('', '----')] + list(Template.TYPE), required=False)

    def __init__(self, template, *args, **kwargs):
        super(TemplateForm, self).__init__(*args, **kwargs)

        self.fields['subject'].initial = template.templateversion_set.last().subject
        self.fields['src'].initial = template.templateversion_set.last().src
        self.fields['type'].initial = template.type
        self.fields['tname'].initial = template.name
        self.tournament = template.tournament

    def clean_name(self):
        name = self.cleaned_data['name']
        return name


class TemplateNewForm(forms.Form):

    name = forms.CharField(max_length=250)
    type = forms.ChoiceField(choices=[('','----')]+list(Template.TYPE), required=False)

    def __init__(self, tournament, *args, **kwargs):
        super(TemplateNewForm, self).__init__(*args, **kwargs)
        self.tournament = tournament

    def clean_name(self):
        name = self.cleaned_data['name']

        if Template.objects.filter(tournament=self.tournament, name=name).exists():
            raise forms.ValidationError("Template with name %(name)s already exists", params={'name':name}, code="double-name")

        return name
