from django.conf import settings
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import AuthResponse


def create_auth_response(request: Request, refresh: RefreshToken) -> Response:
    """Создает Response с установленными JWT токенами в cookies и CSRF токеном."""
    response = Response(
        AuthResponse(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        ).data,
        status=status.HTTP_200_OK,
    )

    # Устанавливаем cookies
    response.set_cookie(
        key=settings.SIMPLE_JWT["AUTH_COOKIE"],
        value=str(refresh.access_token),
        expires=settings.SIMPLE_JWT["AUTH_COOKIE_ACCESS_MAX_AGE"],
        secure=True,  # Обязательно True для HTTPS
        httponly=True,  # Для безопасности
        samesite="None",  # Должно быть 'None' для кросс-доменных запросов
        path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
        domain=".fin-secret.ru",
    )

    response.set_cookie(
        key=settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH"],
        value=str(refresh),
        expires=settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH_MAX_AGE"],
        secure=True,  # Обязательно True для HTTPS
        httponly=True,  # Для безопасности
        samesite="None",  # Должно быть 'None' для кросс-доменных запросов
        path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
        domain=".fin-secret.ru",
    )

    response.set_cookie(
        key="user_id",
        value=str(refresh["user_id"]),
        secure=True,  # Обязательно True для HTTPS
        httponly=True,  # Для безопасности
        samesite="None",  # Должно быть 'None' для кросс-доменных запросов
        max_age=settings.SIMPLE_JWT["AUTH_COOKIE_ACCESS_MAX_AGE"],
        path="/",
        domain=".fin-secret.ru",
    )

    response.set_cookie(
        key="role",
        value="client",
        secure=True,  # Обязательно True для HTTPS
        httponly=True,  # Для безопасности
        samesite="None",  # Должно быть 'None' для кросс-доменных запросов
        max_age=settings.SIMPLE_JWT["AUTH_COOKIE_ACCESS_MAX_AGE"],
        path="/",
        domain=".fin-secret.ru",
    )

    # Устанавливаем CSRF token
    response.set_cookie(
        key="csrftoken",
        value=get_token(request),
        httponly=False,  # Frontend должен читать CSRF token
        samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
        secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
    )

    return response
