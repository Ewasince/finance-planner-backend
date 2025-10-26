from rest_framework import serializers
from scenarios.models import PaymentScenario, RuleType, ScenarioRule


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


class ScenarioRuleCreateSerializer(serializers.ModelSerializer):
    scenario_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = ScenarioRule
        fields = ["id", "scenario_id", "target_account", "type", "amount", "order"]
        read_only_fields = ["id", "scenario_id"]
        extra_kwargs = {
            "type": {"default": RuleType.FIXED},
        }

    def validate_target_account(self, account):
        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_authenticated:
            if account.user_id != request.user.id:
                raise serializers.ValidationError(
                    "Счет должен принадлежать текущему пользователю",
                )
        return account

    def create(self, validated_data):
        scenario = self.context.get("scenario")
        if scenario is None:
            raise serializers.ValidationError("Не удалось определить сценарий")
        validated_data["scenario"] = scenario
        return super().create(validated_data)


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
