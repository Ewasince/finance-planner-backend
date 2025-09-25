from django.conf import settings
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.response import Response

from auth.serializers import AuthResponse


def create_auth_response(request, refresh) -> Response:
    response = Response(
        AuthResponse({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }).data,
        status=status.HTTP_200_OK,
    )

    # Устанавливаем cookies
    response.set_cookie(
        key=settings.SIMPLE_JWT['AUTH_COOKIE'],
        value=str(refresh.access_token),
        expires=settings.SIMPLE_JWT['AUTH_COOKIE_ACCESS_MAX_AGE'],
        secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
        samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
        path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
    )

    response.set_cookie(
        key=settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'],
        value=str(refresh),
        expires=settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH_MAX_AGE'],
        secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
        samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
        path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
    )

    # Устанавливаем CSRF token
    response.set_cookie(
        key='csrftoken',
        value=get_token(request),
        httponly=False,  # Frontend должен читать CSRF token
        samesite='Lax'
    )

    return response
