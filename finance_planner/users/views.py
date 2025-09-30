from rest_framework import permissions, mixins

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from users.models import User
from users.serializers import (
    UserSerializer,
)


class UserViewSet(
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        return UserSerializer

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id, is_active=True)

    @action(detail=False, methods=['get'])
    def me(self, request):
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data)
