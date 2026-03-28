from django.contrib import admin
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from ..serializers_profile import (
    UserBaseSerializer, 
    RiderProfileSerializer, DriverProfileSerializer, DriverPendingUpdateSerializer,
    RiderProfileUpdateSerializer, DriverProfileUpdateSerializer
)
from ..models import DriverProfile, RiderProfile
from rest_framework.parsers import MultiPartParser,FormParser

class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        
        user_data = UserBaseSerializer(user, context={'request': request}).data
        
        rider_data = {}
        try:
            rider_data = RiderProfileSerializer(user.rider_profile, context={'request': request}).data
        except RiderProfile.DoesNotExist:
            rider_data = None

        driver_data = None
        if user.is_driver:
            try:
                driver_data = DriverProfileSerializer(user.driver_profile, context={'request': request}).data
            except DriverProfile.DoesNotExist:
                driver_data = "Incomplete: Onboarding required"

        # Combine into a single flattened dictionary
        response_data = {}
        response_data.update(user_data)
        
        if rider_data:
            response_data.update(rider_data)
            # 'id' from RiderProfile is less useful than user_id, remove if present to avoid confusion
            if 'id' in response_data:
                del response_data['id']

        if user.is_driver and driver_data and isinstance(driver_data, dict):
            response_data['driver_profile'] = driver_data

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
                serializer = RiderProfileUpdateSerializer(rider_profile, data=request.data, partial=True, context={'request': request})
                if serializer.is_valid():
                    serializer.save()
                    return Response({
                        "message": "Profile updated successfully",
                        "data": serializer.data
                    }, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except RiderProfile.DoesNotExist:
                return Response({"error": "Rider profile not found"}, status=status.HTTP_404_NOT_FOUND)

        # CASE 2: DRIVER UPDATE (Instant)
        else:
            try:
                driver_profile = user.driver_profile
                serializer = DriverProfileUpdateSerializer(driver_profile, data=request.data, partial=True, context={'request': request})
                
                if serializer.is_valid():
                    serializer.save()
                    return Response({
                        "message": "Driver profile updated successfully",
                        "data": serializer.data
                    }, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except DriverProfile.DoesNotExist:
                return Response({"error": "Driver profile not found"}, status=status.HTTP_404_NOT_FOUND)