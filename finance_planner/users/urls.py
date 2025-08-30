from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('profile/', UserViewSet.as_view({'get': 'profile', 'put': 'profile', 'patch': 'profile'}),
         name='user-profile'),
    path('', include(router.urls)),
]
