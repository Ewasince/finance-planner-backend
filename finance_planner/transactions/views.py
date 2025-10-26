from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets

from .models import Transaction
from .serializers import TransactionCreateSerializer, TransactionSerializer


class TransactionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["type", "confirmed", "date"]
    search_fields = ["description", "amount"]
    ordering_fields = ["date", "amount", "created_at"]
    ordering = ["-date"]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return TransactionCreateSerializer
        return TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(
            user=self.request.user.id,  # type: ignore[union-attr] # TODO: fix types
        ).select_related(
            "from_account",
            "to_account",
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
