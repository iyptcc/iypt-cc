from django.apps import AppConfig


class ResultConfig(AppConfig):
    name = 'apps.result'

    def ready(self):
        import apps.result.signals
