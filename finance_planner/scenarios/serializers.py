from __future__ import annotations

import uuid

from django.http import Http404
from rest_framework import serializers

from accounts.models import Account
from regular_operations.models import RegularOperation
from scenarios.models import PaymentScenario, RuleType, ScenarioRule


class ScenarioRuleSerializer(serializers.ModelSerializer):
    scenario_id = serializers.PrimaryKeyRelatedField(
        source="scenario",
        queryset=PaymentScenario.objects.all(),
    )
    target_account_id = serializers.PrimaryKeyRelatedField(
        source="target_account",
        queryset=Account.objects.all(),
    )
    target_account_name = serializers.CharField(source="target_account.name", read_only=True)

    class Meta:
        model = ScenarioRule
        fields = [
            "id",
            "scenario_id",
            "target_account_id",
            "target_account_name",
            "type",
            "amount",
            "order",
        ]


class ScenarioRuleCreateUpdateSerializer(serializers.ModelSerializer):
    scenario_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = ScenarioRule
        fields = ["id", "scenario_id", "target_account", "type", "amount", "order"]
        read_only_fields = ["id"]
        extra_kwargs = {
            "type": {"default": RuleType.FIXED},
        }

    def validate_target_account(self, account):
        request = self.context.get("request")
        if not request:
            return account
        if not hasattr(request, "user"):
            return account
        if not request.user.is_authenticated:
            return account
        if account.user_id != request.user.id:
            raise serializers.ValidationError(
                "Счет должен принадлежать текущему пользователю",
            )
        return account

    def _get_scenario(self, scenario_id: uuid.UUID | None) -> PaymentScenario:
        request = self.context.get("request")
        if not request or not getattr(request, "user", None):
            raise serializers.ValidationError({"scenario_id": "Не удалось определить пользователя"})
        if scenario_id is None:
            if self.instance is not None:
                return self.instance.scenario
            raise serializers.ValidationError({"scenario_id": "Укажите сценарий"})
        try:
            scenario = PaymentScenario.objects.get(id=scenario_id, user=request.user)
        except PaymentScenario.DoesNotExist as exc:  # pragma: no cover - defensive
            raise Http404("Сценарий не найден") from exc
        return scenario

    def validate(self, attrs):
        scenario_id = attrs.pop("scenario_id", None)
        attrs["scenario"] = self._get_scenario(scenario_id)
        return super().validate(attrs)

class PaymentScenarioSerializer(serializers.ModelSerializer):
    rules = ScenarioRuleSerializer(many=True, read_only=True)
    operation_id = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()

    class Meta:
        model = PaymentScenario
        fields = [
            "id",
            "user_id",
            "operation_id",
            "title",
            "description",
            "is_active",
            "rules",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_operation_id(self, obj):
        return str(obj.operation_id)

    def get_user_id(self, obj):
        return str(obj.user_id)


class PaymentScenarioCreateSerializer(serializers.ModelSerializer):
    operation_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = PaymentScenario
        fields = ["operation_id", "title", "description", "is_active"]

    def validate_operation_id(self, value):
        request = self.context.get("request")
        try:
            operation = RegularOperation.objects.get(id=value, user=request.user)
        except RegularOperation.DoesNotExist as exc:
            raise serializers.ValidationError("Регулярная операция не найдена") from exc
        if hasattr(operation, "scenario"):
            raise serializers.ValidationError("Для операции сценарий уже существует")
        self.context["operation"] = operation
        return value

    def create(self, validated_data):
        operation = self.context.pop("operation")
        validated_data.pop("operation_id", None)
        return PaymentScenario.objects.create(
            user=self.context["request"].user,
            operation=operation,
            **validated_data,
        )


class PaymentScenarioUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentScenario
        fields = ["title", "description", "is_active"]
