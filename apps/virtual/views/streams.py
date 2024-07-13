from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_list_or_404, get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, UpdateView

from apps.dashboard.delete import ConfirmedDeleteView

from ..forms import StreamEditForm
from ..models import Stream


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("plan.change_fight_operator", raise_exception=False),
    name="dispatch",
)
class View(ListView):

    # template_name = "virtual/streamList.html"

    def get_queryset(self):
        return Stream.objects.filter(tournament=self.request.user.profile.tournament)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("plan.change_fight_operator", raise_exception=False),
    name="dispatch",
)
class Create(CreateView):

    model = Stream
    fields = ["name", "stream_name", "hls_format", "mpd_format"]

    success_url = reverse_lazy("virtual:streams")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return StreamEditForm(
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

    model = Stream
    fields = ["name", "stream_name", "hls_format", "mpd_format"]

    success_url = reverse_lazy("virtual:streams")

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return StreamEditForm(
            self.request.user.profile.tournament, **self.get_form_kwargs()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        urls = []
        for format in [self.object.hls_format, self.object.mpd_format]:
            for subdomain in self.object.streamedgeserver_set.all():
                timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
                urls.append(
                    format.format_map(
                        {
                            "subdomain": subdomain.url,
                            "streamname": self.object.stream_name,
                            "timestamp": timestamp,
                        }
                    )
                )
        context["urls"] = urls
        return context

    def get_object(self, queryset=None):
        obj = Stream.objects.get(
            id=self.kwargs["id"], tournament=self.request.user.profile.tournament
        )
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("plan.change_fight_operator", raise_exception=False),
    name="dispatch",
)
class Delete(ConfirmedDeleteView):

    redirection = "virtual:streams"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            Stream, tournament=request.user.profile.tournament, id=kwargs["id"]
        )
        return obj
