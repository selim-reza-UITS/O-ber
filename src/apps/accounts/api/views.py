from rest_framework import status, views, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from ..serializers import SignUpSerializer, PasswordResetSerializer,VerifyOTPSerializer,LoginSerializer
from django.contrib.auth import get_user_model
from ..services import OTPService
from django.db import transaction
from django.db.models import Q
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

class LoginView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        # 1. If validation fails, return 400 immediately
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        login_id = serializer.validated_data['login_id']
        password = serializer.validated_data['password']

        # 2. Search for the user (using iexact for email to ignore case)
        user = User.objects.filter(
            Q(email__iexact=login_id) | Q(phone_number=login_id)
        ).first()

        # Debugging: See what was found in the terminal
        print(f"DEBUG: Attempting login for ID: {login_id}")
        print(f"DEBUG: User found: {user}")

        # 3. Check if user exists
        if not user:
            return Response({"error": "No account found with this email/phone."}, status=status.HTTP_401_UNAUTHORIZED)

        # 4. Check password
        if not user.check_password(password):
            print(f"DEBUG: Password check failed for {user.email}")
            return Response({"error": "Invalid password."}, status=status.HTTP_401_UNAUTHORIZED)

        # 5. Check if active
        if not user.is_active:
            return Response({"error": "Account is disabled."}, status=status.HTTP_403_FORBIDDEN)

        # 6. Success - Generate Tokens
        try:
            refresh = RefreshToken.for_user(user)
            
            # Initials logic for Flutter UI
            names = user.full_name.split()
            initials = "".join([n[0].upper() for n in names[:2]]) if names else ""

            return Response({
                "user_id": user.user_id,
                "full_name": user.full_name,
                "email": user.email,
                "phone_number": user.phone_number,
                "is_rider": user.is_rider,
                "is_driver": user.is_driver,
                "user_initials": initials,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": f"Token generation failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            
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