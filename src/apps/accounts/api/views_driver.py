from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
from ..models import DriverProfile, VehicleImage
from ..serializers_driver import DriverProfileSerializer


def verify_image_ai(selfie_image, passport_or_nid_image,driving_license_image):
    """
    Logic to compare selfie with NID/License
    Returns True or False
    """
    # Simulate AI processing
    return True

class DriverOnboardingView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        user = request.user

        if DriverProfile.objects.filter(user=user,ai_verified=True,admin_verified=True).exists():
            return Response({"error": "Driver profile already active"}, status=status.HTTP_400_BAD_REQUEST)
        
        
        if DriverProfile.objects.filter(user=user,ai_verified=True).exists():
            return Response({"error": "Driver profile already submitted."}, status=status.HTTP_400_BAD_REQUEST)


        serializer = DriverProfileSerializer(data=request.data)
        
        if serializer.is_valid():
            with transaction.atomic():
                driver_profile = serializer.save(user=user)
                
                images = request.FILES.getlist('vehicle_images')
                for img in images:
                    VehicleImage.objects.create(driver=driver_profile, image=img)
                
                user.is_driver = True
                user.save()

            return Response({
                "message": "Profile details saved. Proceed to selfie verification.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DriverSelfieVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        user = request.user
        selfie = request.FILES.get('selfie')
        
        try:
            profile = user.driver_profile
        except DriverProfile.DoesNotExist:
            return Response({"error": "Complete profile setup first."}, status=status.HTTP_400_BAD_REQUEST)

        if not selfie:
            return Response({"error": "Selfie image is required."}, status=status.HTTP_400_BAD_REQUEST)

        is_verified = verify_image_ai(selfie, profile.nid_front.path)

        if is_verified:
            profile.ai_verified = True
            profile.save()
            return Response({"message": "AI Verification successful. Pending Admin review."})
        else:
            return Response({"error": "AI Verification failed. Face does not match documents."}, status=status.HTTP_400_BAD_REQUEST)