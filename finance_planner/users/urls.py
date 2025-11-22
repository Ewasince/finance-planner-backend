from django.urls import include, path
from rest_framework.routers import DefaultRouter
from users.views import ServiceUserView, UserViewSet


router = DefaultRouter()
router.register(r"", UserViewSet, basename="user")

urlpatterns = [
    path("", include(router.urls)),
    path("svc/<int:user_id>/", ServiceUserView.as_view()),
]
