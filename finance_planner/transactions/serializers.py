from rest_framework import serializers
from transactions.models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    from_account_name = serializers.CharField(source='from_account.name', read_only=True)
    to_account_name = serializers.CharField(source='to_account.name', read_only=True)
    # В TransactionSerializer добавить:
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Transaction
        fields = ['id', 'user', 'date', 'type', 'amount', 'from_account', 'to_account',
                  'from_account_name', 'to_account_name', 'category', 'category_name',
                  'confirmed', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class TransactionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['date', 'type', 'amount', 'category_name', 'from_account', 'to_account', 'confirmed', 'description']

    def validate(self, data):
        # Валидация будет дополнена позже
        return data
