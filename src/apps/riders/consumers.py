import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from .models import RideMessage
from src.apps.riders.models import Ride
from urllib.parse import parse_qs
User = get_user_model()

class TripTrackingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.ride_id = self.scope['url_route']['kwargs']['ride_id']
        self.room_group_name = f'ride_{self.ride_id}'

        # Join the trip room
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # This method receives data from the REST view and sends it to the phone
    async def ride_update(self, event):
        await self.send(text_data=json.dumps(event['data']))

class RideChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 1. JWT Authentication — try query param first (browsers can't send
        #    custom headers on WebSocket), then fall back to Authorization header.
        token = None

        query_string = self.scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        token_list = query_params.get("token", [])
        if token_list:
            token = token_list[0]

        if not token:
            for header in self.scope.get("headers", []):
                if header[0] == b"authorization":
                    token = header[1].decode().split(" ")[-1]
                    break

        if not token:
            await self.close()
            return

        try:
            validated = UntypedToken(token)
            user_id = validated.payload.get("user_id")
            self.user = await database_sync_to_async(User.objects.get)(user_id=user_id)
        except (InvalidToken, TokenError, User.DoesNotExist):
            await self.close()
            return

        # 2. Ride Validation
        # Room is based on Ride ID: ws/chat/ride/<ride_id>/
        self.ride_id = self.scope["url_route"]["kwargs"].get("ride_id")
        self.ride = await self.get_ride(self.ride_id)

        # Ensure the user is either the rider or the driver of this specific ride
        if not self.ride or (self.user != self.ride.rider and self.user != self.ride.driver):
            await self.close()
            return

        self.room_group_name = f"ride_chat_{self.ride_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = data.get('content')

        # Save to DB
        await self.save_ride_message(content)

        # Broadcast to both Rider and Driver
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'content': content,
                'sender_id': self.user.user_id,
                'sender_name': self.user.full_name
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_ride(self, ride_id):
        try:
            return Ride.objects.select_related('rider', 'driver').get(id=ride_id)
        except Ride.DoesNotExist:
            return None

    @database_sync_to_async
    def save_ride_message(self, content):
        return RideMessage.objects.create(
            ride=self.ride,
            sender=self.user,
            content=content
        )
    
class DriverDiscoveryConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 1. JWT Authentication — same pattern as RideChatConsumer.
        #    Try ?token= query param first (browsers can't send custom WS headers),
        #    then fall back to the Authorization header.
        token = None

        query_string = self.scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)

        token_list = query_params.get("token", [])
        if token_list:
            token = token_list[0]

        if not token:
            for header in self.scope.get("headers", []):
                if header[0] == b"authorization":
                    token = header[1].decode().split(" ")[-1]
                    break

        if not token:
            await self.close()
            return

        try:
            validated = UntypedToken(token)
            user_id = validated.payload.get("user_id")
            self.user = await database_sync_to_async(User.objects.get)(user_id=user_id)
        except (InvalidToken, TokenError, User.DoesNotExist):
            await self.close()
            return

        # 2. Get vehicle type from the URL: ws://.../?vehicle_type=XL&token=...
        #    Default to ECONOMY if not provided
        self.vehicle_type = query_params.get("vehicle_type", ["ECONOMY"])[0].upper()

        # 3. Define group names
        self.general_group = "drivers_discovery"
        self.type_group = f"drivers_{self.vehicle_type}"
        # Personal group so the server can target THIS driver only (geofenced ride pushes)
        self.personal_group = f"driver_{self.user.user_id}"

        # 4. Join groups
        await self.channel_layer.group_add(self.general_group, self.channel_name)
        await self.channel_layer.group_add(self.type_group, self.channel_name)
        await self.channel_layer.group_add(self.personal_group, self.channel_name)

        await self.accept()

        # Confirm connection to the driver
        await self.send(text_data=json.dumps({
            "status": "Connected",
            "subscribed_to": self.type_group
        }))

    async def disconnect(self, close_code):
        # Leave groups on disconnect (guard against close before groups were set)
        if hasattr(self, "general_group"):
            await self.channel_layer.group_discard(self.general_group, self.channel_name)
        if hasattr(self, "type_group"):
            await self.channel_layer.group_discard(self.type_group, self.channel_name)
        if hasattr(self, "personal_group"):
            await self.channel_layer.group_discard(self.personal_group, self.channel_name)

    async def receive(self, text_data):
        """ Handles messages sent FROM the driver (like location updates) """
        try:
            data = json.loads(text_data or "{}")
        except (ValueError, TypeError):
            return
        if data.get("type") in ("ping", "heartbeat"):
            await self.send(text_data=json.dumps({"type": "pong"}))
        
        # Example: If driver sends a message, broadcast it to the whole discovery group
        await self.channel_layer.group_send(
            self.general_group,
            {
                "type": "broadcast_message",
                "message": text_data
            }
        )

    async def broadcast_message(self, event):
        await self.send(text_data=event["message"])

    async def new_ride_available(self, event):
        """ 
        This is triggered by the CreateRideView. 
        
        It sends the ride details only to drivers in the matching vehicle group.
        """
        await self.send(text_data=json.dumps({
            "type": "NEW_RIDE_REQUEST",
            "data": event["data"]
        }))
