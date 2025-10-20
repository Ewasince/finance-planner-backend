from rest_framework import serializers

from .models import Account


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
            "accent_color",
            "gradient_theme",
            "custom_image_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class AccountCreateSerializer(serializers.ModelSerializer):
    type: serializers.Serializer = serializers.Serializer(required=False)

    class Meta:
        model = Account
        fields = [
            "name",
            "type",
            "current_balance",
            "target_amount",
            "description",
            "accent_color",
            "gradient_theme",
            "custom_image_url",
        ]
