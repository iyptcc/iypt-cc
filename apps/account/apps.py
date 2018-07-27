from django.apps import AppConfig


class AccountConfig(AppConfig):
    name = 'apps.account'


    def ready(self):
        import apps.account.signals
        import apps.account.guide
