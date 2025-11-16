from typing import Any

from transactions.serializers import TransactionCreateSerializer


def get_result_field(field: str, serializer: TransactionCreateSerializer) -> Any | None:
    if serializer.instance and hasattr(serializer.instance, field):
        return getattr(serializer.instance, field)
    return serializer.validated_data.get(field)


def field_updated(field: str, serializer: TransactionCreateSerializer) -> Any | None:
    return field in serializer.validated_data
