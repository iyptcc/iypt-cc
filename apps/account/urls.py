from django.urls import path

from .views import (
    AccountsView,
    AccountView,
    AvatarView,
    InvoiceView,
    ProfileView,
    TournamentView,
    geninvoice,
    jurorplan,
    mm_join,
)

app_name = "account"

urlpatterns = [
    # url(r'^', include('django.contrib.auth.urls')),
    path("tournament/", TournamentView.as_view(), name="tournament"),
    path("tournament/chat/", mm_join, name="join_chat"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/avatar/", AvatarView.as_view(), name="avatar"),
    path("accounts/", AccountsView.as_view(), name="accounts"),
    path("accounts/<int:account>/", AccountView.as_view(), name="list_account"),
    path("accounts/<int:a_id>/invoice/", geninvoice, name="invoice_account"),
    path(
        "accounts/<int:a_id>/invoice/<int:pdf_id>/",
        InvoiceView.as_view(),
        name="invoice_view",
    ),
    path("juror/", jurorplan, name="jury"),
]
