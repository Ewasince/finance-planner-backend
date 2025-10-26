from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions

from scenarios.models import PaymentScenario
from scenarios.serializers import ScenarioRuleCreateSerializer


class ScenarioRuleCreateView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ScenarioRuleCreateSerializer

    def get_queryset(self):  # pragma: no cover - required by DRF generics
        return PaymentScenario.objects.filter(user=self.request.user)

    def get_scenario(self) -> PaymentScenario:
        if not hasattr(self, "_scenario"):
            self._scenario = get_object_or_404(
                PaymentScenario.objects.filter(user=self.request.user),
                pk=self.kwargs["scenario_id"],
            )
        return self._scenario

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["scenario"] = self.get_scenario()
        return context
