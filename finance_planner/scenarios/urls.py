from rest_framework.routers import SimpleRouter

from scenarios.views import PaymentScenarioViewSet, ScenarioRuleViewSet


router = SimpleRouter()
router.register("rules", ScenarioRuleViewSet, basename="scenario-rule")
router.register("", PaymentScenarioViewSet, basename="scenario")

urlpatterns = router.urls
