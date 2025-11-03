from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django_filters.rest_framework import DjangoFilterBackend
from regular_operations.models import RegularOperation, RegularOperationType
from regular_operations.serializers import (
    RegularOperationCreateSerializer,
    RegularOperationSerializer,
    RegularOperationUpdateSerializer,
)
from rest_framework import filters, permissions, status, viewsets
from rest_framework.response import Response
from scenarios.models import Scenario


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
        if self.action in ["create"]:
            return RegularOperationCreateSerializer
        if self.action in ["update", "partial_update"]:
            return RegularOperationUpdateSerializer
        return RegularOperationSerializer

    def get_queryset(self):
        return (
            RegularOperation.objects.filter(user=self.request.user)
            .select_related("from_account", "to_account")
            .prefetch_related("scenario__rules", "scenario__rules__target_account")
        )

    def perform_create(self, serializer):
        operation_type = serializer.validated_data.get("type")
        if operation_type == RegularOperationType.EXPENSE:
            serializer.save(user=self.request.user)
            return

        try:
            with transaction.atomic():
                operation = serializer.save(user=self.request.user)

                Scenario.objects.create(
                    user=self.request.user,
                    operation=operation,
                    title=f"Сценарий для {operation.title}",
                    description="Создан автоматически",
                    is_active=True,
                )
        except IntegrityError as e:
            raise ValidationError({"detail": "Связанный сценарий уже существует."}) from e

    def create(self, request, *args, **kwargs):
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        self.perform_create(write_serializer)

        operation = write_serializer.instance  # уже сохранённая операция
        read_serializer = RegularOperationSerializer(
            operation, context=self.get_serializer_context()
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)
