from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentScenarioViewSet, ScenarioRuleViewSet

router = DefaultRouter()
router.register(r'', PaymentScenarioViewSet, basename='scenario')

scenario_router = DefaultRouter()
scenario_router.register(r'rules', ScenarioRuleViewSet, basename='scenario-rule')

urlpatterns = [
    path('<uuid:scenario_pk>/', include(scenario_router.urls)),
    path('<uuid:pk>/rules/', PaymentScenarioViewSet.as_view({'get': 'rules'}), name='scenario-rules'),
    path('<uuid:pk>/execute/', PaymentScenarioViewSet.as_view({'post': 'execute'}), name='scenario-execute'),
    path('', include(router.urls)),
]
