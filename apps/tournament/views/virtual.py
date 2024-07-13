from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_list_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.generic import CreateView, ListView, UpdateView

from apps.dashboard.delete import ConfirmedDeleteView
from apps.tournament.forms import BBBForm
from apps.virtual.models import BBBInstance


@method_decorator(login_required, name="dispatch")
class ListServer(ListView):

    template_name = "tournament/bbbList.html"

    def get_queryset(self):
        return BBBInstance.objects.filter(
            tournament=self.request.user.profile.tournament
        )


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("virtual.change_bbbinstance", raise_exception=False),
    name="dispatch",
)
@method_decorator(sensitive_variables("new_secret"), name="dispatch")
@method_decorator(sensitive_post_parameters("new_secret"), name="dispatch")
class UpdateServer(UpdateView):

    model = BBBInstance

    success_url = reverse_lazy("tournament:bbbservers")

    form_class = BBBForm

    def form_valid(self, form):
        clean = form.cleaned_data
        new_secret = clean.get("new_secret")
        if new_secret:
            # encrypt plain password
            form.instance.secret = new_secret
        return super(UpdateServer, self).form_valid(form)

    def get_object(self, queryset=None):
        obj = BBBInstance.objects.get(
            id=self.kwargs["id"], tournament=self.request.user.profile.tournament
        )
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("virtual.add_bbbinstance", raise_exception=False),
    name="dispatch",
)
class CreateServer(CreateView):

    model = BBBInstance
    fields = ["name", "api_url", "secret"]

    success_url = reverse_lazy("tournament:bbbservers")

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        validation = super(CreateServer, self).form_valid(form)
        return validation


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("virtual.delete_bbbinstance", raise_exception=False),
    name="dispatch",
)
class DeleteServer(ConfirmedDeleteView):

    redirection = "tournament:bbbservers"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            BBBInstance, tournament=request.user.profile.tournament, id=kwargs["id"]
        )
        return obj
