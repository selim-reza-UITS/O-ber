from rest_framework import status, views, generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import SignUpSerializer, LoginSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class SignUpView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = SignUpSerializer
    permission_classes = [AllowAny]

class LoginView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )

        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': {
                    'user_id': user.user_id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'is_driver': user.is_driver
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            })
        return Response({'error': 'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    
