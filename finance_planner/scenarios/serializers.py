from __future__ import annotations

from accounts.models import Account
from regular_operations.models import RegularOperation
from rest_framework import serializers, status
from scenarios.models import Scenario, RuleType, ScenarioRule


class ScenarioRuleSerializer(serializers.ModelSerializer):
    target_account_name = serializers.CharField(source="target_account.name", read_only=True)

    class Meta:
        model = ScenarioRule
        fields = [
            "id",
            "scenario",
            "target_account",
            "target_account_name",
            "type",
            "amount",
            "order",
        ]


class ScenarioRuleCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScenarioRule
        fields = ["id", "scenario", "target_account", "type", "amount", "order"]
        read_only_fields = ["id"]
        extra_kwargs = {
            "type": {"default": RuleType.FIXED},
        }

    def validate_target_account(self, account):
        request = self.context.get("request")
        if account.user_id != request.user.id:
            raise serializers.ValidationError(
                "Счет должен принадлежать текущему пользователю",
            )
        return account

    def validate_scenario(self, scenario):
        request = self.context.get("request")
        if scenario.user_id != request.user.id:
            raise serializers.ValidationError(
                "Счет должен принадлежать текущему пользователю",
            )
        return scenario


class ScenarioSerializer(serializers.ModelSerializer):
    rules = ScenarioRuleSerializer(many=True, read_only=True)
    operation_id = serializers.UUIDField(source="operation_id", read_only=True)

    class Meta:
        model = Scenario
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


class ScenarioCreateSerializer(serializers.ModelSerializer):
    operation_id = serializers.PrimaryKeyRelatedField(
        source="operation",
        queryset=RegularOperation.objects.all(),
        write_only=True,
    )

    class Meta:
        model = Scenario
        fields = ["title", "description", "is_active"]


class ScenarioUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scenario
        fields = ["title", "description", "is_active"]
