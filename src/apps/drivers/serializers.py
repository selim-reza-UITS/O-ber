from rest_framework import serializers
from django.db.models import Avg, Sum
from src.apps.accounts.models import DriverProfile
from datetime import timedelta
from django.utils import timezone

class DriverDashboardSerializer(serializers.ModelSerializer):
    rating = serializers.SerializerMethodField()
    total_rides = serializers.SerializerMethodField()
    this_week_rides = serializers.SerializerMethodField()
    active_hours_30_days = serializers.SerializerMethodField()
    vehicle_photos = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='image'
    )

    class Meta:
        model = DriverProfile
        fields = [
            'rating', 'total_rides', 'this_week_rides', 'active_hours_30_days',
            'user_photo', 'vehicle_type', 'vehicle_brand', 'vehicle_model', 
            'vehicle_plate', 'is_online', 'is_active', 'vehicle_photos'
        ]

    def get_rating(self, obj):
        avg = obj.user.reviews_received.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0.0

    def get_total_rides(self, obj):
        return obj.user.rides_as_driver.filter(status='COMPLETED').count()

    def get_this_week_rides(self, obj):
        last_7_days = timezone.now() - timedelta(days=7)
        return obj.user.rides_as_driver.filter(
            status='COMPLETED', 
            created_at__gte=last_7_days
        ).count()

    def get_active_hours_30_days(self, obj):
        last_30_days = timezone.now() - timedelta(days=30)
        shifts = obj.shifts.filter(start_time__gte=last_30_days, end_time__isnull=False)
        total_duration = sum([s.duration for s in shifts], timedelta())
        return f"{int(total_duration.total_seconds() // 3600)}hrs"