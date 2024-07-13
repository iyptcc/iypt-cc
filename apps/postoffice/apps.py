from django.apps import AppConfig


class PostofficeConfig(AppConfig):
    name = "apps.postoffice"

    def ready(self):
        import apps.postoffice.signals

        pass
