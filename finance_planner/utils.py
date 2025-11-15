from typing import Any

from transactions.serializers import TransactionCreateSerializer


def _get_result_field(field: str, serializer: TransactionCreateSerializer) -> Any | None:
    if serializer.instance and hasattr(serializer.instance, field):
        return getattr(serializer.instance, field)
    return serializer.validated_data.get(field)
