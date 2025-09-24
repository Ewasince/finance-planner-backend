from datetime import timedelta

from rest_framework import viewsets, permissions, status

from rest_framework.decorators import action
from rest_framework.response import Response

from users.models import User
from users.serializers import (
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    ChangePasswordSerializer,
    UserSerializer,
)
from django.utils import timezone


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'profile':
            return UserProfileSerializer
        return UserSerializer

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=['get', 'put', 'patch'])
    def profile(self, request):
        user = request.user
        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return Response(serializer.data)
        elif request.method in ['PUT', 'PATCH']:
            serializer = self.get_serializer(user, data=request.data, partial=request.method == 'PATCH')
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        """Получение профиля текущего пользователя"""
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Получение профиля по ID (только своего)"""
        if pk != 'me' and str(request.user.id) != pk:
            return Response(
                {"error": "Вы можете просматривать только свой профиль"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """Обновление профиля пользователя"""
        serializer = UserProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=request.method == 'PATCH'
        )

        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Профиль успешно обновлен",
                "user": UserProfileSerializer(request.user).data
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Смена пароля"""
        serializer = ChangePasswordSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user

        # Проверяем старый пароль
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {"old_password": ["Неверный текущий пароль"]},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Устанавливаем новый пароль (автоматически хешируется)
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response({
            "message": "Пароль успешно изменен"
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Подробная статистика пользователя"""
        user = request.user

        # Более детальная статистика
        from django.db.models import Count, Sum

        stats = {
            'accounts': {
                'total': user.accounts.count(),
                'by_type': user.accounts.values('type').annotate(count=Count('id')),
                'total_balance': user.accounts.aggregate(total=Sum('current_balance'))['total'] or 0
            },
            'transactions': {
                'total': user.transactions.count(),
                'by_type': user.transactions.values('type').annotate(
                    count=Count('id'),
                    total_amount=Sum('amount')
                ),
                'last_30_days': user.transactions.filter(
                    date__gte=timezone.now() - timedelta(days=30)
                ).count()
            },
            'scenarios': {
                'total': user.payment_scenarios.count(),
                'active': user.payment_scenarios.filter(is_active=True).count()
            }
        }

        return Response(stats)

    @action(detail=False, methods=['get'])
    def activity(self, request):
        """Последняя активность пользователя"""
        user = request.user

        recent_transactions = user.transactions.select_related(
            'from_account', 'to_account'
        ).order_by('-date', '-created_at')[:5]

        recent_accounts = user.accounts.order_by('-updated_at')[:3]

        return Response({
            'recent_transactions': [
                {
                    'id': str(t.id),
                    'date': t.date,
                    'type': t.type,
                    'amount': float(t.amount),
                    'description': t.description
                } for t in recent_transactions
            ],
            'recent_accounts': [
                {
                    'id': str(a.id),
                    'name': a.name,
                    'type': a.type,
                    'balance': float(a.current_balance)
                } for a in recent_accounts
            ],
            'last_login': user.last_login,
            'last_activity': timezone.now()
        })
