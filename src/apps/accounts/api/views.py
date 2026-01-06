from rest_framework import status, views, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from ..serializers import SignUpSerializer, PasswordResetSerializer,VerifyOTPSerializer
from django.contrib.auth import get_user_model
from ..services import OTPService
from django.db import transaction
from src.apps.accounts.models import RiderProfile

User = get_user_model()


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class SignUpView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SignUpSerializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    email=serializer.validated_data['email'],
                    phone_number=serializer.validated_data['phone_number'],
                    full_name=serializer.validated_data['full_name'],
                    password=serializer.validated_data['password']
                )
                RiderProfile.objects.create(user=user)
                
            tokens = get_tokens_for_user(user)
            
            # Logic for initials (Selim Reza -> SR)
            names = user.full_name.split()
            initials = "".join([n[0].upper() for n in names[:2]])

            return Response({
                "message": "User created successfully",
                "user": {
                    "id": user.user_id,
                    "initials": initials,
                    "is_rider": user.is_rider
                },
                "tokens": tokens
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username') # Flutter sends Email OR Phone
        password = request.data.get('password')

        user = authenticate(username=username, password=password)
        
        if user:
            return Response({
                "user": {"id": user.user_id, "full_name": user.full_name},
                "tokens": get_tokens_for_user(user)
            })
        return Response({"error": "Invalid email/phone or password"}, status=status.HTTP_401_UNAUTHORIZED)

class ForgotPasswordRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if User.objects.filter(email=email).exists():
            otp = OTPService.generate_otp(email)
            OTPService.send_otp_email(email, otp)
            return Response({"message": "OTP sent to your email."})
        return Response({"error": "User with this email not found."}, status=status.HTTP_404_NOT_FOUND)

class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            
            # Use your OTPService to check Redis
            if OTPService.verify_otp(email, otp):
                return Response({"message": "OTP verified successfully."}, status=status.HTTP_200_OK)
            
            return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            
            if OTPService.verify_otp(email, otp):
                user = User.objects.get(email=email)
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                return Response({"message": "Password updated successfully."})
            
            return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)