from django import forms
from django.urls import path, re_path

from .preview import MergePreview
from .views import (
    AccountChangeView,
    AccountCreateView,
    AccountsView,
    AccountView,
    AttendeeAccountCreateView,
    AttendeeBill,
    AttendeeFeeRequestView,
    PaymentRequestView,
    PFeeCreate,
    PFeeDelete,
    PFeeView,
    RoleFeeUpdate,
    RolesView,
    SettleView,
    TeamAccountCreateView,
    TeamBill,
    TeamFeePartsRequestView,
    TeamFeeView,
)

app_name = "bank"

urlpatterns = [
    path("accounts/", AccountsView.as_view(), name="accounts"),
    path("accounts/create/", AccountCreateView.as_view(), name="create_account"),
    re_path(
        r"^accounts/create/attendee/(?P<attendee>[\d]+)/$",
        AttendeeAccountCreateView.as_view(),
        name="create_attendee_account",
    ),
    re_path(
        r"^accounts/create/team/(?P<team>[\d]+)/$",
        TeamAccountCreateView.as_view(),
        name="create_team_account",
    ),
    re_path(
        r"^accounts/(?P<account>[\d]+)/merge/$",
        MergePreview(forms.Form),
        name="merge_account",
    ),
    path(
        "accounts/<int:account>/payments/", AccountView.as_view(), name="list_account"
    ),
    path("accounts/<int:id>/edit/", AccountChangeView.as_view(), name="change_account"),
    path("bill/teams/", TeamBill.as_view(), name="bill_teams"),
    path("bill/attendees/", AttendeeBill.as_view(), name="bill_attendees"),
    path("fee/team/", TeamFeeView.as_view(), name="fee_team"),
    path("fee/roles/", RolesView.as_view(), name="fee_roles"),
    re_path(
        r"^fee/roles/(?P<id>[\d]+)/$", RoleFeeUpdate.as_view(), name="fee_role_edit"
    ),
    path("fee/property/", PFeeView.as_view(), name="fee_property"),
    path("fee/property/create/", PFeeCreate.as_view(), name="fee_property_create"),
    re_path(
        r"^fee/property/(?P<id>[\d]+)/delete/$",
        PFeeDelete.as_view(),
        name="fee_property_delete",
    ),
    path("payment/request/", PaymentRequestView.as_view(), name="payment_request"),
    re_path(
        r"^payment/request/team/(?P<team_id>[\d]+)/$",
        TeamFeePartsRequestView.as_view(),
        name="payment_team_request",
    ),
    re_path(
        r"^payment/request/attendee/(?P<attendee>[\d]+)/$",
        AttendeeFeeRequestView.as_view(),
        name="payment_attendee_request",
    ),
    re_path(
        r"^payment/(?P<payment>[\d]+)/settle/$",
        SettleView.as_view(),
        name="payment_settle",
    ),
]
