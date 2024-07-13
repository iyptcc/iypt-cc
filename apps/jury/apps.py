from django.apps import AppConfig


class JuryConfig(AppConfig):
    name = "apps.jury"

    def ready(self):
        import apps.jury.signals
