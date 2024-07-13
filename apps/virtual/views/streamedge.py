from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import IntegrityError
from django.shortcuts import get_list_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, UpdateView

from apps.dashboard.delete import ConfirmedDeleteView

from ..models import Stream, StreamEdgeServer


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("virtual.view_streamedgeserver", raise_exception=False),
    name="dispatch",
)
class View(ListView):

    # template_name = "tournament/applicationQList.html"

    def get_queryset(self):
        return StreamEdgeServer.objects.filter(
            stream__tournament=self.request.user.profile.tournament,
            stream_id=self.kwargs["stream_id"],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["stream"] = Stream.objects.get(
            tournament=self.request.user.profile.tournament, id=self.kwargs["stream_id"]
        )
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("virtual.add_streamedgeserver", raise_exception=False),
    name="dispatch",
)
class Create(CreateView):

    model = StreamEdgeServer
    fields = ["url"]

    def get_success_url(self):
        return reverse_lazy(
            "virtual:streamedges", kwargs={"stream_id": self.kwargs["stream_id"]}
        )

    def form_valid(self, form):

        form.instance.stream = Stream.objects.get(
            tournament=self.request.user.profile.tournament, id=self.kwargs["stream_id"]
        )
        try:
            validation = super(Create, self).form_valid(form)
            # clear all caches
            return validation
        except IntegrityError:
            messages.add_message(
                self.request,
                messages.ERROR,
                "Stream %s already has edge %s"
                % (form.instance.stream.name, form.instance.streamedgeserver),
            )
            return redirect("virtual:hallroles", hall_id=self.kwargs["hall_id"])


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("virtual.change_streamedgeserver", raise_exception=False),
    name="dispatch",
)
class Change(UpdateView):

    model = StreamEdgeServer
    fields = ["url"]

    def get_success_url(self):
        return reverse_lazy(
            "virtual:streamedges", kwargs={"stream_id": self.kwargs["stream_id"]}
        )

    def get_object(self, queryset=None):
        obj = StreamEdgeServer.objects.get(
            id=self.kwargs["id"],
            stream_id=self.kwargs["stream_id"],
            stream__tournament=self.request.user.profile.tournament,
        )
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("virtual.delete_streamedgeserver", raise_exception=False),
    name="dispatch",
)
class Delete(ConfirmedDeleteView):

    def get_redirection(self, request, *args, **kwargs):
        return redirect("virtual:streamedges", stream_id=kwargs["stream_id"])

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            StreamEdgeServer,
            stream__tournament=request.user.profile.tournament,
            stream_id=kwargs["stream_id"],
            id=kwargs["id"],
        )
        return obj
