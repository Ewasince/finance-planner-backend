from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AccountViewSet

router = DefaultRouter()
router.register(r'', AccountViewSet, basename='account')

urlpatterns = [
    path('<uuid:pk>/transfer/', AccountViewSet.as_view({'post': 'transfer'}), name='account-transfer'),
    path('', include(router.urls)),
]
