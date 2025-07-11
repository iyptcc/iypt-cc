from django import forms
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth.decorators import login_required, permission_required
from django.core.files.base import ContentFile
from django.utils.decorators import method_decorator
from django.utils.text import capfirst
from django_select2.forms import Select2MultipleWidget
from formtools.preview import FormPreview
from pypdf import PdfWriter

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
        return ["inbox_attendees__active_user__user", "tags"]

    def form_members(self):

        merge_name = forms.CharField(max_length=100, required=False)
        merge_pages = forms.CharField(max_length=200, required=False)

        atts = self.request.user.profile.tournament.attendee_set.all().prefetch_related(
            "active_user__user"
        )

        attendees = forms.ModelMultipleChoiceField(
            queryset=atts,
            required=False,
            widget=Select2MultipleWidget(),
        )

        tags = forms.ModelMultipleChoiceField(
            queryset=self.request.user.profile.tournament.pdftag_set.all(),
            required=False,
            widget=Select2MultipleWidget(),
        )

        return {
            "merge_name": merge_name,
            "merge_pages": merge_pages,
            "attendees": attendees,
            "tags": tags,
        }

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

        if "_add_share" in request.POST:
            context["action"] = "_add_share"

            self.preview_template = "printer/pdf_change_preview.html"

            newatts = form.cleaned_data["attendees"]

            pdfs = []
            for pdf in form.cleaned_data["obj_list"]:

                pdf = {
                    "pure_name": pdf.pure_name(),
                    "name": pdf.name,
                    "file": pdf.file,
                    "share": pdf.inbox_attendees.all(),
                    "tag": pdf.tags.all(),
                }
                pdf["share_new"] = []
                for newatt in newatts:
                    if newatt.pk not in pdf["share"].values_list("pk", flat=True):
                        pdf["share_new"].append(newatt)
                pdfs.append(pdf)

            context["pdfs"] = pdfs

        if "_del_share" in request.POST:
            self.preview_template = "printer/pdf_change_preview.html"

            context["action"] = "_del_share"
            delatts = form.cleaned_data["attendees"]

            pdfs = []
            for pdf in form.cleaned_data["obj_list"]:

                pdf = {
                    "pure_name": pdf.pure_name(),
                    "name": pdf.name,
                    "file": pdf.file,
                    "share": pdf.inbox_attendees.all(),
                    "tag": pdf.tags.all(),
                }

                pdf["share_del"] = []
                pdf["share_del_na"] = []
                for delatt in delatts:
                    if delatt.pk in pdf["share"].values_list("pk", flat=True):
                        pdf["share"] = pdf["share"].exclude(pk=delatt.pk)
                        pdf["share_del"].append(delatt)
                    else:
                        pdf["share_del_na"].append(delatt)

                pdfs.append(pdf)

            context["pdfs"] = pdfs

        if "_all_share" in request.POST:
            self.preview_template = "printer/pdf_change_preview.html"

            context["action"] = "_all_share"

            pdfs = []
            for pdf in form.cleaned_data["obj_list"]:

                pdf = {
                    "pure_name": pdf.pure_name(),
                    "name": pdf.name,
                    "file": pdf.file,
                    "share": [],
                    "tag": pdf.tags.all(),
                    "share_del": pdf.inbox_attendees.all(),
                }

                pdfs.append(pdf)

            context["pdfs"] = pdfs

        if "_add_tag" in request.POST:
            context["action"] = "_add_tag"

            self.preview_template = "printer/pdf_change_preview.html"

            news = form.cleaned_data["tags"]

            pdfs = []
            for pdf in form.cleaned_data["obj_list"]:

                pdf = {
                    "pure_name": pdf.pure_name(),
                    "name": pdf.name,
                    "file": pdf.file,
                    "share": pdf.inbox_attendees.all(),
                    "tag": pdf.tags.all(),
                }
                pdf["tag_new"] = []
                for new in news:
                    if new.pk not in pdf["tag"].values_list("pk", flat=True):
                        pdf["tag_new"].append(new)
                pdfs.append(pdf)

            context["pdfs"] = pdfs

        if "_del_tag" in request.POST:
            self.preview_template = "printer/pdf_change_preview.html"

            context["action"] = "_del_tag"
            dels = form.cleaned_data["tags"]

            pdfs = []
            for pdf in form.cleaned_data["obj_list"]:

                pdf = {
                    "pure_name": pdf.pure_name(),
                    "name": pdf.name,
                    "file": pdf.file,
                    "share": pdf.inbox_attendees.all(),
                    "tag": pdf.tags.all(),
                }

                pdf["tag_del"] = []
                pdf["tag_del_na"] = []
                for delo in dels:
                    if delo.pk in pdf["tag"].values_list("pk", flat=True):
                        pdf["tag"] = pdf["tag"].exclude(pk=delo.pk)
                        pdf["tag_del"].append(delo)
                    else:
                        pdf["tag_del_na"].append(delo)

                pdfs.append(pdf)

            context["pdfs"] = pdfs

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

            merger = PdfWriter()

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

        elif request.POST["action"] == "_add_share":
            news = cleaned_data["attendees"]
            for pdf in cleaned_data["obj_list"]:
                pdf.inbox_attendees.add(*news)

        elif request.POST["action"] == "_del_share":
            news = cleaned_data[("attendees")]
            for pdf in cleaned_data["obj_list"]:
                pdf.inbox_attendees.remove(*news)

        elif request.POST["action"] == "_all_share":
            for pdf in cleaned_data["obj_list"]:
                if pdf.inbox_attendees.exists():
                    pdf.inbox_attendees.clear()

        elif request.POST["action"] == "_add_tag":
            news = cleaned_data["tags"]
            for pdf in cleaned_data["obj_list"]:
                pdf.tags.add(*news)

        elif request.POST["action"] == "_del_tag":
            news = cleaned_data[("tags")]
            for pdf in cleaned_data["obj_list"]:
                pdf.tags.remove(*news)
