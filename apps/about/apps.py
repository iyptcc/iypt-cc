from django.apps import AppConfig


class AboutConfig(AppConfig):
    name = 'apps.about'

    def ready(self):
        import apps.about.signals
