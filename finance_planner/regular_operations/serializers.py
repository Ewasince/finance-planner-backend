from __future__ import annotations

from typing import Any

from django.db import transaction
from rest_framework import serializers

from scenarios.models import PaymentScenario, RuleType, ScenarioRule

from regular_operations.models import RegularOperation, RegularOperationType


class RegularOperationScenarioRuleReadSerializer(serializers.ModelSerializer):
    target_account_name = serializers.CharField(source="target_account.name", read_only=True)

    class Meta:
        model = ScenarioRule
        fields = [
            "id",
            "target_account_id",
            "target_account_name",
            "type",
            "amount",
            "order",
        ]
        read_only_fields = fields


class RegularOperationScenarioRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScenarioRule
        fields = ["id", "target_account", "type", "amount", "order"]
        read_only_fields = ["id"]
        extra_kwargs = {
            "type": {"default": RuleType.FIXED},
        }


class RegularOperationScenarioMetaSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)


class RegularOperationScenarioSerializer(serializers.ModelSerializer):
    rules = RegularOperationScenarioRuleReadSerializer(many=True, read_only=True)

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
    scenario_rules = RegularOperationScenarioRuleSerializer(
        many=True, required=False, allow_empty=True, write_only=True
    )
    scenario = RegularOperationScenarioMetaSerializer(required=False, write_only=True)

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
            "scenario",
            "scenario_rules",
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        instance = self.instance
        operation_type = attrs.get("type") or (instance.type if instance else None)
        from_account = self._get_field_value("from_account", attrs)
        to_account = self._get_field_value("to_account", attrs)
        start_date = attrs.get("start_date") or (instance.start_date if instance else None)
        end_date = attrs.get("end_date") or (instance.end_date if instance else None)
        scenario_rules = attrs.get("scenario_rules")
        scenario_meta = attrs.get("scenario", serializers.empty)

        if instance and "type" in attrs and attrs["type"] != instance.type:
            raise serializers.ValidationError({"type": "Нельзя менять тип операции"})

        request = self.context.get("request")
        user = None
        if request and hasattr(request, "user") and request.user and request.user.is_authenticated:
            user = request.user
        elif instance is not None:
            user = instance.user

        if operation_type is None:
            raise serializers.ValidationError({"type": "Тип операции обязателен"})

        if operation_type == RegularOperationType.EXPENSE:
            if from_account is None:
                raise serializers.ValidationError(
                    {"from_account": "Для расходной операции нужно указать счет списания"}
                )
            if to_account is not None:
                raise serializers.ValidationError(
                    {"to_account": "Для расходной операции не нужно указывать счет зачисления"}
                )
            if scenario_rules:
                raise serializers.ValidationError(
                    {"scenario_rules": "Правила сценария доступны только для доходных операций"}
                )
        elif operation_type == RegularOperationType.INCOME:
            if to_account is None:
                raise serializers.ValidationError(
                    {"to_account": "Для доходной операции нужно указать счет зачисления"}
                )
            if from_account is not None:
                raise serializers.ValidationError(
                    {"from_account": "Для доходной операции не нужно указывать счет списания"}
                )
        else:
            raise serializers.ValidationError({"type": "Недопустимый тип операции"})

        if start_date and end_date and end_date <= start_date:
            raise serializers.ValidationError(
                {"end_date": "Дата окончания должна быть больше или равна дате начала"}
            )

        if scenario_rules and operation_type != RegularOperationType.INCOME:
            raise serializers.ValidationError(
                {"scenario_rules": "Правила сценария доступны только для доходных операций"}
            )

        if (
            scenario_meta is not serializers.empty
            and scenario_meta is not None
            and operation_type != RegularOperationType.INCOME
        ):
            raise serializers.ValidationError(
                {"scenario": "Сценарий доступен только для доходных операций"}
            )

        if user is not None:
            if from_account is not None and from_account.user_id != user.id:
                raise serializers.ValidationError(
                    {"from_account": "Счет списания должен принадлежать текущему пользователю"}
                )
            if to_account is not None and to_account.user_id != user.id:
                raise serializers.ValidationError(
                    {"to_account": "Счет зачисления должен принадлежать текущему пользователю"}
                )
            if scenario_rules:
                for rule in scenario_rules:
                    target_account = rule.get("target_account")
                    if target_account and target_account.user_id != user.id:
                        raise serializers.ValidationError(
                            {
                                "scenario_rules": "Целевые счета сценария должны принадлежать текущему пользователю",
                            }
                        )

        return attrs

    def _get_field_value(self, field: str, attrs: dict[str, Any]):
        if field in attrs:
            return attrs[field]
        if self.instance is not None:
            return getattr(self.instance, field)
        return None

    def create(self, validated_data: dict[str, Any]) -> RegularOperation:
        scenario_rules = validated_data.pop("scenario_rules", [])
        scenario_meta = validated_data.pop("scenario", serializers.empty)
        with transaction.atomic():
            operation = RegularOperation.objects.create(**validated_data)
            self._sync_scenario(operation, scenario_rules, scenario_meta)
        return operation

    def update(self, instance: RegularOperation, validated_data: dict[str, Any]) -> RegularOperation:
        scenario_rules = validated_data.pop("scenario_rules", serializers.empty)
        scenario_meta = validated_data.pop("scenario", serializers.empty)
        with transaction.atomic():
            operation = super().update(instance, validated_data)
            self._sync_scenario(operation, scenario_rules, scenario_meta)
        return operation

    def _sync_scenario(
        self,
        operation: RegularOperation,
        scenario_rules: Any,
        scenario_meta: Any,
    ) -> None:
        scenario_meta_provided = scenario_meta is not serializers.empty
        scenario_meta_values = scenario_meta or {} if scenario_meta_provided else {}

        if operation.type == RegularOperationType.INCOME:
            scenario = getattr(operation, "scenario", None)
            if scenario is None:
                initial_values = {
                    "title": scenario_meta_values.get("title", operation.title),
                    "description": scenario_meta_values.get(
                        "description", operation.description
                    ),
                    "is_active": scenario_meta_values.get("is_active", operation.is_active),
                }
                scenario = PaymentScenario.objects.create(
                    user=operation.user,
                    operation=operation,
                    **initial_values,
                )
            else:
                if scenario_meta_provided:
                    fields_to_update: list[str] = []
                    if "title" in scenario_meta_values:
                        scenario.title = scenario_meta_values["title"]
                        fields_to_update.append("title")
                    if "description" in scenario_meta_values:
                        scenario.description = scenario_meta_values["description"]
                        fields_to_update.append("description")
                    if "is_active" in scenario_meta_values:
                        scenario.is_active = scenario_meta_values["is_active"]
                        fields_to_update.append("is_active")
                    if fields_to_update:
                        scenario.save(update_fields=fields_to_update)

            if scenario_rules is not serializers.empty:
                ScenarioRule.objects.filter(scenario=scenario).delete()
                rules_to_create = []
                for rule_data in scenario_rules:
                    rules_to_create.append(
                        ScenarioRule(
                            scenario=scenario,
                            target_account=rule_data["target_account"],
                            type=rule_data.get("type", RuleType.FIXED),
                            amount=rule_data.get("amount"),
                            order=rule_data.get("order", 0),
                        )
                    )
                if rules_to_create:
                    ScenarioRule.objects.bulk_create(rules_to_create)
        else:
            scenario = getattr(operation, "scenario", None)
            if scenario is not None:
                scenario.delete()
