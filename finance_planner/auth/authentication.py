from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
import jwt
from django.conf import settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from auth.utils import create_auth_response
from users.models import User


class JWTCookieAuthentication(authentication.BaseAuthentication):

    @staticmethod
    def _refresh_token(request):
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'])
        validated_token = RefreshToken(refresh_token)
        user_id = validated_token['user_id']
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

        create_auth_response(request=request, refresh=validated_token)
        return user, validated_token

    def authenticate(self, request):
        access_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE'])
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'])

        is_can_refresh = bool(refresh_token)

        if not access_token:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]
                is_can_refresh = False

        if not access_token:
            if is_can_refresh:
                return self._refresh_token(request=request)
            return None

        try:
            # Валидируем токен
            validated_token = AccessToken(access_token)
            user_id = validated_token['user_id']
            user = User.objects.get(id=user_id)
            return user, validated_token
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found')
