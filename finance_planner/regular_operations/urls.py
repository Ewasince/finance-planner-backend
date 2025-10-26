from django.urls import include, path
from regular_operations.views import RegularOperationViewSet
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r"", RegularOperationViewSet, basename="regular-operation")

urlpatterns = [
    path("", include(router.urls)),
]
