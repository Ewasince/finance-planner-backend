from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    # Получаем стандартный response
    response = exception_handler(exc, context)

    # Если исключение AuthenticationFailed и статус 403, меняем на 401
    if (
        response is not None
        and isinstance(exc, AuthenticationFailed)
        and response.status_code == status.HTTP_403_FORBIDDEN
    ):
        response.status_code = status.HTTP_401_UNAUTHORIZED

    return response
