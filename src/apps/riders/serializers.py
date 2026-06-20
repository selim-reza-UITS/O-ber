# rides/serializers.py
from rest_framework import serializers
from django.contrib.gis.geos import Point
from .models import Ride
from src.apps.accounts.models import User, DriverProfile
from src.apps.payments.models import Transaction

from .utils import calculate_dynamic_fare

class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['full_name', 'phone_number', 'user_id', 'is_driver']

class SimpleDriverProfileSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(read_only=True)
    class Meta:
        model = DriverProfile
        fields = ['user', 'user_photo', 'vehicle_brand', 'vehicle_model', 'vehicle_plate', 'vehicle_type', 'last_location']

class RideSerializer(serializers.ModelSerializer):
    pickup_lat = serializers.FloatField(write_only=True)
    pickup_lng = serializers.FloatField(write_only=True)
    dropoff_lat = serializers.FloatField(write_only=True)
    dropoff_lng = serializers.FloatField(write_only=True)
    
    # Allow client to set vehicle_type and payment_method
    vehicle_type = serializers.ChoiceField(choices=['ECONOMY', 'XL', 'PREMIUM'], default='ECONOMY', write_only=True)
    
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
            return SimpleDriverProfileSerializer(obj.driver.driver_profile).data
        return None

    def get_payment_status(self, obj):
        if hasattr(obj, 'transaction'):
            return obj.transaction.status
        return 'UNPAID'

    def create(self, validated_data):
        # Extract Lat/Lng and convert to PostGIS Point
        p_lat = validated_data.pop('pickup_lat')
        p_lng = validated_data.pop('pickup_lng')
        d_lat = validated_data.pop('dropoff_lat')
        d_lng = validated_data.pop('dropoff_lng')
        
        # Handle vehicle type
        v_type = validated_data.pop('vehicle_type', 'ECONOMY')
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

