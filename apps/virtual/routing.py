# chat/routing.py
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r"^ws/virtual/clock/(?P<fight_id>[0-9]+)/(?P<stage>[0-9])/view/$",
        consumers.FightViewConsumer.as_asgi(),
    ),
    # url(r'^ws/clocks/(?P<round_id>[0-9]+)/$', consumers.RoundViewConsumer.as_asgi()),
]
