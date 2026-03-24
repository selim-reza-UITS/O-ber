from rest_framework import serializers
from django.db.models import Avg
from .models import TermsAndConditionsModel, PrivacyAndPolicyModel, AboutUs, HelpSupport, PriceConfig, Notification, Commision
from src.apps.accounts.models import User, DriverProfile, PendingDriverUpdate
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
    commission_data = serializers.SerializerMethodField()
    
    class Meta:
        model = PriceConfig
        fields = ['id', 'vehicle_type', 'base_fare', 'price_per_km', 'price_per_minute', 'aruba_tax_percentage', 'commission_data']
    
    def get_commission_data(self, obj):
        """Get commission data for this price config"""
        try:
            commission = Commision.objects.latest('created_at')
            return {
                'id': commission.id,
                'platform_commission': float(commission.commision),
                'driver_commission': 100 - float(commission.commision)
            }
        except Commision.DoesNotExist:
            return None

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'



class AdminUserListSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['profile_picture', 'user_id', 'full_name', 'email', 'phone_number', 'is_driver', 'status', 'created_at', 'updated_at', 'date_joined']


    def get_profile_picture(self, obj):
        request = self.context.get('request')
        photo_url = None
        
        if isinstance(obj, DriverProfile):
            photo_url = obj.user_photo.url if obj.user_photo else None
        elif obj.is_driver and hasattr(obj, 'driver_profile'):
            photo_url = obj.driver_profile.user_photo.url if obj.driver_profile.user_photo else None
        elif hasattr(obj, 'rider_profile'):
            photo_url = obj.rider_profile.user_photo.url if obj.rider_profile.user_photo else None
        
        if photo_url and request:
            return request.build_absolute_uri(photo_url)
        return photo_url
    
    def get_status(self, obj):
        if not obj.is_active:
            return "Blocked"
        
        if obj.is_driver and hasattr(obj, 'driver_profile'):
            driver_profile = obj.driver_profile
            if driver_profile.admin_verified:
                return "Verified"
            elif driver_profile.ai_verified:
                return "AI Verified"
            else:
                return "Pending Verification"
        
        if obj.is_active:
            return "Active"
        
        return "Blocked"





    




class AdminTransactionSerializer(serializers.ModelSerializer):
    ride_id = serializers.ReadOnlyField(source='ride.id')
    driver_name = serializers.ReadOnlyField(source='ride.driver.full_name')
    rider_name = serializers.ReadOnlyField(source='ride.rider.full_name')
    pickup = serializers.ReadOnlyField(source='ride.pickup_address')
    dropoff = serializers.ReadOnlyField(source='ride.dropoff_address')
    total_earnings = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = ['id', 'ride_id', 'driver_name', 'rider_name', 'pickup', 'dropoff', 'amount', 'status', 'total_earnings', 'created_at']
        read_only_fields = ['id', 'ride_id', 'driver_name', 'rider_name', 'pickup', 'dropoff', 'amount', 'status', 'total_earnings', 'created_at']
    
    def get_total_earnings(self, obj):
        from django.db.models import Sum
        total = Transaction.objects.filter(status='SUCCESS').aggregate(Sum('amount'))['amount__sum']
        return float(total) if total else 0.0
        



class AdminRideListSerializer(serializers.ModelSerializer):
    rider_name = serializers.ReadOnlyField(source='rider.full_name')
    driver_name = serializers.ReadOnlyField(source='driver.full_name')
    distance = serializers.SerializerMethodField()
    
    class Meta:
        model = Ride
        fields = ['id', 'status', 'rider_name', 'driver_name', 'pickup_address', 'dropoff_address', 'distance', 'created_at', 'estimated_price']
    
    def get_distance(self, obj):
        if obj.pickup_location and obj.dropoff_location:
            distance_m = obj.pickup_location.distance(obj.dropoff_location)
            distance_km = distance_m * 111.32
            return round(distance_km, 2)
        return None


class AdminRideDetailSerializer(serializers.ModelSerializer):
    rider_name = serializers.ReadOnlyField(source='rider.full_name')
    rider_id = serializers.ReadOnlyField(source='rider.user_id')
    driver_name = serializers.ReadOnlyField(source='driver.full_name')
    driver_id = serializers.ReadOnlyField(source='driver.user_id')
    driver_ratings = serializers.SerializerMethodField(read_only=True)
    driver_total_trip_count = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Ride
        fields = [
            'id', 'driver_ratings', 'driver_total_trip_count', 'status', 'rider_name', 'rider_id', 'driver_name', 'driver_id',
            'pickup_address', 'dropoff_address', 'pickup_location', 'dropoff_location',
            'estimated_price', 'final_price', 'requested_vehicle_type', 'payment_method',
            'created_at', 'arrival_time', 'start_time', 'drop_off_time', 'cancelled_by', 'cancellation_reason', 'cancellation_fee'
        ]
    
    def get_driver_ratings(self, obj):
        try:
            if obj.driver and obj.driver.user:
                avg_rating = obj.driver.user.reviews_received.aggregate(Avg('rating'))['rating__avg']
                return round(avg_rating, 1) if avg_rating else 0.0
            return 0.0
        except Exception as e:
            return 0.0
    
    def get_driver_total_trip_count(self, obj):
        try:
            if obj.driver and obj.driver.user:
                return obj.driver.user.rides_as_driver.filter(status='COMPLETED').count()
            return 0
        except Exception as e:
            return 0
        

class AdminDriverListSerializer(serializers.ModelSerializer):
    user_id = serializers.ReadOnlyField(source='user.user_id')
    full_name = serializers.ReadOnlyField(source='user.full_name')
    email = serializers.ReadOnlyField(source='user.email')
    phone_number = serializers.ReadOnlyField(source='user.phone_number')
    profile_picture = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = DriverProfile
        fields = ['user_id', 'full_name', 'email', 'phone_number', 'profile_picture', 'status', 'is_rejected', 'created_at']
    
    def get_profile_picture(self, obj):
        if obj.user_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user_photo.url)
            return obj.user_photo.url
        return None
    
    def get_status(self, obj):
        if obj.is_rejected:
            return "Rejected"
        elif obj.admin_verified:
            return "Verified"
        elif obj.ai_verified:
            return "AI Verified"
        else:
            return "Pending Verification"



class DriverDetailSerializer(serializers.ModelSerializer):
    user_id = serializers.ReadOnlyField(source='user.user_id')
    full_name = serializers.ReadOnlyField(source='user.full_name')
    email = serializers.ReadOnlyField(source='user.email')
    phone_number = serializers.ReadOnlyField(source='user.phone_number')
    profile_picture = serializers.SerializerMethodField()
    driver_ratings = serializers.SerializerMethodField(read_only=True)
    driver_total_trip_count = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = DriverProfile
        fields = [
            'user_id', 'full_name', 'email', 'phone_number', 'profile_picture', 'driver_ratings', 'driver_total_trip_count',
            'date_of_birth', 'gender', 'nid_number', 'driver_license_number',
            'nid_front', 'nid_back', 'license_front', 'license_back',
            'vehicle_type', 'vehicle_brand', 'vehicle_model', 'vehicle_plate', 'registration_photo',
            'ai_verified', 'admin_verified', 'is_rejected', 'created_at'
        ]
    
    def get_profile_picture(self, obj):
        if obj.user_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user_photo.url)
            return obj.user_photo.url
        return None
    
    def get_driver_ratings(self, obj):
        try:
            if obj.user:
                avg_rating = obj.user.reviews_received.aggregate(Avg('rating'))['rating__avg']
                return round(avg_rating, 1) if avg_rating else 0.0
            return 0.0
        except Exception as e:
            return 0.0
    
    def get_driver_total_trip_count(self, obj):
        try:
            if obj.user:
                return obj.user.rides_as_driver.filter(status='COMPLETED').count()
            return 0
        except Exception as e:
            return 0

class AdminProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['user_id', 'admin_profile_image', 'full_name', 'email', 'phone_number']
        read_only_fields = ['user_id', 'email', 'phone_number']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        
        # Build absolute URL for admin_profile_image
        if instance.admin_profile_image and request:
            data['admin_profile_image'] = request.build_absolute_uri(instance.admin_profile_image.url)
        elif instance.admin_profile_image:
            data['admin_profile_image'] = instance.admin_profile_image.url
        else:
            data['admin_profile_image'] = None
            
        return data


class AdminPasswordUpdateSerializer(serializers.Serializer):
    """Serializer for admin password update with validation"""
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, min_length=8)
    confirm_new_password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError({"confirm_new_password": "Passwords do not match."})
        return data

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value
    




class CashWithdrawSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=10)
    destination_account = serializers.CharField(max_length=100)
    transfer_group = serializers.CharField(max_length=100)



class CommisionSerializer(serializers.ModelSerializer):
    driver_commission = serializers.SerializerMethodField()
    platform_commission = serializers.SerializerMethodField()
    applies_to = serializers.SerializerMethodField()
    
    class Meta:
        model = Commision
        fields = ['id', 'commision', 'driver_commission', 'platform_commission', 'applies_to', 'created_at', 'updated_at']
        read_only_fields = ['id', 'driver_commission', 'platform_commission', 'applies_to', 'created_at', 'updated_at']
    
    def get_driver_commission(self, obj):
        """Driver earnings percentage"""
        return 100 - float(obj.commision)
    
    def get_platform_commission(self, obj):
        """Platform commission percentage"""
        return float(obj.commision)
    
    def get_applies_to(self, obj):
        """Shows this applies to all vehicle types and all drivers"""
        return "All Vehicle Types (ECONOMY, XL, PREMIUM) for All Drivers"
    
    def validate_commision(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Commission percentage must be between 0 and 100")
        return value
    
    def validate_commision(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Commission percentage must be between 0 and 100")
        return value
    

class BlockSerilaizer(serializers.ModelSerializer):
    is_blocked_status = serializers.CharField(source='get_is_blocked_display', read_only=True)
    
    class Meta:
        model = User
        fields = ['user_id', 'full_name', 'email', 'phone_number', 'is_blocked', 'is_blocked_status', 'is_active']
        read_only_fields = ['user_id', 'full_name', 'email', 'phone_number', 'is_active']