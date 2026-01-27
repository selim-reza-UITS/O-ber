from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
from ..models import DriverProfile, VehicleImage
from ..serializers_driver import DriverProfileSerializer
import requests
import os

def verify_image_ai(selfie_file, document_file):
    """
    Sends images to the FastAPI service for identity verification.
    """
    print("django called me!!!")
    url = os.getenv("KYC_SERVICE_URL", "http://kyc_service:8000/verify-identity/")
    
    try:
        selfie_file.seek(0)
        document_file.seek(0)
        files = {
            'id_card': document_file,
            'selfie': selfie_file
        }
        
        response = requests.post(url, files=files, timeout=90)
        
        if response.status_code == 200:
            result = response.json()
            return result.get("is_match", False)
        return False
    except Exception as e:
        print(f"AI Verification Error: {e}")
        return False
    
class DriverOnboardingView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        user = request.user

        if DriverProfile.objects.filter(user=user, ai_verified=True, admin_verified=True).exists():
            return Response({"error": "Driver profile is already fully active."}, status=status.HTTP_400_BAD_REQUEST)
        
        if DriverProfile.objects.filter(user=user, ai_verified=True).exists():
            return Response({"error": "Profile already submitted. Please wait for admin approval."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = DriverProfileSerializer(data=request.data)
        
        if serializer.is_valid():
            with transaction.atomic():
                DriverProfile.objects.filter(user=user, ai_verified=False).delete()
                
                driver_profile = serializer.save(user=user)
                
                images = request.FILES.getlist('vehicle_images')
                for img in images:
                    VehicleImage.objects.create(driver=driver_profile, image=img)
                            
            return Response({
                "message": "Step 1 complete: Profile details saved. Now upload a selfie for AI verification.",
                "next_step": "verify-selfie"
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
            return Response({"error": "Please complete onboarding form first."}, status=status.HTTP_400_BAD_REQUEST)

        if not selfie:
            return Response({"error": "Selfie image is required."}, status=status.HTTP_400_BAD_REQUEST)

        is_verified = verify_image_ai(selfie, profile.nid_front.file)

        if is_verified:
            profile.ai_verified = True
            profile.save()
            
            # Optional: Notify Admin here via Signal or Email
            
            return Response({
                "status": "success",
                "message": "AI Verification successful! Your profile is now under final review by our team."
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": "failed",
                "error": "Face verification failed. Please ensure your selfie matches your NID and try again."
            }, status=status.HTTP_400_BAD_REQUEST)