from __future__ import annotations

from regular_operations.models import RegularOperation
from rest_framework import serializers
from scenarios.models import RuleType, Scenario, ScenarioRule


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

    class Meta:
        model = Scenario
        fields = [
            "id",
            "operation",
            "title",
            "description",
            "is_active",
            "rules",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "operation", "rules", "created_at", "updated_at"]


class ScenarioCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scenario
        fields = ["title", "operation", "description", "is_active"]

    def create(self, validated_data):
        validated_data['user_id'] = self.context['request'].user.id
        return validated_data
