from django.conf.urls import include, url

from .views import AccountsView, AccountView, AvatarView, InvoiceView, ProfileView, TournamentView, geninvoice

app_name='account'

urlpatterns = [
    #url(r'^', include('django.contrib.auth.urls')),
    url(r'^tournament/$', TournamentView.as_view(),name="tournament" ),
    url(r'^profile/$', ProfileView.as_view(), name='profile'),
    url(r'^profile/avatar/$', AvatarView.as_view(), name='avatar'),
    url(r'^accounts/$', AccountsView.as_view(), name='accounts'),
    url(r'^accounts/(?P<account>[0-9]+)/$', AccountView.as_view() ,name="list_account" ),
    url(r'^accounts/(?P<a_id>[0-9]+)/invoice/$', geninvoice ,name="invoice_account" ),
    url(r'^accounts/(?P<a_id>[0-9]+)/invoice/(?P<pdf_id>[0-9]+)/$', InvoiceView.as_view() ,name="invoice_view" ),
]
