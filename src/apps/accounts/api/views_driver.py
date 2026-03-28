from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
from ..models import DriverProfile, VehicleImage
from ..serializers_driver import DriverProfileSerializer
import requests
import os

class DriverOnboardingView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        user = request.user

        if DriverProfile.objects.filter(user=user, admin_verified=True).exists():
            return Response({"error": "Driver profile is already fully active."}, status=status.HTTP_400_BAD_REQUEST)
        
        if DriverProfile.objects.filter(user=user, admin_verified=False).exists():
            return Response({"error": "Profile already submitted. Please wait for our Admin team to review and activate your account."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = DriverProfileSerializer(data=request.data)
        
        if serializer.is_valid():
            with transaction.atomic():
                DriverProfile.objects.filter(user=user).delete()
                
                # Automatically bypass ai_verified flag since AI KYC is removed
                driver_profile = serializer.save(user=user, ai_verified=True)
                
                images = request.FILES.getlist('vehicle_images')
                for img in images:
                    VehicleImage.objects.create(driver=driver_profile, image=img)
                            
            return Response({
                "message": "Profile submitted successfully! Please wait for our Admin team to review and activate your account."
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
