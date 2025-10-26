from django.db.models import QuerySet
from rest_framework import mixins, permissions
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from .models import User
from .serializers import UserSerializer


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
