from django.apps import AppConfig


class RegistrationConfig(AppConfig):
    name = 'apps.registration'

    def ready(self):
        import apps.registration.signals
        pass
