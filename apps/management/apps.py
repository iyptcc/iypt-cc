from django.apps import AppConfig


class ManagementConfig(AppConfig):
    name = "apps.management"

    def ready(self):
        import apps.management.signals
