from django.urls import path
from oauth2_provider.urls import base_urlpatterns
from oauth2_provider.views import IntrospectTokenView, RevokeTokenView, TokenView

from . import views

app_name = "oauth2_provider"

overwrite = [
    path("authorize/", views.MyAuthorizationView.as_view(), name="authorize"),
    path("authorize", views.MyAuthorizationView.as_view(), name="authorize"),
    path("token", TokenView.as_view(), name="token"),
    path("revoke_token", RevokeTokenView.as_view(), name="revoke-token"),
    path("introspect", IntrospectTokenView.as_view(), name="introspect"),
]
urlpatterns = overwrite + base_urlpatterns
