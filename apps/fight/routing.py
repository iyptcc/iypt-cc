# chat/routing.py
from django.urls import path, re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r"^ws/clock/(?P<fight_id>[0-9]+)/(?P<stage>[0-9])/control/$",
        consumers.FightControlConsumer.as_asgi(),
    ),
    re_path(
        r"^ws/clock/(?P<fight_id>[0-9]+)/(?P<stage>[0-9])/view/$",
        consumers.FightViewConsumer.as_asgi(),
    ),
    path("ws/clocks/<int:round_id>/", consumers.RoundViewConsumer.as_asgi()),
]
