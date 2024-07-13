from django.contrib.auth.decorators import login_required, permission_required
from django.core import signing
from django.db import IntegrityError
from django.shortcuts import get_list_or_404, get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, UpdateView

from apps.dashboard.delete import ConfirmedDeleteView

from ...tournament.models import Tournament
from ..forms import HallEditForm
from ..models import Hall


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("plan.change_fight_operator", raise_exception=False),
    name="dispatch",
)
class View(ListView):

    template_name = "virtual/hallList.html"

    def get_queryset(self):
        return Hall.objects.filter(tournament=self.request.user.profile.tournament)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("plan.change_fight_operator", raise_exception=False),
    name="dispatch",
)
class Create(CreateView):

    model = Hall
    fields = ["name"]

    success_url = reverse_lazy("virtual:halls")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return HallEditForm(
            self.request.user.profile.tournament, **self.get_form_kwargs()
        )

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        return super(Create, self).form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("plan.change_fight_operator", raise_exception=False),
    name="dispatch",
)
class Change(UpdateView):

    model = Hall
    fields = ["name"]

    success_url = reverse_lazy("virtual:halls")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return HallEditForm(
            self.request.user.profile.tournament, **self.get_form_kwargs()
        )

    def get_object(self, queryset=None):
        obj = Hall.objects.get(
            id=self.kwargs["id"], tournament=self.request.user.profile.tournament
        )
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("plan.change_fight_operator", raise_exception=False),
    name="dispatch",
)
class Delete(ConfirmedDeleteView):

    redirection = "virtual:halls"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            Hall, tournament=request.user.profile.tournament, id=kwargs["id"]
        )
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("virtual.change_hall", raise_exception=False), name="dispatch"
)
class Move(View):
    def post(self, request, id, direction):
        obj = get_object_or_404(
            Hall, id=self.kwargs["id"], tournament=self.request.user.profile.tournament
        )
        if direction == "up":
            obj.up()
        if direction == "down":
            obj.down()

        return redirect("virtual:halls")


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("virtual.view_hall", raise_exception=False), name="dispatch"
)
class Links(View):
    def get(self, request, id):
        hall = get_object_or_404(
            Hall, id=id, tournament=self.request.user.profile.tournament
        )

        signer = signing.Signer(salt="invite-links")
        # set password according to role
        links = []
        for role in [r[0] for r in Tournament.BBB_ROLES]:
            sig = signer.sign(
                "%s-invitation-hall-%d-role-%s" % (hall.tournament.slug, hall.id, role)
            )
            li = {
                "slug": hall.tournament.slug,
                "hall": id,
                "role": role,
                "sig": sig.split(":")[-1],
            }
            links.append(li)

        return render(
            request,
            "virtual/joinlinks.html",
            context={"links": links, "hall": hall.name},
        )
