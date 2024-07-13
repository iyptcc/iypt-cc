from django.apps import AppConfig


class ScheduleConfig(AppConfig):
    name = "apps.schedule"

    def ready(self):
        import apps.schedule.signals
