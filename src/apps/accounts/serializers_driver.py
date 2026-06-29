from rest_framework import serializers
from .models import DriverProfile, VehicleImage

class VehicleImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = VehicleImage
        fields = ['id', 'image']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image:
            if request:
                return request.build_absolute_uri(obj.image.url)
            # fallback for environments where request context is missing
            return f"https://api.rydeislands.com{obj.image.url}"
        return None

class DriverProfileSerializer(serializers.ModelSerializer):
    vehicle_photos = VehicleImageSerializer(many=True, read_only=True)
    # Single source of truth for "is this driver verified?" -> admin approval
    is_verified = serializers.BooleanField(source='admin_verified', read_only=True)

    class Meta:
        model = DriverProfile
        fields = [ 'id',
            'user_photo', 'date_of_birth', 'gender', 
            'nid_front', 'nid_back', 'license_front', 'license_back',
            'vehicle_type', 'vehicle_brand', 'vehicle_model', 'registration_photo',
            'ai_verified', 'admin_verified', 'is_verified', 'vehicle_photos', 'created_at', 'updated_at'
        ]
        read_only_fields = ['ai_verified', 'admin_verified', 'is_verified', 'created_at', 'updated_at']