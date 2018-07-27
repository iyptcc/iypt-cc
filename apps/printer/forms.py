from codemirror2.widgets import CodeMirrorEditor
from django import forms
from django_select2.forms import Select2MultipleWidget

from .models import Pdf, PdfTag, Template, TemplateVersion


class TemplateForm(forms.Form):

    tname = forms.CharField(label="Template Name")
    files = forms.ModelMultipleChoiceField(queryset=Pdf.objects.none(), widget=Select2MultipleWidget, required=False)
    src = forms.CharField(widget=CodeMirrorEditor(options={'mode': 'stex','lineNumbers' : True}))
    name = forms.CharField(required=False)
    type = forms.ChoiceField(choices=[('', '----')] + list(Template.TYPE), required=False)

    def __init__(self, template, *args, **kwargs):
        super(TemplateForm, self).__init__(*args, **kwargs)

        src = template.templateversion_set.last().src
        if src == "":
            src = "empty"
        self.fields['src'].initial = src
        self.fields['type'].initial = template.type
        self.fields['files'].queryset = Pdf.objects.filter(tournament=template.tournament)
        self.fields['files'].initial = template.files.all()
        self.fields['tname'].initial = template.name
        self.tournament = template.tournament

    def clean_name(self):
        name = self.cleaned_data['name']

        if name!="":
            if Pdf.objects.filter(tournament=self.tournament, name=name).exists():
                raise forms.ValidationError("File with name %(name)s already exists", params={'name':name}, code="double-name")

        return name


class UploadForm(forms.Form):

    name = forms.CharField(max_length=250)
    file = forms.FileField()

    def __init__(self, tournament, *args, **kwargs):
        super(UploadForm, self).__init__(*args, **kwargs)

        self.fields["tags"] = forms.ModelMultipleChoiceField(PdfTag.objects.filter(tournament=tournament), required=False, widget=Select2MultipleWidget)

class TemplateNewForm(forms.Form):

    name = forms.CharField(max_length=250)
    type = forms.ChoiceField(choices=[('','----')]+list(Template.TYPE), required=False)

    def __init__(self, tournament, *args, **kwargs):
        super(TemplateNewForm, self).__init__(*args, **kwargs)
        self.tournament = tournament

        self.fields["parent"] = forms.ModelChoiceField(Template.objects.filter(tournament=tournament), required=False)

    def clean_name(self):
        name = self.cleaned_data['name']

        if Template.objects.filter(tournament=self.tournament, name=name).exists():
            raise forms.ValidationError("Template with name %(name)s already exists", params={'name':name}, code="double-name")

        return name
