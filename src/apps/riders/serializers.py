# rides/serializers.py
from rest_framework import serializers
from django.contrib.gis.geos import Point
from .models import Ride

from src.apps.accounts.models import User, DriverProfile, VehicleImage
from src.apps.payments.models import Transaction
from .models import Ride, RideMessage
from .utils import calculate_dynamic_fare
from django.db.models import Avg
class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['full_name', 'phone_number', 'user_id', 'is_driver']

class RideMessageSerializer(serializers.ModelSerializer):
    """Serializes a persisted in-ride chat message."""
    sender_id = serializers.ReadOnlyField(source='sender.user_id')
    sender_name = serializers.ReadOnlyField(source='sender.full_name')

    class Meta:
        model = RideMessage
        fields = ['id', 'ride', 'sender_id', 'sender_name', 'content', 'timestamp']
        read_only_fields = fields

class RideVehicleImageSerializer(serializers.ModelSerializer):
    """Vehicle photo(s) of the driver's car, with absolute URLs."""
    image = serializers.SerializerMethodField()

    class Meta:
        model = VehicleImage
        fields = ['id', 'image']

    def get_image(self, obj):
        if not obj.image:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

class SimpleDriverProfileSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(read_only=True)
    # The driver's vehicle photos (gallery uploaded during onboarding).
    vehicle_images = RideVehicleImageSerializer(
        source='vehicle_photos', many=True, read_only=True
    )
    rating = serializers.SerializerMethodField()
    total_trips = serializers.SerializerMethodField()
    class Meta:
        model = DriverProfile
        fields = ['user', 'user_photo', 'vehicle_brand', 'vehicle_model', 'vehicle_plate', 'vehicle_type', 'last_location', 'vehicle_images','rating','total_trips']

    def get_rating(self, obj):
        avg = obj.user.reviews_received.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0.0

    def get_total_trips(self, obj):
        return obj.user.rides_as_driver.filter(status='COMPLETED').count()

class RideSerializer(serializers.ModelSerializer):
    pickup_lat = serializers.FloatField(write_only=True)
    pickup_lng = serializers.FloatField(write_only=True)
    dropoff_lat = serializers.FloatField(write_only=True)
    dropoff_lng = serializers.FloatField(write_only=True)
    
    # Allow client to set vehicle_type and payment_method
    vehicle_type = serializers.CharField(required=False, allow_blank=True, write_only=True)
    
    # Nested info
    driver_details = serializers.SerializerMethodField()
    rider_details = SimpleUserSerializer(source='rider', read_only=True)
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Ride
        fields = [
            'id', 'status', 'pickup_address', 'dropoff_address', 
            'pickup_lat', 'pickup_lng', 'dropoff_lat', 'dropoff_lng',
            'estimated_price', 'rider', 'driver', 'created_at',
            'vehicle_type', 'requested_vehicle_type',
            'driver_details', 'rider_details', 'payment_status',
            'cancellation_reason', 'cancellation_fee'
        ]
        read_only_fields = ['id', 'status', 'estimated_price', 'rider', 'driver', 'requested_vehicle_type', 
                          'cancellation_reason', 'cancellation_fee']

    def to_representation(self, instance):
        data = super().to_representation(instance)

        pickup = instance.pickup_location
        dropoff = instance.dropoff_location

        # Point(lng, lat) -> .x = longitude, .y = latitude
        data['pickup_lat'] = pickup.y if pickup else None
        data['pickup_lng'] = pickup.x if pickup else None
        data['dropoff_lat'] = dropoff.y if dropoff else None
        data['dropoff_lng'] = dropoff.x if dropoff else None
        data['is_running'] = instance.status in ['ACCEPTED', 'ARRIVED', 'STARTED']

        # --- Estimated distance & time (same logic as calculate_dynamic_fare) ---
        if pickup and dropoff:
            # PostGIS distance is in degrees, ~111.32 km per degree
            distance_km = pickup.distance(dropoff) * 111.32
            # Duration based on average speed of 40 km/h
            estimated_minutes = (distance_km / 40) * 60

            data['estimated_distance_km'] = round(distance_km, 2)
            data['estimated_time_min'] = round(estimated_minutes)
        else:
            data['estimated_distance_km'] = None
            data['estimated_time_min'] = None

        return data
    

    def get_driver_details(self, obj):
        if obj.driver and hasattr(obj.driver, 'driver_profile'):
            # Pass context (request) down so vehicle image URLs are absolute.
            return SimpleDriverProfileSerializer(
                obj.driver.driver_profile, context=self.context
            ).data
        return None

    def get_payment_status(self, obj):
        if hasattr(obj, 'transaction'):
            return obj.transaction.status
        return 'UNPAID'

    def to_internal_value(self, data):
        # Accept the rider's selected vehicle type under EITHER key
        # (`vehicle_type` or `requested_vehicle_type`) and normalize to
        # UPPERCASE. Previously only a `vehicle_type` ChoiceField was read, so a
        # client sending `requested_vehicle_type` (or anything outside
        # ECONOMY/XL/PREMIUM, e.g. SUV) silently fell back to ECONOMY.
        validated = super().to_internal_value(data)
        raw_type = data.get('vehicle_type') or data.get('requested_vehicle_type')
        if raw_type:
            validated['vehicle_type'] = str(raw_type).strip().upper()
        return validated

    def create(self, validated_data):
        # Extract Lat/Lng and convert to PostGIS Point
        p_lat = validated_data.pop('pickup_lat')
        p_lng = validated_data.pop('pickup_lng')
        d_lat = validated_data.pop('dropoff_lat')
        d_lng = validated_data.pop('dropoff_lng')

        # Resolve the requested vehicle type. IMPORTANT: pop BOTH keys
        # unconditionally so neither leaks into Ride.objects.create() (the
        # model has no `vehicle_type` field). Prefer an explicit
        # requested_vehicle_type handed in by the view via .save(...), then the
        # serializer's own vehicle_type field, then fall back to ECONOMY.
        # Always normalized to UPPERCASE so it matches drivers via iexact.
        requested_type = validated_data.pop('requested_vehicle_type', None)
        field_type = validated_data.pop('vehicle_type', None)
        v_type = requested_type or field_type or 'ECONOMY'
        v_type = str(v_type).strip().upper()
        validated_data['requested_vehicle_type'] = v_type

        validated_data['pickup_location'] = Point(p_lng, p_lat, srid=4326)
        validated_data['dropoff_location'] = Point(d_lng, d_lat, srid=4326)

        # Calculate Dynamic Fare
        validated_data['estimated_price'] = calculate_dynamic_fare(
            validated_data['pickup_location'],
            validated_data['dropoff_location'],
            v_type
        )

        return super().create(validated_data)
