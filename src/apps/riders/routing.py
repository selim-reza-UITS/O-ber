# src/apps/riders/routing.py
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    # Trip Tracking (Driver location updates)
    path("ws/ride/<str:ride_id>/", consumers.TripTrackingConsumer.as_asgi()),
    
    # Ride Chat
    path("ws/ride/chat/<str:ride_id>/", consumers.RideChatConsumer.as_asgi()),
    
    # Driver Discovery (Live Ride Requests)
    path("ws/drivers/discovery/", consumers.DriverDiscoveryConsumer.as_asgi()),
]