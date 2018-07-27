import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer


class ChatConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = 'chat_%s' % self.room_name

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    def receive_json(self, content):
        text_data_json = content
        message = text_data_json['message']

        # Send message to room group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )

    # Receive message from room group
    def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        self.send_json(content={
            'message': message
        })

class FightControlConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['fight_id']
        #print(self.scope["user"].profile.tournament)
        self.room_group_name = '%s_fight_%s' % (self.scope["user"].profile.tournament.slug, self.room_name)
        print(self.room_group_name)

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    def receive_json(self, content):
        action = content['action']

        # Send message to room group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': "clock_action",
                'action': action
            }
        )

    # Receive message from room group
    def clock_action(self, event):
        action = event['action']

    def clock_state(self, event):
        state = event["state"]
        self.send_json(content={'state': state})



class FightViewConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['fight_id']
        #print(self.scope["user"].profile.tournament)
        self.room_group_name = '%s_fight_%s' % (self.scope["user"].profile.tournament.slug, self.room_name)

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    def receive_json(self, content):
        state = content['state']
        print("received state")
        print(state)
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name, {'type': "clock_state", 'state': state}
        )



    # Receive message from room group
    def clock_action(self, event):
        action = event['action']

        # Send message to WebSocket
        self.send_json(content={
            'action': action
        })

    def clock_state(self,event):
        pass
