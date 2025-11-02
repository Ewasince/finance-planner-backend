from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class ObjectOwner(BasePermission):
    def has_object_permission(self, request: Request, view: APIView, obj: Any):
        return request.user == obj.user
