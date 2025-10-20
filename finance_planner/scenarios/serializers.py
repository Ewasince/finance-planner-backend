from rest_framework import serializers

from .models import PaymentScenario, ScenarioRule


class ScenarioRuleSerializer(serializers.ModelSerializer):
    target_account_name = serializers.CharField(source="target_account.name", read_only=True)
    scenario_id = serializers.UUIDField()

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
        read_only_fields = ["id", "target_account_name", "type"]


class PaymentScenarioSerializer(serializers.ModelSerializer):
    rules = ScenarioRuleSerializer(many=True, read_only=True)

    class Meta:
        model = PaymentScenario
        fields = [
            "id",
            "user",
            "title",
            "description",
            "is_active",
            "rules",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class PaymentScenarioCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentScenario
        fields = ["title", "description", "is_active"]
