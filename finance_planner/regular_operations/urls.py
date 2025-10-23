from django.urls import include, path
from rest_framework.routers import DefaultRouter

from regular_operations.views import RegularOperationViewSet


router = DefaultRouter()
router.register(r"", RegularOperationViewSet, basename="regular-operation")

urlpatterns = [
    path("", include(router.urls)),
]
