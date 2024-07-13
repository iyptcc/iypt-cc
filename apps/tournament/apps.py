from django.apps import AppConfig


class TournamentConfig(AppConfig):
    name = "apps.tournament"

    def ready(self):
        import apps.tournament.signals

        pass
