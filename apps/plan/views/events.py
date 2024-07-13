from django.contrib.auth.decorators import login_required, permission_required
from django.core import signing
from django.db import IntegrityError
from django.shortcuts import get_list_or_404, get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, UpdateView

from apps.dashboard.delete import ConfirmedDeleteView

from ...tournament.models import Tournament
from ..forms import EventEditForm
from ..models import Event


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("plan.add_fight", raise_exception=False), name="dispatch"
)
class View(ListView):

    # template_name = "plan/eventsList.html"

    def get_queryset(self):
        return Event.objects.filter(tournament=self.request.user.profile.tournament)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("plan.add_fight", raise_exception=False), name="dispatch"
)
class Create(CreateView):

    model = Event
    fields = [
        "name",
        "type",
    ]

    success_url = reverse_lazy("plan:events")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return EventEditForm(
            self.request.user.profile.tournament, **self.get_form_kwargs()
        )

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        return super(Create, self).form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("plan.add_fight", raise_exception=False), name="dispatch"
)
class Change(UpdateView):

    model = Event
    fields = ["order", "type"]

    success_url = reverse_lazy("plan:events")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return EventEditForm(
            self.request.user.profile.tournament, **self.get_form_kwargs()
        )

    def get_object(self, queryset=None):
        obj = Event.objects.get(
            id=self.kwargs["id"], tournament=self.request.user.profile.tournament
        )
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("plan.add_fight", raise_exception=False), name="dispatch"
)
class Delete(ConfirmedDeleteView):

    redirection = "plan:events"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            Event, tournament=request.user.profile.tournament, id=kwargs["id"]
        )
        return obj
