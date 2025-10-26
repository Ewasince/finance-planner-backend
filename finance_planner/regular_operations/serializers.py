from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, TypeAlias

from django.db import transaction

from core.utils import is_provided
from regular_operations.models import RegularOperation, RegularOperationType
from rest_framework import serializers
from scenarios.models import PaymentScenario, RuleType, ScenarioRule
from scenarios.serializers import (
    ScenarioRuleCreateSerializer,
    ScenarioRuleSerializer,
)


EmptyValue: TypeAlias = type(serializers.empty) | None
ScenarioRulePayload: TypeAlias = Mapping[str, Any]
ScenarioRulesData: TypeAlias = Sequence[ScenarioRulePayload]
ScenarioMetaData: TypeAlias = Mapping[str, Any]


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



class RegularOperationScenarioMetaSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)

class RegularOperationCreateUpdateSerializer(serializers.ModelSerializer):
    scenario_rules = ScenarioRuleCreateSerializer(
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
        is_updating_validate = self.instance is not None
        user = self._get_authenticated_user()
        if is_updating_validate:
            if attrs.get("type", serializers.empty) != self.instance.type:
                raise serializers.ValidationError({"type": "Нельзя менять тип операции"})

            if user is None:
                user = self.instance.user

        operation_type = self._get_field_value("type", attrs)
        from_account = self._get_field_value("from_account", attrs)
        to_account = self._get_field_value("to_account", attrs)
        start_date = self._get_field_value("start_date", attrs)
        end_date = self._get_field_value("end_date", attrs)
        scenario_rules = attrs.get("scenario_rules")
        scenario_data = attrs.get("scenario", serializers.empty)

        if operation_type is None:
            raise serializers.ValidationError({"type": "Тип операции обязателен"})

        if operation_type == RegularOperationType.EXPENSE:
            self._validate_expense(
                from_account=from_account,
                to_account=to_account,
                scenario_rules=scenario_rules,
                scenario_data=scenario_data,
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
        scenario_rules: ScenarioRulesData | EmptyValue,
        scenario_data: ScenarioMetaData | EmptyValue,
    ) -> None:
        if from_account is None:
            raise serializers.ValidationError(
                {"from_account": "Для расходной операции нужно указать счет списания"}
            )
        if to_account is not None:
            raise serializers.ValidationError(
                {"to_account": "Для расходной операции не нужно указывать счет зачисления"}
            )
        if is_provided(scenario_rules) and len(scenario_rules) > 0:
            raise serializers.ValidationError(
                {"scenario_rules": "Правила сценария доступны только для доходных операций"}
            )
        if is_provided(scenario_data):
            raise serializers.ValidationError(
                {"scenario": "Сценарий доступен только для доходных операций"}
            )

    def _get_authenticated_user(self) -> Any | None:
        request = self.context.get("request", None)
        if request is None:
            return None
        if not hasattr(request, "user"):
            return None
        # noinspection PyUnresolvedReferences
        user = request.user
        if not user:
            return None
        if not user.is_authenticated:
            return None
        return user

    def _get_field_value(self, field: str, attrs: dict[str, Any]):
        if field in attrs:
            return attrs[field]
        if self.instance is not None:
            return getattr(self.instance, field)
        return None

    def create(self, validated_data: dict[str, Any]) -> RegularOperation:
        scenario_rules = validated_data.pop("scenario_rules", [])
        scenario_data = validated_data.pop("scenario", serializers.empty)
        with transaction.atomic():
            operation = RegularOperation.objects.create(**validated_data)
            self._sync_scenario(operation, scenario_rules, scenario_data)
        return operation

    def update(
        self, instance: RegularOperation, validated_data: dict[str, Any]
    ) -> RegularOperation:
        scenario_rules = validated_data.pop("scenario_rules", serializers.empty)
        scenario_data = validated_data.pop("scenario", serializers.empty)
        with transaction.atomic():
            operation = super().update(instance, validated_data)
            self._sync_scenario(operation, scenario_rules, scenario_data)
        return operation

    def _sync_scenario(
        self,
        operation: RegularOperation,
        scenario_rules: ScenarioRulesData | EmptyValue,
        scenario_data: ScenarioMetaData | EmptyValue,
    ) -> None:
        scenario_data_provided = scenario_data is not serializers.empty
        scenario_defaults = {
            "title": operation.title,
            "description": operation.description,
            "is_active": operation.is_active,
        }
        scenario_data_payload = (
            scenario_data
            if scenario_data_provided and scenario_data is not None
            else {}
        )
        scenario_creation_values = {**scenario_defaults, **scenario_data_payload}

        if operation.type == RegularOperationType.INCOME:
            scenario = getattr(operation, "scenario", None)
            if scenario is None:
                scenario = PaymentScenario.objects.create(
                    user=operation.user,
                    operation=operation,
                    **scenario_creation_values,
                )
            elif scenario_data_provided:
                fields_to_update: list[str] = []
                if "title" in scenario_data_payload:
                    scenario.title = scenario_data_payload["title"]
                    fields_to_update.append("title")
                if "description" in scenario_data_payload:
                    scenario.description = scenario_data_payload["description"]
                    fields_to_update.append("description")
                if "is_active" in scenario_data_payload:
                    scenario.is_active = scenario_data_payload["is_active"]
                    fields_to_update.append("is_active")
                if fields_to_update:
                    scenario.save(update_fields=fields_to_update)

            if scenario_rules is not serializers.empty:
                ScenarioRule.objects.filter(scenario=scenario).delete()
                rules_to_create: list[ScenarioRule] = []
                if scenario_rules:
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
