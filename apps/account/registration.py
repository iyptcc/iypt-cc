from registration.backends.hmac.views import RegistrationView as OrigRegistrationView
from registration.forms import RegistrationFormTermsOfService
from registration.signals import user_activated

from apps.account.models import ActiveUser


class RegistrationView(OrigRegistrationView):

    form_class = RegistrationFormTermsOfService


def create_profile(sender, **kwargs):
    print("user was activated, create profile")

    ActiveUser.objects.create(user=kwargs['user'])

user_activated.connect(create_profile)
