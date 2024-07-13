from django.apps import AppConfig


class VirtualConfig(AppConfig):
    name = "apps.virtual"

    def ready(self):
        import apps.virtual.signals

        pass
