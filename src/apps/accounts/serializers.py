import phonenumbers
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import RiderProfile


User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Base serializer for User details"""
    class Meta:
        model = User
        fields = ['user_id', 'full_name', 'email', 'phone_number', 'is_rider', 'is_driver']

class SignUpSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone_number', 'password', 'confirm_password']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    def validate_phone_number(self, value):
        """
        Validates Aruba (+297) phone numbers
        """
        try:
            parsed_number = phonenumbers.parse(value, "AW")
            
            if not phonenumbers.is_valid_number(parsed_number):
                raise serializers.ValidationError("Invalid Aruba phone number.")
            
            if phonenumbers.region_code_for_number(parsed_number) != "AW":
                raise serializers.ValidationError("Only Aruba (+297) phone numbers are allowed.")

            # Return the standardized international format (+297xxxxxxx)
            return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
            
        except phonenumbers.phonenumberutil.NumberParseException:
            raise serializers.ValidationError("Invalid phone format. Please enter a valid number.")
        
    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        validate_password(attrs['password'])
        return attrs

    def create(self, validated_data):
        # Remove confirm_password before creating user
        validated_data.pop('confirm_password')
        
        # Create user using the manager
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data['full_name'],
            phone_number=validated_data['phone_number'],
            is_rider=True # Default to rider
        )
        
        # Automatically create the Rider Profile
        RiderProfile.objects.create(user=user)
        return user

    def to_representation(self, instance):
        """Include JWT Tokens in response so the user is logged in immediately"""
        refresh = RefreshToken.for_user(instance)
        return {
            'user_id': instance.user_id,
            'full_name': instance.full_name,
            'email': instance.email,
            'phone_number': instance.phone_number,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }
class LoginSerializer(serializers.Serializer):
    """Handles Email or Phone login"""
    login_id = serializers.CharField() 
    password = serializers.CharField(write_only=True)

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        validate_password(attrs['new_password'])
        return attrs
