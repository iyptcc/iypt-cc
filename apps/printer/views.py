import paramiko
from celery.result import AsyncResult
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.forms import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_list_or_404, get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView
from django_downloadview import ObjectDownloadView
from paramiko.ssh_exception import SSHException

from apps.dashboard.delete import ConfirmedDeleteView

from .default_context import default_template_context
from .forms import ImportForm, TemplateForm, TemplateNewForm, UploadForm
from .models import FileServer, Pdf, PdfTag, Template, TemplateVersion
from .tasks import render_to_pdf
from .utils import render_template

# Create your views here.


@method_decorator(login_required, name="dispatch")
class ListPdfs(ListView):

    template_name = "printer/list.html"

    def get_queryset(self):

        return Pdf.objects.filter(tournament=self.request.user.profile.tournament)


@method_decorator(login_required, name="dispatch")
class ListTemplates(ListView):

    template_name = "printer/templates.html"

    def get_queryset(self):

        return Template.objects.filter(tournament=self.request.user.profile.tournament)


@method_decorator(login_required, name="dispatch")
class FileView(ObjectDownloadView):

    attachment = False

    mimetype = "application/pdf"

    def get_object(self, queryset=None):
        try:
            obj = self.request.user.profile.tournament.pdf_set.get(
                file=self.kwargs["name"]
            ).file
            return obj
        except:
            raise Pdf.DoesNotExist("File does not exist")


@method_decorator(login_required, name="dispatch")
class AddTemplate(View):

    def get(self, request):
        form = TemplateNewForm(request.user.profile.tournament)

        return render(request, "printer/template_new.html", context={"form": form})

    def post(self, request):
        form = TemplateNewForm(request.user.profile.tournament, request.POST)
        if form.is_valid():

            tpl = Template.objects.create(
                tournament=request.user.profile.tournament,
                name=form.cleaned_data["name"],
                type=form.cleaned_data["type"],
                parent=form.cleaned_data["parent"],
            )
            TemplateVersion.objects.create(
                template=tpl, author=request.user.profile, src=""
            )

            return redirect("printer:templates")

        return render(request, "printer/template_new.html", context={"form": form})


@method_decorator(login_required, name="dispatch")
class EditTemplate(View):

    def get(self, request, id):

        template = get_object_or_404(
            Template, id=id, tournament=request.user.profile.tournament
        )

        form = TemplateForm(template)

        if template.type in default_template_context:
            context = default_template_context[template.type]
        else:
            context = {}

        return render(
            request,
            "printer/template_edit.html",
            context={"form": form, "context": context},
        )

    def post(self, request, id):

        trn = request.user.profile.tournament
        template = get_object_or_404(Template, id=id, tournament=trn)

        form = TemplateForm(template, request.POST)

        if form.is_valid():

            if "type" in form.changed_data:
                template.type = form.cleaned_data["type"]
                template.save()

            if "tname" in form.changed_data:
                template.name = form.cleaned_data["tname"]
                template.save()

            if "files" in form.changed_data:
                template.files.set(form.cleaned_data["files"])
                template.save()

            if "parent" in form.changed_data:
                template.parent = form.cleaned_data["parent"]
                template.save()

            if "src" in form.changed_data:
                TemplateVersion.objects.create(
                    template=template,
                    author=request.user.profile,
                    src=form.cleaned_data["src"],
                )

            if "_save" in request.POST:
                return redirect("printer:templates")

            if "_save_continue" in request.POST:
                return render(
                    request, "printer/template_edit.html", context={"form": form}
                )

            if "_render" in request.POST and form.cleaned_data["name"] != "":

                if form.cleaned_data["type"] in default_template_context:
                    context = default_template_context[template.type]
                else:
                    context = {}

                pdf = Pdf.objects.create(name=form.cleaned_data["name"], tournament=trn)

                res = render_to_pdf.delay(template.id, pdf.id, context=context)

                pdf.task_id = res.id
                pdf.save()
                pdf.tags.add(
                    PdfTag.objects.filter(tournament=trn, name="Debug").first()
                )

                return redirect("printer:list")

            if "_source" in request.POST:

                if form.cleaned_data["type"] in default_template_context:
                    context = default_template_context[template.type]
                else:
                    context = {}

                (src, err) = render_template(template.id, context)

                return render(request, "printer/source.html", context={"src": src})

        return render(request, "printer/template_edit.html", context={"form": form})


@method_decorator(login_required, name="dispatch")
class ListTemplateVersions(ListView):

    template_name = "printer/template_versions.html"

    def get_queryset(self):

        template = get_object_or_404(
            Template,
            tournament=self.request.user.profile.tournament,
            id=self.kwargs["id"],
        )

        return template.templateversion_set.all()


def view_error(request, id):

    trn = request.user.profile.tournament
    res = AsyncResult(id)
    get_object_or_404(Pdf, task_id=res.id, tournament=trn, status=Pdf.FAILURE)

    # if res.state == 'FAILURE':

    return render(request, "printer/error.html", context=res.info)


def view_render_error(request, id):

    trn = request.user.profile.tournament
    res = AsyncResult(id)
    get_object_or_404(Pdf, task_id=res.id, tournament=trn, status=Pdf.ERROR)

    return render(request, "printer/render_error.html", context=res.result)


class ORMHostKeyPolicy(paramiko.MissingHostKeyPolicy):

    def __init__(self, server):
        self.server = server

    def missing_host_key(self, client, hostname, key):
        if self.server.fingerprint != key.get_base64():
            raise SSHException(
                f"got fingerprint {key.get_base64()} which is not {self.server.fingerprint}"
            )


@method_decorator(login_required, name="dispatch")
class PdfImport(View):

    def get(self, request, id):
        trn = request.user.profile.tournament
        server = get_object_or_404(FileServer, tournament=trn, id=id)

        ssh = paramiko.SSHClient()
        policy = ORMHostKeyPolicy(server)
        ssh.set_missing_host_key_policy(policy)
        try:
            ssh.connect(
                hostname=server.hostname,
                port=server.port,
                username=server.username,
                password=server.password,
            )
            sftp = ssh.open_sftp()

            form = ImportForm(sftp, trn)
        except SSHException as e:
            return render(request, "printer/import.html", {"error": e})
        return render(request, "printer/import.html", {"form": form})

    def post(self, request, id):
        trn = request.user.profile.tournament
        server = get_object_or_404(FileServer, tournament=trn, id=id)
        ssh = paramiko.SSHClient()
        policy = ORMHostKeyPolicy(server)
        ssh.set_missing_host_key_policy(policy)
        ssh.connect(
            hostname=server.hostname,
            port=server.port,
            username=server.username,
            password=server.password,
        )
        sftp = ssh.open_sftp()

        form = ImportForm(sftp, trn, request.POST)

        if form.is_valid():
            print("valid", form.cleaned_data)
            for file in form.cleaned_data["files"]:
                rf = sftp.open(file)
                data = rf.read()
                cf = ContentFile(data, file)

                pdf = Pdf.objects.create(
                    file=cf,
                    name=file,
                    status=Pdf.UPLOAD,
                    tournament=request.user.profile.tournament,
                )

            return redirect("printer:list")

        return render(request, "printer/import.html", {"form": form})


@method_decorator(login_required, name="dispatch")
class PdfUpload(View):

    def get(self, request):

        form = UploadForm(request.user.profile.tournament)

        return render(request, "printer/upload.html", {"form": form})

    def post(self, request):

        form = UploadForm(request.user.profile.tournament, request.POST, request.FILES)

        if form.is_valid():
            try:
                pdf = Pdf.objects.create(
                    file=request.FILES["file"],
                    name=form.cleaned_data["name"],
                    status=Pdf.UPLOAD,
                    tournament=request.user.profile.tournament,
                )

                pdf.tags.add(*form.cleaned_data["tags"])

                return redirect("printer:list")
            except Exception as e:
                form.add_error("name", ValidationError("Name already exists"))
                return render(request, "printer/upload.html", {"form": form})

        return render(request, "printer/upload.html", {"form": form})


@method_decorator(login_required, name="dispatch")
class TagView(ListView):

    template_name = "printer/tagList.html"

    def get_queryset(self):
        return PdfTag.objects.filter(tournament=self.request.user.profile.tournament)


@method_decorator(login_required, name="dispatch")
# @method_decorator(permission_required('tournament.change_origin', raise_exception=False), name='dispatch')
class TagChange(UpdateView):

    model = PdfTag
    fields = ["name", "color"]

    success_url = reverse_lazy("printer:tags")

    def get_object(self, queryset=None):
        obj = PdfTag.objects.get(
            id=self.kwargs["id"], tournament=self.request.user.profile.tournament
        )
        return obj

    def post(self, request, *args, **kwargs):
        # clear all caches
        # caches['results'].clear()

        return super().post(request, *args, **kwargs)


@method_decorator(login_required, name="dispatch")
# @method_decorator(permission_required('tournament.change_origin', raise_exception=False), name='dispatch')
class TagCreate(CreateView):

    model = PdfTag
    fields = ["name", "color", "type"]

    success_url = reverse_lazy("printer:tags")

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        try:
            validation = super(TagCreate, self).form_valid(form)
            # clear all caches
            # caches['results'].clear()
            return validation
        except IntegrityError:
            messages.add_message(
                self.request,
                messages.ERROR,
                "Tag type %s already exists" % form.instance.type,
            )
            return redirect("printer:tags")


@method_decorator(login_required, name="dispatch")
# @method_decorator(permission_required('tournament.delete_origin',raise_exception=False),name='dispatch')
class TagDelete(ConfirmedDeleteView):

    redirection = "printer:tags"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            PdfTag, tournament=request.user.profile.tournament, id=kwargs["id"]
        )
        return obj
