from auth.permissions import ServiceTokenPermission
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from .models import User
from .serializers import UserSerializer, UserServiceSerializer


class UserViewSet(
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self) -> type[UserSerializer]:
        return UserSerializer

    def get_queryset(self) -> QuerySet[User]:
        return User.objects.filter(
            id=self.request.user.id,  # type: ignore[union-attr] # TODO: fix types
            is_active=True,
        )

    @action(detail=False, methods=["get"])
    def me(self, request: Request) -> Response:
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data)


class ServiceUserView(APIView):
    permission_classes = [ServiceTokenPermission]

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        serializer = UserServiceSerializer(user)
        return Response(serializer.data)
