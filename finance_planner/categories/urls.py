from django.urls import path, include
from rest_framework.routers import DefaultRouter
from categories.views import CategoryViewSet

router = DefaultRouter()
router.register(r'', CategoryViewSet, basename='category')

urlpatterns = [
    path('tree/', CategoryViewSet.as_view({'get': 'tree'}), name='category-tree'),
    path('by-type/', CategoryViewSet.as_view({'get': 'by_type'}), name='category-by-type'),
    path('roots/', CategoryViewSet.as_view({'get': 'roots'}), name='category-roots'),
    path('with-budget/', CategoryViewSet.as_view({'get': 'with_budget'}), name='category-with-budget'),
    path('<uuid:pk>/children/', CategoryViewSet.as_view({'get': 'children'}), name='category-children'),
    path('', include(router.urls)),
]