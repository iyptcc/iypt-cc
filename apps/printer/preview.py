from django import forms
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth.decorators import login_required, permission_required
from django.core.files.base import ContentFile
from django.utils.decorators import method_decorator
from django.utils.text import capfirst
from formtools.preview import FormPreview
from pypdf import PdfMerger

from apps.dashboard.forms import ModelDeleteListField
from apps.dashboard.preview import ListPreview

from .models import Pdf


@method_decorator(login_required, name="__call__")
class PdfListPreview(ListPreview):

    form_template = "printer/list.html"
    success_url = "printer:list"

    def get_filters(self, request):
        trn = request.user.profile.tournament

        filters = [
            {
                "name": "Status",
                "elements": [self.DirectSelector(x[0], x[1]) for x in Pdf.STATUS],
                "filter": "status__in",
            },
            {"name": "Tags", "filter": "tags__in", "elements": trn.pdftag_set.all()},
        ]

        return filters

    def get_prefetch(self):
        return []

    def form_members(self):

        merge_name = forms.CharField(max_length=100, required=False)
        merge_pages = forms.CharField(max_length=200, required=False)

        return {"merge_name": merge_name, "merge_pages": merge_pages}

    def require_objs(self):
        return False

    def get_queryset(self):
        trn = self.request.user.profile.tournament
        return Pdf.objects.filter(tournament=trn)

    def preview_actions(self, request, form, context):

        if "_merge" in request.POST:

            context["action"] = "_merge"

            self.preview_template = "printer/pdf_merge_preview.html"

            pdfs = []

            for pdf in form.cleaned_data["obj_list"]:

                pdfs.append(
                    {"pure_name": pdf.pure_name(), "name": pdf.name, "file": pdf.file}
                )

            context["pdfs"] = pdfs

            context["pages"] = self._get_pagelist(form.cleaned_data["merge_pages"])

    def get_context(self, request, form):
        context = super().get_context(request, form)
        context["fileservers"] = request.user.profile.tournament.fileserver_set.all()

        return context

    def delete_perm(self, request):
        return request.user.has_perm("printer.delete_pdf")

    def _get_pagelist(self, s):
        pages = s.strip()
        if pages == "":
            return None
        runs = pages.split(",")
        inc = []
        for r in runs:
            parts = r.split(":")
            if len(parts) == 1:
                inc.append(int(parts[0]))
            else:
                s = slice(*map(int, parts))
                inc += list(range(10000))[s]

        if inc == []:
            inc = None
        return inc

    def done_actions(self, request, cleaned_data):
        if request.POST["action"] == "_merge":
            trn = request.user.profile.tournament

            merger = PdfMerger()

            inc = self._get_pagelist(cleaned_data["merge_pages"])
            print(inc)
            for pdf in cleaned_data["obj_list"]:
                merger.append(open(pdf.file.path, "rb"), pages=inc)

            cf = ContentFile(b"", cleaned_data["merge_name"])
            merger.write(cf)

            Pdf.objects.create(
                file=cf,
                name=cleaned_data["merge_name"],
                status=Pdf.MERGE,
                tournament=trn,
            )
