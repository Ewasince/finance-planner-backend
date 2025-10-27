from __future__ import annotations

from typing import Any

from rest_framework import serializers

from regular_operations.models import RegularOperation, RegularOperationType
from scenarios.models import PaymentScenario
from scenarios.serializers import ScenarioRuleSerializer


class RegularOperationScenarioSerializer(serializers.ModelSerializer):
    rules = ScenarioRuleSerializer(many=True, read_only=True)

    class Meta:
        model = PaymentScenario
        fields = [
            "id",
            "title",
            "description",
            "is_active",
            "created_at",
            "updated_at",
            "rules",
        ]
        read_only_fields = fields


class RegularOperationSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(read_only=True)
    from_account_name = serializers.CharField(source="from_account.name", read_only=True)
    to_account_name = serializers.CharField(source="to_account.name", read_only=True)
    scenario = RegularOperationScenarioSerializer(read_only=True)

    class Meta:
        model = RegularOperation
        fields = [
            "id",
            "user_id",
            "title",
            "description",
            "amount",
            "type",
            "from_account",
            "from_account_name",
            "to_account",
            "to_account_name",
            "start_date",
            "end_date",
            "period_type",
            "period_interval",
            "is_active",
            "scenario",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "from_account_name",
            "to_account_name",
            "scenario",
            "created_at",
            "updated_at",
        ]


class RegularOperationCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegularOperation
        fields = [
            "title",
            "description",
            "amount",
            "type",
            "from_account",
            "to_account",
            "start_date",
            "end_date",
            "period_type",
            "period_interval",
            "is_active",
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0912
        request = self.context.get('request')
        is_updating_validate = self.instance is not None
        if is_updating_validate:
            if attrs.get("type", self.instance.type) != self.instance.type:
                raise serializers.ValidationError({"type": "Нельзя менять тип операции"})

        operation_type = self._get_field_value("type", attrs)
        from_account = self._get_field_value("from_account", attrs)
        to_account = self._get_field_value("to_account", attrs)
        start_date = self._get_field_value("start_date", attrs)
        end_date = self._get_field_value("end_date", attrs)

        if operation_type is None:
            raise serializers.ValidationError({"type": "Тип операции обязателен"})

        if operation_type == RegularOperationType.EXPENSE:
            self._validate_expense(
                from_account=from_account,
                to_account=to_account,
            )
        elif operation_type == RegularOperationType.INCOME:
            self._validate_income(
                from_account=from_account,
                to_account=to_account,
            )
        else:
            raise serializers.ValidationError({"type": "Недопустимый тип операции"})

        if start_date and end_date and end_date <= start_date:
            raise serializers.ValidationError(
                {"end_date": "Дата окончания должна быть больше или равна дате начала"}
            )

        if from_account is not None and from_account.user_id != request.user.id:
            raise serializers.ValidationError(
                {"from_account": "Счет списания должен принадлежать текущему пользователю"}
            )
        if to_account is not None and to_account.user_id != request.user.id:
            raise serializers.ValidationError(
                {"to_account": "Счет зачисления должен принадлежать текущему пользователю"}
            )

        return attrs

    def _validate_income(self, *, from_account: Any | None, to_account: Any | None) -> None:
        if to_account is None:
            raise serializers.ValidationError(
                {"to_account": "Для доходной операции нужно указать счет зачисления"}
            )
        if from_account is not None:
            raise serializers.ValidationError(
                {"from_account": "Для доходной операции не нужно указывать счет списания"}
            )

    def _validate_expense(
            self,
            *,
            from_account: Any | None,
            to_account: Any | None,
    ) -> None:
        if from_account is None:
            raise serializers.ValidationError(
                {"from_account": "Для расходной операции нужно указать счет списания"}
            )
        if to_account is not None:
            raise serializers.ValidationError(
                {"to_account": "Для расходной операции не нужно указывать счет зачисления"}
            )

    def _get_field_value(self, field: str, attrs: dict[str, Any]):
        if field in attrs:
            return attrs[field]
        if self.instance is not None:
            return getattr(self.instance, field)
        return None

    def create(self, validated_data: dict[str, Any]) -> RegularOperation:
        return RegularOperation.objects.create(**validated_data)

    def update(
            self, instance: RegularOperation, validated_data: dict[str, Any]
    ) -> RegularOperation:
        return super().update(instance, validated_data)
