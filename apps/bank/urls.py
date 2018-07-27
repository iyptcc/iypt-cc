from django import forms
from django.conf.urls import include, url

from .preview import MergePreview
from .views import (AccountChangeView, AccountCreateView, AccountsView, AccountView, AttendeeAccountCreateView,
                    AttendeeBill, AttendeeFeeRequestView, PaymentRequestView, PFeeCreate, PFeeDelete, PFeeView,
                    RoleFeeUpdate, RolesView, SettleView, TeamAccountCreateView, TeamBill, TeamFeeRequestView,
                    TeamFeeView)

app_name='bank'

urlpatterns = [
    url(r'^accounts/$', AccountsView.as_view() ,name="accounts" ),
    url(r'^accounts/create/$', AccountCreateView.as_view() ,name="create_account" ),
    url(r'^accounts/create/attendee/(?P<attendee>[\d]+)/$', AttendeeAccountCreateView.as_view() ,name="create_attendee_account" ),
    url(r'^accounts/create/team/(?P<team>[\d]+)/$', TeamAccountCreateView.as_view() ,name="create_team_account" ),
    url(r'^accounts/(?P<account>[\d]+)/merge/$',MergePreview(forms.Form), name="merge_account" ),
    url(r'^accounts/(?P<account>[0-9]+)/payments/$', AccountView.as_view() ,name="list_account" ),
    url(r'^accounts/(?P<id>[0-9]+)/edit/$', AccountChangeView.as_view() ,name="change_account" ),
    url(r'^bill/teams/$', TeamBill.as_view() ,name="bill_teams" ),
    url(r'^bill/attendees/$', AttendeeBill.as_view() ,name="bill_attendees" ),
    url(r'^fee/team/$', TeamFeeView.as_view() ,name="fee_team" ),
    url(r'^fee/roles/$', RolesView.as_view() ,name="fee_roles" ),
    url(r'^fee/roles/(?P<id>[\d]+)/$', RoleFeeUpdate.as_view() ,name="fee_role_edit" ),
    url(r'^fee/property/$', PFeeView.as_view() ,name="fee_property" ),
    url(r'^fee/property/create/$', PFeeCreate.as_view() ,name="fee_property_create" ),
    url(r'^fee/property/(?P<id>[\d]+)/delete/$', PFeeDelete.as_view() ,name="fee_property_delete" ),
    url(r'^payment/request/$', PaymentRequestView.as_view() ,name="payment_request" ),
    url(r'^payment/request/team/(?P<team>[\d]+)/$', TeamFeeRequestView.as_view() ,name="payment_team_request" ),
    url(r'^payment/request/attendee/(?P<attendee>[\d]+)/$', AttendeeFeeRequestView.as_view() ,name="payment_attendee_request" ),
    url(r'^payment/(?P<payment>[\d]+)/settle/$', SettleView.as_view() ,name="payment_settle" ),
]
