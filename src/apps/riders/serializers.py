# rides/serializers.py
from rest_framework import serializers
from django.contrib.gis.geos import Point
from .models import Ride

class RideSerializer(serializers.ModelSerializer):
    pickup_lat = serializers.FloatField(write_only=True)
    pickup_lng = serializers.FloatField(write_only=True)
    dropoff_lat = serializers.FloatField(write_only=True)
    dropoff_lng = serializers.FloatField(write_only=True)

    class Meta:
        model = Ride
        fields = [
            'id', 'status', 'pickup_address', 'dropoff_address', 
            'pickup_lat', 'pickup_lng', 'dropoff_lat', 'dropoff_lng',
            'estimated_price', 'rider', 'driver', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'estimated_price', 'rider', 'driver']

    def create(self, validated_data):
        # Extract Lat/Lng and convert to PostGIS Point
        p_lat = validated_data.pop('pickup_lat')
        p_lng = validated_data.pop('pickup_lng')
        d_lat = validated_data.pop('dropoff_lat')
        d_lng = validated_data.pop('dropoff_lng')

        validated_data['pickup_location'] = Point(p_lng, p_lat, srid=4326)
        validated_data['dropoff_location'] = Point(d_lng, d_lat, srid=4326)
        
        # Calculate Dummy Fare (We will improve this in Step B)
        # For now, let's just set a flat 15.00 for testing
        validated_data['estimated_price'] = 15.00 
        
        return super().create(validated_data)