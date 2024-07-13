from django.apps import AppConfig


class BankConfig(AppConfig):
    name = "apps.bank"

    def ready(self):
        import apps.bank.signals
