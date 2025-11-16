from django.conf import settings
from rest_framework.permissions import BasePermission


class ServiceTokenPermission(BasePermission):
    def has_permission(self, request, view):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("SVCBearer "):
            return False

        token = auth_header.split(" ")[1]

        return token == settings.SERVICE_AUTH_TOKEN
