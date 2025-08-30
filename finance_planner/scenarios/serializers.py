from rest_framework import serializers
from scenarios.models import PaymentScenario, ScenarioRule


class ScenarioRuleSerializer(serializers.ModelSerializer):
    target_account_name = serializers.CharField(source='target_account.name', read_only=True)

    class Meta:
        model = ScenarioRule
        fields = ['id', 'scenario', 'target_account', 'target_account_name', 'type',
                  'amount', 'percentage', 'order']
        read_only_fields = ['id']


class PaymentScenarioSerializer(serializers.ModelSerializer):
    rules = ScenarioRuleSerializer(many=True, read_only=True)
    source_account_name = serializers.CharField(source='source_account.name', read_only=True)

    class Meta:
        model = PaymentScenario
        fields = ['id', 'user', 'name', 'description', 'source_account', 'source_account_name',
                  'is_active', 'execution_order', 'rules', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class PaymentScenarioCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentScenario
        fields = ['name', 'description', 'source_account', 'is_active', 'execution_order']
