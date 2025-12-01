from auth.utils import create_auth_response
from django.conf import settings
import jwt
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from users.models import User


class JWTCookieAuthentication(authentication.BaseAuthentication):
    @staticmethod
    def _refresh_token(request: Request) -> tuple[User, RefreshToken] | None:
        """Обновляет access токен используя refresh токен из куки."""
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH"])
        if refresh_token is None:
            return None

        validated_token = RefreshToken(refresh_token)  # type: ignore[arg-type] # TODO: fix types
        user_id = validated_token["user_id"]
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

        create_auth_response(request=request, refresh=validated_token)
        return user, validated_token

    def authenticate(self, request: Request):
        """Аутентификация пользователя по JWT токену из куки или заголовка Authorization."""
        access_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE"])
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH"])

        is_can_refresh = bool(refresh_token)

        if not access_token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                access_token = auth_header.split(" ")[1]
                is_can_refresh = False

        if not access_token:
            if is_can_refresh:
                return self._refresh_token(request=request)
            raise AuthenticationFailed("No access token provided")

        try:
            # Валидируем токен
            validated_token = AccessToken(access_token)  # type: ignore[arg-type] # TODO: fix types
            user_id = validated_token["user_id"]
            user = User.objects.get(id=user_id)
            return user, validated_token
        except jwt.ExpiredSignatureError as e:
            raise AuthenticationFailed("Token has expired") from e
        except jwt.InvalidTokenError as e:
            raise AuthenticationFailed("Invalid token") from e
        except User.DoesNotExist as e:
            raise AuthenticationFailed("User not found") from e
