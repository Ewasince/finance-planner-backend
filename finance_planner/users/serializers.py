from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "created_at"]
        read_only_fields = ["id", "created_at"]


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    password2 = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    tokens = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "password",
            "password2",
            "first_name",
            "last_name",
            "tokens",
        )
        extra_kwargs = {
            "password": {"write_only": True},
            "password2": {"write_only": True},
        }

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})

        if User.objects.filter(username=attrs.get("username")).exists():
            raise serializers.ValidationError(
                {"username": "Пользователь с таким именем уже существует"}
            )

        return attrs

    def create(self, validated_data):
        # Удаляем password2 из данных
        validated_data.pop("password2")

        # Создаем пользователя с хешированным паролем
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],  # Пароль автоматически хешируется
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )

        return user


class UserProfileSerializer(serializers.ModelSerializer):
    # Вычисляемые поля для статистики
    accounts_count = serializers.SerializerMethodField()
    transactions_count = serializers.SerializerMethodField()
    scenarios_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "created_at",
            "accounts_count",
            "transactions_count",
            "scenarios_count",
            "is_active",
            "last_login",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "accounts_count",
            "transactions_count",
            "scenarios_count",
            "last_login",
        ]

    def get_accounts_count(self, obj):
        return obj.accounts.count()

    def get_transactions_count(self, obj):
        return obj.transactions.count()

    def get_scenarios_count(self, obj):
        return obj.scenarios.count()


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def validate_email(self, value):
        # Проверяем, что email не занят другим пользователем
        if User.objects.filter(email=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True, write_only=True, validators=[validate_password]
    )
    new_password2 = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password": "Пароли не совпадают"})
        return attrs
