from rest_framework import serializers
from .models import User,RiderProfile,DriverProfile,VehicleImage,PendingDriverUpdate

class UserBaseSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = User
        fields = ['user_id', 'full_name', 'email', 'phone_number', 'is_rider', 'is_driver']

class RiderProfileSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = RiderProfile
        fields = ['user_photo']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        
        if instance.user_photo and request:
            data['user_photo'] = request.build_absolute_uri(instance.user_photo.url)
        elif instance.user_photo:
            data['user_photo'] = instance.user_photo.url
        else:
            data['user_photo'] = None
            
        return data

class VehicleImageSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = VehicleImage
        fields = ['id', 'image']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        
        if instance.image and request:
            data['image'] = request.build_absolute_uri(instance.image.url)
        elif instance.image:
            data['image'] = instance.image.url
        else:
            data['image'] = None
            
        return data

class DriverProfileSerializer(serializers.ModelSerializer):
    vehicle_photos = VehicleImageSerializer(many=True, read_only=True)

    class Meta:
        model = DriverProfile
        fields = [
            'user_photo', 'date_of_birth', 'gender', 
            'nid_front', 'nid_back', 'license_front', 'license_back',
            'vehicle_type', 'vehicle_brand', 'vehicle_model', 'registration_photo',
            'ai_verified', 'admin_verified', 'is_active', 'vehicle_photos'
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        
        # List of image fields to convert to absolute URLs
        image_fields = ['user_photo', 'nid_front', 'nid_back', 'license_front', 'license_back', 'registration_photo']
        
        for field in image_fields:
            obj_field = getattr(instance, field, None)
            if obj_field and request:
                data[field] = request.build_absolute_uri(obj_field.url)
            elif obj_field:
                data[field] = obj_field.url
            else:
                data[field] = None
                
        return data
    

class RiderProfileUpdateSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name')

    class Meta:
        model = RiderProfile
        fields = ['full_name', 'user_photo']

    def update(self, instance, validated_data):
        # Update User model (full_name)
        user_data = validated_data.pop('user', {})
        if 'full_name' in user_data:
            instance.user.full_name = user_data['full_name']
            instance.user.save()
        
        # Update RiderProfile (user_photo)
        instance.user_photo = validated_data.get('user_photo', instance.user_photo)
        instance.save()
        return instance

class DriverPendingUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PendingDriverUpdate
        exclude = ['driver', 'created_at']