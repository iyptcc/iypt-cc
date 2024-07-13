from django.urls import path, re_path

from .views import FeedbackChange, overview, plan

app_name = "feedback"

urlpatterns = [
    # url(r'^', include('django.contrib.auth.urls')),
    path("plan/", plan, name="plan"),
    path("overview/", overview, name="overview"),
    re_path(
        r"^edit/(?P<fight_id>[0-9]+)/(?P<t_slug>[-\w]+)/$",
        FeedbackChange.as_view(),
        name="edit",
    ),
]
