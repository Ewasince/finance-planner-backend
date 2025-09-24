from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
import jwt
from django.conf import settings
from rest_framework_simplejwt.tokens import AccessToken

from users.models import User


class JWTCookieAuthentication(authentication.BaseAuthentication):

    def authenticate(self, request):
        access_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE'])

        if not access_token:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]

        if not access_token:
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
