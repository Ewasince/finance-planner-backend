from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransactionViewSet

router = DefaultRouter()
router.register(r'', TransactionViewSet, basename='transaction')

urlpatterns = [
    path('summary/', TransactionViewSet.as_view({'get': 'summary'}), name='transaction-summary'),
    path('by-month/', TransactionViewSet.as_view({'get': 'by_month'}), name='transaction-by-month'),
    path('', include(router.urls)),
]
