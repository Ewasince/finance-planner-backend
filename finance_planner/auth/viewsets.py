from auth.models import MyAuthSerializer
from auth.serializers import AuthResponse
from auth.utils import create_auth_response
from django.conf import settings
from django.contrib.auth import authenticate
from django.middleware.csrf import get_token
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from users.serializers import UserRegistrationSerializer


@swagger_auto_schema(
    request_body=MyAuthSerializer(),
    methods=[
        "post",
    ],
    responses={200: AuthResponse, 400: "Ошибка"},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request: Request):  # type: ignore[no-untyped-def]
    """Аутентифицирует пользователя и возвращает JWT токены в cookies."""
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(username=username, password=password)

    if user is None:
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

    refresh = RefreshToken.for_user(user)

    return create_auth_response(request=request, refresh=refresh)


@swagger_auto_schema(
    request_body=UserRegistrationSerializer(),
    methods=[
        "post",
    ],
    responses={201: AuthResponse(), 400: "Ошибка"},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def sign_up_view(request):
    """Регистрирует нового пользователя и возвращает JWT токены в cookies."""
    serializer = UserRegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return create_auth_response(request=request, refresh=RefreshToken.for_user(user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Удаляет JWT токены из cookies."""
    response = Response({"message": "Logout successful"}, status=status.HTTP_200_OK)

    # Удаляем cookies
    response.delete_cookie(settings.SIMPLE_JWT["AUTH_COOKIE"], samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"])
    response.delete_cookie(settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH"], samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"])
    response.delete_cookie("csrftoken", samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"])

    return response


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_token_view(request):
    """Обновляет access токен используя refresh токен из куки."""
    refresh_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH"])

    if not refresh_token:
        return Response({"error": "Refresh token not found"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        refresh = RefreshToken(refresh_token)
        new_access_token = str(refresh.access_token)

        response = Response({"message": "Token refreshed successfully"}, status=status.HTTP_200_OK)

        # Обновляем access token cookie
        response.set_cookie(
            key=settings.SIMPLE_JWT["AUTH_COOKIE"],
            value=new_access_token,
            expires=settings.SIMPLE_JWT["AUTH_COOKIE_ACCESS_MAX_AGE"],
            secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
            httponly=settings.SIMPLE_JWT["AUTH_COOKIE_HTTP_ONLY"],
            samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
            path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
        )

        return response

    except Exception:
        return Response({"error": "Invalid refresh token"}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_profile_view(request):
    """Возвращает информацию о текущем аутентифицированном пользователе."""
    user = request.user
    return Response({"user": {"id": user.id, "username": user.username, "email": user.email}})


@api_view(["GET"])
@permission_classes([AllowAny])
def get_csrf_token(request):
    """Возвращает CSRF токен в cookie."""
    response = Response({"message": "CSRF token set"})
    response.set_cookie(key="csrftoken", value=get_token(request), httponly=False, samesite="Lax")
    return response
