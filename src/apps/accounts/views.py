from django.db.models import Q
from rest_framework import status, views, generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import SignUpSerializer, LoginSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class SignUpView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignUpSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        # Flatten array errors into single strings
        errors = {
            key: value[0] if isinstance(value, list) and len(value) > 0 else str(value)
            for key, value in serializer.errors.items()
        }
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

