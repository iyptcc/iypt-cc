from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import IntegrityError
from django.shortcuts import get_list_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, UpdateView

from apps.account.models import ParticipationRole
from apps.dashboard.delete import ConfirmedDeleteView

from ..forms import HallRoleEditForm
from ..models import Hall, HallRole


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("virtual.view_hallrole", raise_exception=False), name="dispatch"
)
class View(ListView):

    # template_name = "tournament/applicationQList.html"

    def get_queryset(self):
        return HallRole.objects.filter(
            hall__tournament=self.request.user.profile.tournament,
            hall_id=self.kwargs["hall_id"],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["hall"] = Hall.objects.get(
            tournament=self.request.user.profile.tournament, id=self.kwargs["hall_id"]
        )
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("virtual.add_hallrole", raise_exception=False), name="dispatch"
)
class Create(CreateView):

    model = HallRole

    def get_success_url(self):
        return reverse_lazy(
            "virtual:hallroles", kwargs={"hall_id": self.kwargs["hall_id"]}
        )

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return HallRoleEditForm(
            self.request.user.profile.tournament, **self.get_form_kwargs()
        )

    def form_valid(self, form):

        form.instance.hall = Hall.objects.get(
            tournament=self.request.user.profile.tournament, id=self.kwargs["hall_id"]
        )
        try:
            validation = super(Create, self).form_valid(form)
            # clear all caches
            return validation
        except IntegrityError:
            messages.add_message(
                self.request,
                messages.ERROR,
                "Hall %s already has role %s"
                % (form.instance.hall.name, form.instance.role),
            )
            return redirect("virtual:hallroles", hall_id=self.kwargs["hall_id"])


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("virtual.change_hallrole", raise_exception=False),
    name="dispatch",
)
class Change(UpdateView):

    model = HallRole

    def get_success_url(self):
        return reverse_lazy(
            "virtual:hallroles", kwargs={"hall_id": self.kwargs["hall_id"]}
        )

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return HallRoleEditForm(
            self.request.user.profile.tournament, **self.get_form_kwargs()
        )

    def get_object(self, queryset=None):
        obj = HallRole.objects.get(
            id=self.kwargs["id"],
            hall__id=self.kwargs["hall_id"],
            hall__tournament=self.request.user.profile.tournament,
        )
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("virtual.delete_hallrole", raise_exception=False),
    name="dispatch",
)
class Delete(ConfirmedDeleteView):

    def get_redirection(self, request, *args, **kwargs):
        return redirect("virtual:hallroles", hall_id=kwargs["hall_id"])

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            HallRole,
            hall__tournament=request.user.profile.tournament,
            hall__id=kwargs["hall_id"],
            id=kwargs["id"],
        )
        return obj
