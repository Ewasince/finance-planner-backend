from typing import Any

from django.utils import timezone
from rest_framework import serializers
from transactions.models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    from_account_name = serializers.CharField(source="from_account.name", read_only=True)
    to_account_name = serializers.CharField(source="to_account.name", read_only=True)
    scenario_id = serializers.UUIDField(source="scenario_rule.scenario_id", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "user_id",
            "date",
            "type",
            "amount",
            "from_account",
            "to_account",
            "from_account_name",
            "to_account_name",
            "confirmed",
            "description",
            "created_at",
            "updated_at",
            "operation",
            "scenario_rule",
            "scenario_id",
            "planned_date",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at", "scenario_rule", "operation", "scenario_id", "planned_date"]


class TransactionCreateSerializer(serializers.ModelSerializer):
    confirmed = serializers.BooleanField(
        default=True,
    )
    # TODO: почему то не заносится тип транзакции, потом пофиксим. Пока — вручную указываем
    # type = serializers.SerializerMethodField()
    #
    # def get_type(self, obj) -> str | None:
    #     if obj.from_account and obj.to_account:
    #         return TransactionType.TRANSFER
    #     elif obj.from_account and not obj.to_account:
    #         return TransactionType.EXPENSE
    #     elif not obj.from_account and obj.to_account:
    #         return TransactionType.INCOME
    #
    #     return None

    class Meta:
        model = Transaction
        fields = [
            "id",
            "date",
            "type",
            "amount",
            "from_account",
            "to_account",
            "confirmed",
            "description",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if (
            self._get_field_value("confirmed", attrs)
            and self._get_field_value("date", attrs) > timezone.now().date()
        ):
            raise serializers.ValidationError(
                {"date": "Нельзя создавать фактические транзакции в будущем"}
            )
        if not self._get_field_value("to_account", attrs) and not self._get_field_value(
            "from_account", attrs
        ):
            raise serializers.ValidationError(
                {"account": "Транзакция должна взаимодействовать со счётом"}
            )
        return attrs

    def _get_field_value(self, field: str, attrs: dict[str, Any]):
        if field in attrs:
            return attrs[field]
        if self.instance is not None:
            return getattr(self.instance, field)
        return None


class TransactionUpdateSerializer(TransactionCreateSerializer):
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs.get("confirmed") is not None and self.instance.confirmed != attrs["confirmed"]:
            raise serializers.ValidationError(
                {"date": "Нельзя делать фактическими транзакции запланированными"}
            )
        return super().validate(attrs)


class CalculateResponse(serializers.Serializer):
    transactions_created = serializers.IntegerField()
