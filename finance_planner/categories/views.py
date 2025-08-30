from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from categories.models import Category
from categories.serializers import CategorySerializer, CategoryCreateSerializer, CategoryTreeSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CategoryCreateSerializer
        return CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user).select_related('parent')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Дерево категорий с вложенностью"""
        categories = Category.objects.filter(
            user=request.user,
            parent__isnull=True
        ).prefetch_related('children')

        serializer = CategoryTreeSerializer(categories, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Категории сгруппированные по типам"""
        category_type = request.query_params.get('type')

        queryset = self.get_queryset()
        if category_type:
            queryset = queryset.filter(type=category_type)

        # Группируем по типу и считаем количество
        categories_by_type = queryset.values('type').annotate(
            count=Count('id')
        ).order_by('type')

        return Response(categories_by_type)

    @action(detail=False, methods=['get'])
    def roots(self, request):
        """Только корневые категории (без родителей)"""
        root_categories = self.get_queryset().filter(parent__isnull=True)
        serializer = self.get_serializer(root_categories, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        """Дочерние категории"""
        category = self.get_object()
        children = category.children.all()
        serializer = self.get_serializer(children, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def with_budget(self, request):
        """Категории с установленным лимитом бюджета"""
        budget_categories = self.get_queryset().filter(
            budget_limit__isnull=False
        ).order_by('type', 'name')

        serializer = self.get_serializer(budget_categories, many=True)
        return Response(serializer.data)
