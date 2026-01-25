from rest_framework import serializers
from .models import TermsAndConditionsModel, PrivacyAndPolicyModel, AboutUs, HelpSupport, PriceConfig, Notification
from src.apps.accounts.models import User, DriverProfile
from src.apps.riders.models import Ride
from src.apps.payments.models import Transaction

class TermsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsAndConditionsModel
        fields = ['content']

class PrivacySerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacyAndPolicyModel
        fields = ['content']

class AboutUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutUs
        fields = ['content']

class HelpSupportSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpSupport
        fields = ['id', 'message', 'created_at', 'is_resolved']
        read_only_fields = ['id', 'created_at', 'is_resolved']

class PriceConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceConfig
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'

class AdminUserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['user_id', 'full_name', 'email', 'phone_number', 'is_rider', 'is_driver', 'date_joined']

class AdminTransactionSerializer(serializers.ModelSerializer):
    ride_id = serializers.ReadOnlyField(source='ride.id')
    payer_name = serializers.ReadOnlyField(source='ride.rider.full_name')
    
    class Meta:
        model = Transaction
        fields = ['id', 'ride_id', 'payer_name', 'amount', 'status', 'created_at']

class AdminRideListSerializer(serializers.ModelSerializer):
    rider_name = serializers.ReadOnlyField(source='rider.full_name')
    driver_name = serializers.ReadOnlyField(source='driver.full_name')
    
    class Meta:
        model = Ride
        fields = ['id', 'status', 'rider_name', 'driver_name', 'pickup_address', 'dropoff_address', 'created_at', 'estimated_price']