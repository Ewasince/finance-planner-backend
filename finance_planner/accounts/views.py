from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Account
from .serializers import AccountSerializer, AccountCreateSerializer


class AccountViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AccountCreateSerializer
        return AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def transfer(self, request, pk=None):
        account = self.get_object()
        # Логика перевода будет реализована позже
        return Response({'status': 'transfer endpoint', 'account_id': str(account.id)})
