from django.apps import AppConfig


class AccountConfig(AppConfig):
    name = "apps.account"

    def ready(self):
        import apps.account.guide  # noqa: F401
        import apps.account.signals  # noqa: F401
