from rest_framework import mixins, permissions, status, viewsets
from rest_framework.response import Response
from scenarios.models import Scenario, ScenarioRule
from scenarios.serializers import (
    ScenarioCreateSerializer,
    ScenarioRuleCreateUpdateSerializer,
    ScenarioRuleSerializer,
    ScenarioSerializer,
    ScenarioUpdateSerializer,
)


class ScenarioViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Scenario.objects.filter(user=self.request.user)
            .select_related("operation")
            .prefetch_related("rules", "rules__target_account")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return ScenarioCreateSerializer
        if self.action in {"update", "partial_update"}:
            return ScenarioUpdateSerializer
        return ScenarioSerializer

    def _serialize_response(self, instance, *, status_code):
        serializer = ScenarioSerializer(instance, context=self.get_serializer_context())
        return Response(serializer.data, status=status_code)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scenario = serializer.save()
        return self._serialize_response(scenario, status_code=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):  # pragma: no cover - handled by partial_update
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        scenario = serializer.save()
        return self._serialize_response(scenario, status_code=status.HTTP_200_OK)


class ScenarioRuleViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            ScenarioRule.objects.filter(scenario__user=self.request.user)
            .select_related("scenario", "target_account")
            .order_by("order")
        )

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return ScenarioRuleCreateUpdateSerializer

        return ScenarioRuleSerializer

    def _serialize_response(self, instance, *, status_code):
        serializer = ScenarioRuleSerializer(instance, context=self.get_serializer_context())
        return Response(serializer.data, status=status_code)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rule = serializer.save()
        return self._serialize_response(rule, status_code=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        rule = serializer.save()
        return self._serialize_response(rule, status_code=status.HTTP_200_OK)
