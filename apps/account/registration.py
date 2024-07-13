from captcha.fields import CaptchaField
from django_registration.backends.activation.views import (
    RegistrationView as OrigRegistrationView,
)
from django_registration.forms import RegistrationFormTermsOfService
from django_registration.signals import user_activated

from apps.account.models import ActiveUser


class RegistrationCaptcha(RegistrationFormTermsOfService):
    captcha = CaptchaField()


class RegistrationView(OrigRegistrationView):

    form_class = RegistrationCaptcha


def create_profile(sender, **kwargs):
    print("user was activated, create profile")

    ActiveUser.objects.create(user=kwargs["user"])


user_activated.connect(create_profile)
