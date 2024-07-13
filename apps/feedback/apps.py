from django.apps import AppConfig


class FeedbackConfig(AppConfig):
    name = "apps.feedback"

    def ready(self):
        import apps.feedback.signals  # noqa: F401
