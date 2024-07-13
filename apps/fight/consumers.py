import json
from datetime import datetime, timedelta

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.utils import timezone

from apps.plan.models import Fight, Stage
from apps.tournament.models import Phase

from .models import ClockState
from .utils import check_fight_permission


class RoundViewConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["round_id"]
        # print(self.scope["user"].profile.tournament)
        # self.room_group_name = '%s_fight_%s' % (self.scope["user"].profile.tournament.slug, self.room_name)

        if not self.scope["user"].has_perm("jury.clocks"):
            self.close()
            return

        self.round = (
            self.scope["user"]
            .profile.tournament.round_set(manager="selectives")
            .get(order=self.room_name)
        )

        # Join room group
        for f in self.round.fight_set.all():
            for s in f.stage_set.all():
                async_to_sync(self.channel_layer.group_add)(
                    "%s_fight_%s_%s"
                    % (self.scope["user"].profile.tournament.slug, f.id, s.order),
                    self.channel_name,
                )
        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        for f in self.round.fight_set.all():
            for s in f.stage_set.all():
                async_to_sync(self.channel_layer.group_discard)(
                    "%s_fight_%s_%s"
                    % (self.scope["user"].profile.tournament.slug, f.id, s.order),
                    self.channel_name,
                )

    # Receive message from WebSocket
    def receive_json(self, content):
        pass

    # Receive message from room group
    def clock_action(self, event):
        pass

    def clock_state(self, event):
        state = event["state"]
        fight = event["fight"]
        stage = event["stage"]
        self.send_json(content={"state": state, "fight": fight, "stage": stage})


class FightControlConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["fight_id"]
        self.stage = self.scope["url_route"]["kwargs"]["stage"]
        # print(self.scope["user"].profile.tournament)
        self.room_group_name = "%s_fight_%s_%s" % (
            self.scope["user"].profile.tournament.slug,
            self.room_name,
            self.stage,
        )
        print(self.room_group_name)

        try:
            fi = Fight.objects.get(pk=self.room_name)
        except:
            self.close()
            return

        if not check_fight_permission(self.scope["user"], fi):
            self.close()
            return

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
        action = content["action"]

        # Send message to room group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name, {"type": "clock_action", "action": action}
        )

    # Receive message from room group
    def clock_action(self, event):
        action = event["action"]

    def clock_state(self, event):
        state = event["state"]
        self.send_json(content={"state": state})


class FightViewConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["fight_id"]
        self.stage = self.scope["url_route"]["kwargs"]["stage"]
        # print(self.scope["user"].profile.tournament)
        try:
            self.room_group_name = "%s_fight_%s_%s" % (
                self.scope["user"].profile.tournament.slug,
                self.room_name,
                self.stage,
            )
            fi = Fight.objects.get(pk=self.room_name)
        except:
            self.close()
            return

        if not check_fight_permission(self.scope["user"], fi):
            self.close()
            return

        self.stage_obj = fi.stage_set.get(order=self.stage)

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name, self.channel_name
        )

        self.accept()

        self.server_state = None

    def disconnect(self, close_code):
        try:
            oldphase = Phase.objects.get(
                tournament=self.scope["user"].profile.tournament,
                pk=self.server_state["state"]["id"],
            )
            ClockState.objects.create(
                stage=self.stage_obj,
                phase=oldphase,
                elapsed=self.server_state["state"]["elapsed"],
                server_time=self.server_state["received"],
            )
        except:
            pass

        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name, self.channel_name
        )

    # Receive message from WebSocket
    def receive_json(self, content):
        state = content["state"]
        # print("received state")
        print(state)

        if self.server_state is None:
            self.server_state = {"state": state, "received": timezone.now()}

            oldphase = Phase.objects.get(
                tournament=self.scope["user"].profile.tournament,
                pk=self.server_state["state"]["id"],
            )
            ClockState.objects.create(
                stage=self.stage_obj,
                phase=oldphase,
                elapsed=self.server_state["state"]["elapsed"],
            )

        if state["id"] != self.server_state["state"]["id"]:
            print("statechange:")
            try:
                oldphase = Phase.objects.get(
                    tournament=self.scope["user"].profile.tournament,
                    pk=self.server_state["state"]["id"],
                )
                ClockState.objects.create(
                    stage=self.stage_obj,
                    phase=oldphase,
                    elapsed=self.server_state["state"]["elapsed"],
                    server_time=self.server_state["received"],
                )

                newphase = Phase.objects.get(
                    tournament=self.scope["user"].profile.tournament, pk=state["id"]
                )
                ClockState.objects.create(
                    stage=self.stage_obj, phase=newphase, elapsed=state["elapsed"]
                )

            except Exception as e:
                print(e)
            print("old", self.server_state)
            print("new", state)

        if self.server_state["received"] < (timezone.now() - timedelta(seconds=4)):
            # break of more than 4 seconds
            print("large timedelta")
            try:
                oldphase = Phase.objects.get(
                    tournament=self.scope["user"].profile.tournament,
                    pk=self.server_state["state"]["id"],
                )
                ClockState.objects.create(
                    stage=self.stage_obj,
                    phase=oldphase,
                    elapsed=self.server_state["state"]["elapsed"],
                    server_time=self.server_state["received"],
                )

                newphase = Phase.objects.get(
                    tournament=self.scope["user"].profile.tournament, pk=state["id"]
                )
                ClockState.objects.create(
                    stage=self.stage_obj, phase=newphase, elapsed=state["elapsed"]
                )
            except Exception as e:
                print(e)

        self.server_state = {"state": state, "received": timezone.now()}

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "clock_state",
                "state": state,
                "fight": self.room_name,
                "stage": self.stage,
            },
        )

    # Receive message from room group
    def clock_action(self, event):
        action = event["action"]

        # Send message to WebSocket
        self.send_json(content={"action": action})

    def clock_state(self, event):
        pass
