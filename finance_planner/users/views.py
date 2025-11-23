from auth.permissions import ServiceTokenPermission
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from users.models import User
from users.serializers import (
    ChangePasswordSerializer,
    UserSerializer,
    UserServiceSerializer,
)


class UserViewSet(
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self) -> type[UserSerializer | ChangePasswordSerializer]:
        if self.action == "change_password":
            return ChangePasswordSerializer
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

    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user: User = request.user  # type: ignore[assignment]
        new_password = serializer.validated_data["new_password"]

        user.set_password(new_password)
        user.save()

        return Response(
            {"detail": "Пароль успешно изменён"},
            status=status.HTTP_200_OK,
        )


class ServiceUserView(APIView):
    permission_classes = [ServiceTokenPermission]

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        serializer = UserServiceSerializer(user)
        return Response(serializer.data)
