import json
from channels.generic.websocket import AsyncWebsocketConsumer

class AlertConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "security_alerts"

        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Receive message from WebSocket (client to server)
    async def receive(self, text_data):
        pass

    # Receive message from group (server to client)
    async def alert_message(self, event):
        alert_data = event["alert"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            "type": "new_alert",
            "alert": alert_data
        }))
