from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserProfileSerializer(serializers.ModelSerializer):
    accounts_count = serializers.SerializerMethodField()
    transactions_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'created_at', 'accounts_count', 'transactions_count']
        read_only_fields = ['id', 'created_at', 'accounts_count', 'transactions_count']

    def get_accounts_count(self, obj):
        return obj.accounts.count()

    def get_transactions_count(self, obj):
        return obj.transactions.count()
