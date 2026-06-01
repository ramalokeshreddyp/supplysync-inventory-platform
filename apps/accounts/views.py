from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.serializers import RegisterSerializer, LoginSerializer, ChangePasswordSerializer
from core.throttles import LoginRateLimitThrottle

class RegisterView(APIView):
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    permission_classes = []
    throttle_classes = [LoginRateLimitThrottle]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        throttle = LoginRateLimitThrottle()
        ip_address = throttle.get_ident(request)
        
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            
            # Update last_login_at
            user.last_login_at = timezone.now()
            user.save(update_fields=['last_login_at'])
            
            # Clear failed login attempts in cache
            LoginRateLimitThrottle.clear_failed_attempts(ip_address)
            
            refresh = RefreshToken.for_user(user)
            return Response({
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "user_id": user.id,
                "username": user.username,
                "role": user.role
            }, status=status.HTTP_200_OK)
        except Exception as e:
            LoginRateLimitThrottle.increment_failed_attempts(ip_address)
            raise e

class LogoutView(APIView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            raise ValidationError({"refresh_token": ["This field is required."]})
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)
        except Exception:
            raise ValidationError({"refresh_token": ["Invalid, blacklisted, or expired token."]})

class ChangePasswordView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({"message": "Password updated successfully."}, status=status.HTTP_200_OK)
