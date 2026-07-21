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
        
    def __init__(self, *args, **kwargs):
        """Make EVERY writable onboarding field mandatory with one shared
        message. This overrides model-level null/blank (e.g. date_of_birth is
        null/blank on the model but must be provided during onboarding).
        Read-only fields (id, ai_verified, admin_verified, is_verified,
        vehicle_photos, created_at, updated_at) are left untouched.
        """
        super().__init__(*args, **kwargs)
        REQUIRED_MSG = "This field is must."
        for field in self.fields.values():
            if field.read_only:
                continue
            field.required = True
            field.allow_null = False
            field.error_messages["required"] = REQUIRED_MSG
            field.error_messages["null"] = REQUIRED_MSG
            # Only text-based fields support blank; guard so we don't set an
            # unsupported attribute on ImageField / DateField / ChoiceField.
            if isinstance(field, serializers.CharField):
                field.allow_blank = False
                field.error_messages["blank"] = REQUIRED_MSG
            # Choice fields (e.g. gender) reject empty/blank with their own key.
            if isinstance(field, serializers.ChoiceField):
                field.error_messages["invalid_choice"] = REQUIRED_MSG