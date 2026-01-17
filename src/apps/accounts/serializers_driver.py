from rest_framework import serializers
from .models import DriverProfile, VehicleImage

class VehicleImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleImage
        fields = ['id', 'image']

class DriverProfileSerializer(serializers.ModelSerializer):
    vehicle_photos = VehicleImageSerializer(many=True, read_only=True)

    class Meta:
        model = DriverProfile
        fields = [
            'user_photo', 'date_of_birth', 'gender', 
            'nid_front', 'nid_back', 'license_front', 'license_back',
            'vehicle_type', 'vehicle_brand', 'vehicle_model', 'registration_photo',
            'ai_verified', 'admin_verified', 'vehicle_photos'
        ]
        read_only_fields = ['ai_verified', 'admin_verified']