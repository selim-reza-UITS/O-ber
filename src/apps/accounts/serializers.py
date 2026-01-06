from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import RiderProfile, DriverProfile

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

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        validate_password(attrs['password'])
        return attrs

    def to_representation(self, instance):
        """Custom response: Includes user details + JWT Tokens after signup"""
        data = super().to_representation(instance)
        refresh = RefreshToken.for_user(instance)
        data['tokens'] = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        # Add initials if no photo (UI logic for Flutter)
        names = instance.full_name.split()
        initials = "".join([n[0].upper() for n in names[:2]])
        data['user_initials'] = initials
        return data

class LoginSerializer(serializers.Serializer):
    """Handles Email or Phone login"""
    username = serializers.CharField() # Flutter can send email OR phone here
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