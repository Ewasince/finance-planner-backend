from rest_framework import permissions, viewsets

from .models import Account
from .serializers import AccountCreateSerializer, AccountSerializer


class AccountViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self) -> type[AccountSerializer] | type[AccountCreateSerializer]:
        if self.action in ["create", "update", "partial_update"]:
            return AccountCreateSerializer
        return AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(
            user=self.request.user.id,  # type: ignore[union-attr] # TODO: fix types
        ).order_by(
            "-created_at",
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
