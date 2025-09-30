from rest_framework import viewsets, permissions, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from .models import PaymentScenario, ScenarioRule
from scenarios.serializers import (
    PaymentScenarioSerializer,
    PaymentScenarioCreateSerializer,
    ScenarioRuleSerializer
)


class PaymentScenarioViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PaymentScenarioCreateSerializer
        return PaymentScenarioSerializer

    def get_queryset(self):
        return PaymentScenario.objects.filter(user=self.request.user.id).prefetch_related('rules__target_account')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get'])
    def rules(self, request, pk=None):
        scenario = self.get_object()
        rules = scenario.rules.all()
        serializer = ScenarioRuleSerializer(rules, many=True)
        return Response(serializer.data)


class ScenarioRuleViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet
):
    serializer_class = ScenarioRuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ScenarioRule.objects.filter(scenario__user=self.request.user.id)

    def perform_create(self, serializer):
        scenario_id = self.kwargs.get('scenario_pk')
        scenario = PaymentScenario.objects.get(id=scenario_id, user=self.request.user)
        serializer.save(scenario=scenario)
