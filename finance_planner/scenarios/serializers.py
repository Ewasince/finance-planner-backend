from rest_framework import serializers

from scenarios.models import PaymentScenario, ScenarioRule


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
    operation_id = serializers.UUIDField(source="operation_id", read_only=True)

    class Meta:
        model = PaymentScenario
        fields = [
            "id",
            "user",
            "operation_id",
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
        fields = ["operation", "title", "description", "is_active"]
        read_only_fields = ["operation"]
