from dataclasses import dataclass
from datetime import datetime

import paramiko
from codemirror2.widgets import CodeMirrorEditor
from django import forms
from django_select2.forms import Select2MultipleWidget
from paramiko.ssh_exception import SSHException

from ..tournament.models import Origin, Tournament
from .models import Pdf, PdfTag, Template


class TemplateForm(forms.Form):

    tname = forms.CharField(label="Template Name")
    files = forms.ModelMultipleChoiceField(
        queryset=Pdf.objects.none(), widget=Select2MultipleWidget, required=False
    )
    src = forms.CharField(
        widget=CodeMirrorEditor(
            options={"mode": "stex", "lineNumbers": True, "viewportMargin": 100}
        )
    )
    name = forms.CharField(required=False)
    type = forms.ChoiceField(
        choices=[("", "----")] + list(Template.TYPE), required=False
    )
    parent = forms.ModelChoiceField(queryset=Template.objects.none(), required=False)

    def __init__(self, template, *args, **kwargs):
        super(TemplateForm, self).__init__(*args, **kwargs)

        src = template.templateversion_set.last().src
        if src == "":
            src = "empty"
        self.fields["src"].initial = src
        self.fields["type"].initial = template.type
        self.fields["files"].queryset = Pdf.objects.filter(
            tournament=template.tournament
        )
        self.fields["files"].initial = template.files.all()
        self.fields["tname"].initial = template.name
        self.fields["parent"].queryset = Template.objects.filter(
            tournament=template.tournament
        )
        self.fields["parent"].initial = template.parent
        self.tournament = template.tournament

    def clean_name(self):
        name = self.cleaned_data["name"]

        if name != "":
            if Pdf.objects.filter(tournament=self.tournament, name=name).exists():
                raise forms.ValidationError(
                    "File with name %(name)s already exists",
                    params={"name": name},
                    code="double-name",
                )

        return name


class UploadForm(forms.Form):

    name = forms.CharField(max_length=250)
    file = forms.FileField()

    def __init__(self, tournament, *args, **kwargs):
        super(UploadForm, self).__init__(*args, **kwargs)

        self.fields["tags"] = forms.ModelMultipleChoiceField(
            PdfTag.objects.filter(tournament=tournament),
            required=False,
            widget=Select2MultipleWidget,
        )


@dataclass
class RemoteFile:
    name: str
    size: str
    mtime: datetime
    imported: bool
    origin: Origin | None = None


class ImportForm(forms.Form):

    def __init__(self, sftp, trn: Tournament, *args, **kwargs):
        super(ImportForm, self).__init__(*args, **kwargs)

        def sizeof_fmt(num, suffix="B"):
            for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
                if abs(num) < 1024.0:
                    return f"{num:3.1f}{unit}{suffix}"
                num /= 1024.0
            return f"{num:.1f}Yi{suffix}"

        imported = trn.pdf_set.values_list("name", flat=True)
        files = []
        for file in sftp.listdir_attr():
            if file.filename.lower().endswith(".pdf"):
                files.append(
                    (
                        file.filename,
                        RemoteFile(
                            name=file.filename,
                            size=sizeof_fmt(file.st_size),
                            mtime=datetime.fromtimestamp(file.st_mtime),
                            imported=file.filename in imported,
                        ),
                    )
                )
        files = sorted(files, key=lambda x: x[1].mtime, reverse=True)
        self.fields["files"] = forms.MultipleChoiceField(choices=files, required=False)


class TemplateNewForm(forms.Form):

    name = forms.CharField(max_length=250)
    type = forms.ChoiceField(
        choices=[("", "----")] + list(Template.TYPE), required=False
    )

    def __init__(self, tournament, *args, **kwargs):
        super(TemplateNewForm, self).__init__(*args, **kwargs)
        self.tournament = tournament

        self.fields["parent"] = forms.ModelChoiceField(
            Template.objects.filter(tournament=tournament), required=False
        )

    def clean_name(self):
        name = self.cleaned_data["name"]

        if Template.objects.filter(tournament=self.tournament, name=name).exists():
            raise forms.ValidationError(
                "Template with name %(name)s already exists",
                params={"name": name},
                code="double-name",
            )

        return name
