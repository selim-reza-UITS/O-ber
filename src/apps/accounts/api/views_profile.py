from django.contrib import admin
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from ..serializers_profile import (
    UserBaseSerializer, 
    RiderProfileSerializer, 
    DriverProfileSerializer,
    RiderProfileUpdateSerializer,
    DriverPendingUpdateSerializer,
)
from ..models import DriverProfile, RiderProfile,PendingDriverUpdate
from rest_framework.parsers import MultiPartParser,FormParser

class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        
        user_data = UserBaseSerializer(user).data
        
        rider_data = {}
        try:
            rider_data = RiderProfileSerializer(user.rider_profile).data
        except RiderProfile.DoesNotExist:
            rider_data = None

        driver_data = None
        if user.is_driver:
            try:
                driver_data = DriverProfileSerializer(user.driver_profile).data
            except DriverProfile.DoesNotExist:
                driver_data = "Incomplete: Onboarding required"

        response_data = {
            "user": [user_data],
            "rider_profile": [rider_data] if rider_data else [],
            "driver_profile": [driver_data] if driver_data else []
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
class UserProfileUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request):
        user = request.user
        
        # CASE 1: RIDER UPDATE (Immediate)
        if not user.is_driver:
            try:
                rider_profile = user.rider_profile
                serializer = RiderProfileUpdateSerializer(rider_profile, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response({
                        "message": "Profile updated successfully",
                        "data": serializer.data
                    }, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except RiderProfile.DoesNotExist:
                return Response({"error": "Rider profile not found"}, status=status.HTTP_404_NOT_FOUND)

        # CASE 2: DRIVER UPDATE (Queued for Approval)
        else:
            try:
                driver_profile = user.driver_profile
                # We use update_or_create to allow only ONE pending request at a time
                pending_update, created = PendingDriverUpdate.objects.get_or_create(driver=driver_profile)
                
                serializer = DriverPendingUpdateSerializer(pending_update, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    
                    # Mark profile as unverified while change is pending if necessary
                    # driver_profile.admin_verified = False 
                    # driver_profile.save()

                    return Response({
                        "message": "Update request submitted for Admin review.",
                        "status": "PENDING_APPROVAL"
                    }, status=status.HTTP_202_ACCEPTED)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except DriverProfile.DoesNotExist:
                return Response({"error": "Driver profile not found"}, status=status.HTTP_404_NOT_FOUND)
            
            
@admin.action(description="Approve selected updates and apply to live profile")
def approve_driver_updates(modeladmin, request, queryset):
    for pending in queryset:
        driver = pending.driver
        if pending.full_name:
            driver.user.full_name = pending.full_name
            driver.user.save()
        
        fields_to_update = ['user_photo', 'gender', 'nid_front', 'nid_back', 
                            'license_front', 'license_back', 'vehicle_type', 
                            'vehicle_brand', 'vehicle_model', 'registration_photo']
        
        for field in fields_to_update:
            new_value = getattr(pending, field)
            if new_value: # Only update if the field was changed in the pending request
                setattr(driver, field, new_value)
        
        driver.admin_verified = True
        driver.save()
        pending.delete()