from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, UserProfileViewSet

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('me/change-password/', UserProfileViewSet.as_view({'post': 'change_password'}), name='user-change-password'),
    path('me/stats/', UserProfileViewSet.as_view({'get': 'stats'}), name='user-stats'),
    path('me/activity/', UserProfileViewSet.as_view({'get': 'activity'}), name='user-activity'),
    path('', include(router.urls)),
]
