from typing import Any

from accounts.models import Account, AccountType
from rest_framework import serializers
from serializers import StartEndInputSerializer


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "id",
            "user",
            "name",
            "type",
            "current_balance",
            "target_amount",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class AccountCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "id",
            "name",
            "type",
            "current_balance",
            "target_amount",
            "description",
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        user = getattr(self.context.get("request"), "user", None)
        if user is None:
            raise serializers.ValidationError("Требуется аутентификация.")

        account_type = attrs.get("type")

        if (
            account_type == AccountType.MAIN
            and Account.objects.filter(user=user, type=AccountType.MAIN).exists()
        ):
            raise serializers.ValidationError({"type": "Нельзя создать два основных счёта"})
        return attrs


class AccountUpdateSerializer(AccountCreateSerializer):
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs.get("type", self.instance.type) != self.instance.type:
            raise serializers.ValidationError({"type": "Нельзя менять тип счёта"})
        return super().validate(attrs)


class StatisticsRequestSerializer(StartEndInputSerializer):
    only_confirmed = serializers.BooleanField(
        default=False,
        help_text="Показать только реальные изменения баланса",
    )
    accounts = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(),
        many=True,
        required=False,
        help_text="Список ID счетов модели Account",
    )


class StatisticsResponse(serializers.Serializer):
    balances = serializers.DictField(
        child=serializers.DictField(
            child=serializers.DecimalField(max_digits=12, decimal_places=2)
        ),
        help_text="Ключ — id счёта, значение — словарь {'дата': баланс}",
    )
