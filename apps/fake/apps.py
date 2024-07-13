from django.apps import AppConfig


class FakeConfig(AppConfig):
    name = "apps.fake"

    def ready(self):
        import apps.fake.signals  # noqa: F401
