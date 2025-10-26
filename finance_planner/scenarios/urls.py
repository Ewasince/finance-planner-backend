from django.urls import path

from scenarios.views import ScenarioRuleCreateView


urlpatterns = [
    path(
        "<uuid:scenario_id>/rules/",
        ScenarioRuleCreateView.as_view(),
        name="scenario-rule-create",
    ),
]
