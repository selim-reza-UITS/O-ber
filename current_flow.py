POST /drivers/toggle-online/ -> Makes the driver available in the system.
 
Next connect to websocket for getting request ws://10.10.13.22:9400/ws/drivers/discovery/
 
Create Ride (HTTP - Rider) /rider/ride/create/ (Body: pickup/dropoff coordinates).
 
(WS - Driver): discovery socket: {"event": "NEW_RIDE_REQUESTED", "ride_id": "...", "pickup_address": "..."}
 
(HTTP - Driver): POST /drivers/accept-ride/<id>/ -> Driver claims the ride.
 
As soon as a ride is ACCEPTED, both apps connect to: 
 
ws://10.10.13.22:9400/ws/ride/<ride_id>/ (For location/status updates).
ws://10.10.13.22:9400/ws/ride/chat/<ride_id>/ (For chat).
 
Location Updates (HTTP - Driver): Action: Driver app calls POST /drivers/location-update/ every 3-5 seconds with current lat/lng and ride_id.
 
Rider receives via the socket: {"type": "LOCATION_UPDATE", "lat": 1.234, "lng": 1.234}
 
Update Status (HTTP - Driver): Driver calls POST /drivers/ride-status/<ride_id>/ with body {"status": "ARRIVED"} then "STARTED".
 
Finish Trip (HTTP - Driver): Driver calls POST /drivers/ride-status/<ride_id>/ with body {"status": "COMPLETED"}.This Automatically triggers process_ride_payment.
 
Rider rates the experience.POST /rider/ride/review/ (Body: ride_id, rating, comment). 
 
#update:
 
first driver connets to it:
 
ws://10.10.13.22:9500/ws/drivers/discovery/
 
If user creates req:
{{BASE_URL}}rider/ride/create/
{
    "pickup_address": "Oranjestad, Aruba",
    "dropoff_address": "Eagle Beach, Aruba",
    "pickup_lat": 12.52,
    "pickup_lng": -70.03,
    "dropoff_lat": 12.55,
    "dropoff_lng": -70.05,
    "requested_vehicle_type": "ECONOMY"
}
 
he gets response:
{
    "id": 3,
    "status": "SEARCHING",
    "pickup_address": "Oranjestad, Aruba",
    "dropoff_address": "Eagle Beach, Aruba",
    "estimated_price": "15.00",
    "rider": "523529",
    "driver": null,
    "created_at": "2026-01-24T19:30:09.019986+06:00",
    "nearby_drivers_count": 1
}
 
 
 
and driver get response like this:
 
 
{"event": "NEW_RIDE_AVAILABLE", "ride": {"id": 3, "status": "SEARCHING", "pickup_address": "Oranjestad, Aruba", "dropoff_address": "Eagle Beach, Aruba", "estimated_price": "15.00", "rider": "523529",
19:30:09.042
 
{"status": "Connected to Discovery Group"}
19:29:59.522
 
Connected to ws://10.10.13.22:9500/ws/drivers/discovery/
 
 
 