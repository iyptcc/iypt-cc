from django.apps import AppConfig


class PlanConfig(AppConfig):
    name = 'apps.plan'

    def ready(self):
        import apps.plan.signals
