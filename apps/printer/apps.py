from django.apps import AppConfig


class PrinterConfig(AppConfig):
    name = 'apps.printer'

    def ready(self):
        import apps.printer.signals
