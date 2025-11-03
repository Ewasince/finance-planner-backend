from rest_framework.routers import SimpleRouter
from scenarios.views import ScenarioRuleViewSet, ScenarioViewSet


router = SimpleRouter()
router.register("rules", ScenarioRuleViewSet, basename="scenario-rule")
router.register("", ScenarioViewSet, basename="scenario")

urlpatterns = router.urls
