from rest_framework import serializers
from categories.models import Category


class CategorySerializer(serializers.ModelSerializer):
    children_count = serializers.SerializerMethodField()
    is_root = serializers.BooleanField(read_only=True)
    has_children = serializers.BooleanField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'user', 'name', 'type', 'parent', 'color', 'icon',
                  'description', 'is_system', 'budget_limit', 'children_count',
                  'is_root', 'has_children', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'children_count']

    def get_children_count(self, obj):
        return obj.children.count()


class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['name', 'type', 'parent', 'color', 'icon', 'description', 'budget_limit']

    def validate(self, data):
        # Проверяем, что родительская категория принадлежит тому же пользователю
        request = self.context.get('request')
        if request and data.get('parent'):
            if data['parent'].user != request.user:
                raise serializers.ValidationError("Родительская категория должна принадлежать вам")
        return data


class CategoryTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'type', 'color', 'icon', 'children']

    def get_children(self, obj):
        children = obj.children.all()
        return CategoryTreeSerializer(children, many=True).data
