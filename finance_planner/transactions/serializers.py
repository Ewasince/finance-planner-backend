from rest_framework import serializers

from .models import Transaction, TransactionType


class TransactionSerializer(serializers.ModelSerializer):
    from_account_name = serializers.CharField(source="from_account.name", read_only=True)
    to_account_name = serializers.CharField(source="to_account.name", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "user_id",
            "date",
            "type",
            "amount",
            "from_account",
            "to_account",
            "from_account_name",
            "to_account_name",
            "confirmed",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class TransactionCreateSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()

    def get_type(self, obj) -> str | None:
        if obj.from_account and obj.to_account:
            return TransactionType.TRANSFER
        elif obj.from_account and not obj.to_account:
            return TransactionType.EXPENSE
        elif not obj.from_account and obj.to_account:
            return TransactionType.INCOME

        return None

    class Meta:
        model = Transaction
        fields = [
            "date",
            "type",
            "amount",
            "from_account",
            "to_account",
            "confirmed",
            "description",
        ]

    def validate(self, data):
        # Валидация будет дополнена позже
        return data
