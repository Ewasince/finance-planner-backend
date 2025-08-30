from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum
from django.utils import timezone
from .models import Transaction
from .serializers import TransactionSerializer, TransactionCreateSerializer


class TransactionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'confirmed', 'date']
    search_fields = ['description', 'amount']
    ordering_fields = ['date', 'amount', 'created_at']
    ordering = ['-date']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TransactionCreateSerializer
        return TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).select_related('from_account', 'to_account')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date', timezone.now().date())

        queryset = self.get_queryset()
        if start_date:
            queryset = queryset.filter(date__gte=start_date, date__lte=end_date)

        summary = queryset.values('type').annotate(
            total=Sum('amount')
        )

        return Response(summary)

    @action(detail=False, methods=['get'])
    def by_month(self, request):
        queryset = self.get_queryset()
        monthly_data = []

        # Упрощенная реализация для начала
        for transaction in queryset:
            month = transaction.date.strftime('%Y-%m')
            monthly_data.append({
                'month': month,
                'type': transaction.type,
                'amount': float(transaction.amount)
            })

        return Response(monthly_data)
