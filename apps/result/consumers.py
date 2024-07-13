import json
from datetime import datetime, timedelta

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.utils import timezone

from apps.plan.models import Fight, Stage
from apps.tournament.models import Phase


class ClockConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["fight_id"]
        self.stage = self.scope["url_route"]["kwargs"]["stage"]
        # print(self.scope["user"].profile.tournament)
        #
        # print(self.room_group_name)

        try:
            fi = Fight.objects.get(pk=self.room_name)
        except:
            self.close()
            return

        if not fi.round.tournament.public_clock:
            self.close()
            return

        self.room_group_name = "%s_fight_%s_%s" % (
            fi.round.tournament.slug,
            self.room_name,
            self.stage,
        )
        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name, self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name, self.channel_name
        )

    # Receive message from WebSocket
    def receive_json(self, content):
        pass

    # Receive message from room group
    def clock_action(self, event):
        pass

    def clock_state(self, event):
        state = event["state"]
        self.send_json(content={"state": state})
