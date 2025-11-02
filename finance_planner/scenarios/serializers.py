from __future__ import annotations
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
    scenario_id = serializers.PrimaryKeyRelatedField(
        source="scenario",
        queryset=PaymentScenario.objects.all(),
    )

    class Meta:
        model = ScenarioRule
        fields = ["id", "scenario_id", "target_account", "type", "amount", "order"]
        read_only_fields = ["id", "scenario_id"]
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

class PaymentScenarioSerializer(serializers.ModelSerializer):
    rules = ScenarioRuleSerializer(many=True, read_only=True)
    operation_id = serializers.UUIDField(source="operation_id", read_only=True)

    class Meta:
        model = PaymentScenario
        fields = [
            "id",
            "operation_id",
            "title",
            "description",
            "is_active",
            "rules",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "operation_id", "created_at", "updated_at"]

class PaymentScenarioCreateSerializer(serializers.ModelSerializer):
    operation_id = serializers.PrimaryKeyRelatedField(
        source="operation",
        queryset=RegularOperation.objects.all(),
        write_only=True,
    )

    class Meta:
        model = PaymentScenario
        fields = ["title", "description", "is_active"]
