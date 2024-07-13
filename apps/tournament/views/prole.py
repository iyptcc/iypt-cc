from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import IntegrityError
from django.shortcuts import get_list_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, UpdateView

from apps.account.models import ParticipationRole
from apps.dashboard.delete import ConfirmedDeleteView

from ..forms import RoleEditForm


@method_decorator(login_required, name="dispatch")
class RolesView(ListView):

    template_name = "tournament/rolesList.html"

    def get_queryset(self):
        return ParticipationRole.objects.filter(
            tournament=self.request.user.profile.tournament
        )


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("account.add_participationrole", raise_exception=False),
    name="dispatch",
)
class RoleCreate(CreateView):

    model = ParticipationRole
    fields = ["name", "type", "groups"]

    success_url = reverse_lazy("tournament:proles")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return RoleEditForm(
            self.request.user.profile.tournament, **self.get_form_kwargs()
        )

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        try:
            return super(RoleCreate, self).form_valid(form)
        except IntegrityError:
            messages.add_message(
                self.request,
                messages.ERROR,
                "Role of type %s already exists" % form.instance.get_type_display(),
            )
            return redirect("tournament:proles")


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("account.change_participationrole", raise_exception=False),
    name="dispatch",
)
class RoleChange(UpdateView):

    model = ParticipationRole
    fields = ["name", "type", "groups"]

    success_url = reverse_lazy("tournament:proles")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return RoleEditForm(
            self.request.user.profile.tournament, **self.get_form_kwargs()
        )

    def get_object(self, queryset=None):
        obj = ParticipationRole.objects.get(
            id=self.kwargs["id"], tournament=self.request.user.profile.tournament
        )
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("account.delete_participationrole", raise_exception=False),
    name="dispatch",
)
class RoleDelete(ConfirmedDeleteView):

    redirection = "tournament:proles"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            ParticipationRole,
            tournament=request.user.profile.tournament,
            id=kwargs["id"],
        )
        return obj
