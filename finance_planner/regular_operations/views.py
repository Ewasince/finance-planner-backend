from django_filters.rest_framework import DjangoFilterBackend
from regular_operations.models import RegularOperation
from regular_operations.serializers import (
    RegularOperationCreateSerializer,
    RegularOperationSerializer,
    RegularOperationUpdateSerializer,
)
from rest_framework import filters, permissions, viewsets


class RegularOperationViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["type", "is_active", "period_type"]
    search_fields = ["title", "description"]
    ordering_fields = ["start_date", "amount", "created_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action in ["create", "partial_update"]:
            return RegularOperationCreateSerializer
        if self.action in ["update"]:
            return RegularOperationUpdateSerializer
        return RegularOperationSerializer

    def get_queryset(self):
        return (
            RegularOperation.objects.filter(user=self.request.user)
            .select_related("from_account", "to_account")
            .prefetch_related("scenario__rules", "scenario__rules__target_account")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
