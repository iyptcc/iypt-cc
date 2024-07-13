from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import IntegrityError
from django.shortcuts import get_list_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, UpdateView

from apps.dashboard.delete import ConfirmedDeleteView
from apps.feedback.models import ChairFeedbackCriterion, FeedbackGrade


@method_decorator(login_required, name="dispatch")
class FeedbackGradeView(ListView):

    template_name = "tournament/feedbackgrades.html"

    def get_queryset(self):
        return FeedbackGrade.objects.filter(
            tournament=self.request.user.profile.tournament
        ).order_by("value")


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("feedback.change_feedbackgrade", raise_exception=False),
    name="dispatch",
)
class FeedbackGradeChange(UpdateView):

    model = FeedbackGrade
    fields = ["name", "value"]

    success_url = reverse_lazy("tournament:feedbackgrades")

    def get_object(self, queryset=None):
        obj = FeedbackGrade.objects.get(
            id=self.kwargs["id"], tournament=self.request.user.profile.tournament
        )
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("feedback.add_feedbackgrade", raise_exception=False),
    name="dispatch",
)
class FeedbackGradeCreate(CreateView):

    model = FeedbackGrade
    fields = ["name", "value"]

    success_url = reverse_lazy("tournament:feedbackgrades")

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        try:
            validation = super(FeedbackGradeCreate, self).form_valid(form)
            return validation
        except IntegrityError:
            messages.add_message(
                self.request,
                messages.ERROR,
                "Grade with value %f already exists" % form.instance.value,
            )
            return redirect("tournament:feedbackgrades")


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("feedback.delete_feedbackgrade", raise_exception=False),
    name="dispatch",
)
class FeedbackGradeDelete(ConfirmedDeleteView):

    redirection = "tournament:feedbackgrades"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            FeedbackGrade, tournament=request.user.profile.tournament, id=kwargs["id"]
        )
        return obj


@method_decorator(login_required, name="dispatch")
class ChairFeedbackCriterionView(ListView):

    template_name = "tournament/chairfeedbackcriteria.html"

    def get_queryset(self):
        return ChairFeedbackCriterion.objects.filter(
            tournament=self.request.user.profile.tournament
        )


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(
        "feedback.change_chairfeedbackcriterion", raise_exception=False
    ),
    name="dispatch",
)
class ChairFeedbackCriterionChange(UpdateView):

    model = ChairFeedbackCriterion
    fields = ["name"]

    success_url = reverse_lazy("tournament:chairfeedbackcriteria")

    def get_object(self, queryset=None):
        obj = ChairFeedbackCriterion.objects.get(
            id=self.kwargs["id"], tournament=self.request.user.profile.tournament
        )
        return obj


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("feedback.add_chairfeedbackcriterion", raise_exception=False),
    name="dispatch",
)
class ChairFeedbackCriterionCreate(CreateView):

    model = ChairFeedbackCriterion
    fields = ["name"]

    success_url = reverse_lazy("tournament:chairfeedbackcriteria")

    def form_valid(self, form):
        form.instance.tournament = self.request.user.profile.tournament
        try:
            validation = super(ChairFeedbackCriterionCreate, self).form_valid(form)
            return validation
        except IntegrityError:
            messages.add_message(
                self.request,
                messages.ERROR,
                "Criterion %s already exists" % form.instance.name,
            )
            return redirect("tournament:chairfeedbackcriteria")


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(
        "feedback.delete_chairfeedbackcriterion", raise_exception=False
    ),
    name="dispatch",
)
class ChairFeedbackCriterionDelete(ConfirmedDeleteView):

    redirection = "tournament:chairfeedbackcriteria"

    def get_objects(self, request, *args, **kwargs):
        obj = get_list_or_404(
            ChairFeedbackCriterion,
            tournament=request.user.profile.tournament,
            id=kwargs["id"],
        )
        return obj
