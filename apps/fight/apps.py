from django.apps import AppConfig


class FightConfig(AppConfig):
    name = 'apps.fight'

    def ready(self):
        import apps.fight.signals
        pass
