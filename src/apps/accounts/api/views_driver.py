from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
from ..models import DriverProfile, VehicleImage
from ..serializers_driver import DriverProfileSerializer
import requests
import os
import logging

logger = logging.getLogger(__name__)


class DriverOnboardingView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def _log_and_response(self, data, status_code):
        logger.info(f"Response ({status_code}): {data}")
        return Response(data, status=status_code)

    def post(self, request):
        logger.info(f"--- DriverOnboardingView POST Called by user {request.user} ---")
        logger.info(f"Headers: {request.headers}")
        logger.info(f"Request Data: {request.data}")
        logger.info(f"Request FILES: {request.FILES}")

        user = request.user

        if DriverProfile.objects.filter(user=user, admin_verified=True).exists():
            logger.warning("User already has an active driver profile.")
            return self._log_and_response({"error": "Driver profile is already fully active."}, status.HTTP_400_BAD_REQUEST)
        
        if DriverProfile.objects.filter(user=user, admin_verified=False).exists():
            logger.warning("User already submitted a profile, awaiting review.")
            return self._log_and_response({"error": "Profile already submitted. Please wait for our Admin team to review and activate your account."}, status.HTTP_400_BAD_REQUEST)

        serializer = DriverProfileSerializer(data=request.data)
        
        if serializer.is_valid():
            logger.info("Serializer is valid. Attempting to save profile.")
            try:
                with transaction.atomic():
                    DriverProfile.objects.filter(user=user).delete()
                    
                    # Automatically bypass ai_verified flag since AI KYC is removed
                    driver_profile = serializer.save(user=user, ai_verified=True)
                    logger.info(f"Driver profile created: {driver_profile.id}")
                    
                    images = request.FILES.getlist('vehicle_images')
                    logger.info(f"Found {len(images)} vehicle images in request.")
                    for img in images:
                        VehicleImage.objects.create(driver=driver_profile, image=img)
                                
                logger.info("Profile submitted successfully.")
                return self._log_and_response({
                    "message": "Profile submitted successfully! Please wait for our Admin team to review and activate your account."
                }, status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Error during transaction saving driver profile: {str(e)}", exc_info=True)
                return self._log_and_response({"error": "An internal error occurred while saving the profile."}, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Convert serializer errors into a single string message
        error_messages = []
        for field, errors in serializer.errors.items():
            for error in errors:
                if isinstance(error, str):
                    error_messages.append(f"{field}: {error}")
                else:
                    error_messages.append(f"{field}: {str(error)}")
        
        error_string = " | ".join(error_messages)
        
        logger.error(f"Validation failed. Serializer errors: {error_string}")
        return self._log_and_response({"error": error_string}, status.HTTP_400_BAD_REQUEST)

