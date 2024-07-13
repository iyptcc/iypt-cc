from django.contrib.auth.hashers import check_password
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication

from ..models import Token


class TrnTokenAuthentication(TokenAuthentication):
    model = Token

    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            if not key.startswith("iyptcc."):
                raise exceptions.AuthenticationFailed(_("Not an IYPTCC token."))
            parts = key.split(".")
            token = model.objects.select_related("user").get(user_id=parts[1])
            if not check_password(parts[2], token.key):
                raise exceptions.AuthenticationFailed(_("Invalid token."))

        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("Invalid token."))

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed(_("User inactive or deleted."))

        return (token.user, token)
