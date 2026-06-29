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
    # Exposes admin approval as a clear `is_verified` flag for the apps.
    is_verified = serializers.BooleanField(source='admin_verified', read_only=True)

    class Meta:
        model = DriverProfile
        fields = [
            'user_photo', 'date_of_birth', 'gender', 
            'nid_front', 'nid_back', 'license_front', 'license_back',
            'vehicle_type', 'vehicle_brand', 'vehicle_model', 'registration_photo',
            'ai_verified', 'admin_verified', 'is_verified', 'is_active', 'vehicle_photos'
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
    full_name = serializers.CharField(source='user.full_name', required=False)
    phone_number = serializers.CharField(source='user.phone_number', required=False)

    class Meta:
        model = RiderProfile
        fields = ['full_name', 'phone_number', 'user_photo']

    def update(self, instance, validated_data):
        # Update User model (full_name, phone_number)
        user_data = validated_data.pop('user', {})
        
        if 'full_name' in user_data:
            instance.user.full_name = user_data['full_name']
        if 'phone_number' in user_data:
            instance.user.phone_number = user_data['phone_number']
            
        if user_data:
            instance.user.save()
        
        # Update RiderProfile (user_photo)
        instance.user_photo = validated_data.get('user_photo', instance.user_photo)
        instance.save()
        return instance

class DriverProfileUpdateSerializer(serializers.ModelSerializer):
    # These live on the User model, not on DriverProfile.
    full_name = serializers.CharField(source='user.full_name', required=False)
    phone_number = serializers.CharField(
        source='user.phone_number', required=False, allow_blank=True
    )

    class Meta:
        model = DriverProfile
        # Editable, non-document driver fields (documents like NID/license stay
        # out of the instant update because they require admin re-verification).
        fields = [
            'full_name', 'phone_number', 'user_photo',
            'date_of_birth', 'gender',
            'vehicle_type', 'vehicle_brand', 'vehicle_model',
        ]
        extra_kwargs = {
            'user_photo': {'required': False},
            'date_of_birth': {'required': False},
            'gender': {'required': False},
            'vehicle_type': {'required': False},
            'vehicle_brand': {'required': False},
            'vehicle_model': {'required': False},
        }

    # Image fields that should only accept real uploaded files.
    IMAGE_FIELDS = ['user_photo']

    def to_internal_value(self, data):
        """Make multipart updates forgiving of common frontend habits:
        - Re-sending an existing image URL (a string) instead of a new file
          would otherwise raise "The submitted data was not a file" (400).
        - Sending empty strings for optional fields would fail validation.
        In both cases we simply drop the key so the existing value is kept.
        """
        if hasattr(data, 'copy'):
            data = data.copy()

        # 1. Drop image fields that aren't actual uploaded files.
        for field_name in self.IMAGE_FIELDS:
            if field_name in data and not hasattr(data.get(field_name), 'read'):
                data.pop(field_name)

        # 2. Drop blank/empty optional values ("" -> keep current value).
        for key in list(data.keys()):
            value = data.get(key)
            if isinstance(value, str) and value.strip() == '':
                data.pop(key)

        return super().to_internal_value(data)

    def update(self, instance, validated_data):
        # 1. User-level fields (full_name / phone_number)
        user_data = validated_data.pop('user', {})
        if 'full_name' in user_data:
            instance.user.full_name = user_data['full_name']
        if 'phone_number' in user_data:
            instance.user.phone_number = user_data['phone_number']
        if user_data:
            instance.user.save()

        # 2. DriverProfile fields — only the ones actually sent
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def to_representation(self, instance):
        """Return a consistent payload (with absolute photo URL)."""
        request = self.context.get('request')
        data = {
            'user_id': instance.user.user_id,
            'full_name': instance.user.full_name,
            'phone_number': instance.user.phone_number,
            'email': instance.user.email,
            'date_of_birth': instance.date_of_birth,
            'gender': instance.gender,
            'vehicle_type': instance.vehicle_type,
            'vehicle_brand': instance.vehicle_brand,
            'vehicle_model': instance.vehicle_model,
            'is_verified': instance.admin_verified,
        }
        if instance.user_photo:
            data['user_photo'] = (
                request.build_absolute_uri(instance.user_photo.url)
                if request else instance.user_photo.url
            )
        else:
            data['user_photo'] = None
        return data
class DriverPendingUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PendingDriverUpdate
        fields = [
            'full_name', 'user_photo', 'gender', 'nid_front', 'nid_back', 
            'license_front', 'license_back', 'vehicle_type', 
            'vehicle_brand', 'vehicle_model', 'registration_photo'
        ]