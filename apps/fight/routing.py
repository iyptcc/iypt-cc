# chat/routing.py
from django.conf.urls import url

from . import consumers

websocket_urlpatterns = [
    url(r'^ws/clock/(?P<fight_id>[0-9]+)/control/$', consumers.FightControlConsumer),
    url(r'^ws/clock/(?P<fight_id>[0-9]+)/view/$', consumers.FightViewConsumer),
]
