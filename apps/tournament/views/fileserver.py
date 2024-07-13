from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_list_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.generic import CreateView, ListView, UpdateView

from apps.dashboard.delete import ConfirmedDeleteView
from apps.printer.models import FileServer
from apps.tournament.forms import BBBForm, FileServerForm


@method_decorator(login_required, name="dispatch")
class ListServer(ListView):

    template_name = "tournament/fileList.html"

    def get_queryset(self):
        return FileServer.objects.filter(
            tournament=self.request.user.profile.tournament
        )


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("printer.change_fileserver", raise_exception=False),
    name="dispatch",
)
@method_decorator(sensitive_variables("new_password"), name="dispatch")
@method_decorator(sensitive_post_parameters("new_password"), name="dispatch")
class UpdateServer(UpdateView):

    model = FileServer

    success_url = reverse_lazy("tournament:fileservers")

    form_class = FileServerForm

    def form_valid(self, form):
        clean = form.cleaned_data
        new_password = clean.get("new_password")
        if new_password:
            # encrypt plain password
            form.instance.password = new_password
        return super(UpdateServer, self).form_valid(form)

    def get_object(self, queryset=None):
        obj = FileServer.objects.get(
            id=self.kwargs["id"], tournament=self.request.user.profile.tournament
        )
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("printer.add_fileserver", raise_exception=False),
    name="dispatch",
)
class CreateServer(CreateView):

    model = FileServer
    fields = ["name", "hostname", "port", "username", "fingerprint", "password"]

    success_url = reverse_lazy("tournament:fileservers")

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        validation = super(CreateServer, self).form_valid(form)
        return validation


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("printer.delete_fileserver", raise_exception=False),
    name="dispatch",
)
class DeleteServer(ConfirmedDeleteView):

    redirection = "tournament:fileservers"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            FileServer, tournament=request.user.profile.tournament, id=kwargs["id"]
        )
        return obj
