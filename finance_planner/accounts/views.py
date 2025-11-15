from datetime import date as _date, timedelta
from decimal import Decimal

from accounts.models import Account
from accounts.serializers import (
    AccountCreateSerializer,
    AccountSerializer,
    AccountUpdateSerializer,
    StatisticsRequestSerializer,
    StatisticsResponse,
)
from dateutil.rrule import DAILY, rrule
from django.db.models import Case, F, Q, QuerySet, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from transactions.models import Transaction


class AccountViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self) -> type[AccountSerializer] | type[AccountCreateSerializer]:
        if self.action in ["create"]:
            return AccountCreateSerializer
        if self.action in ["update", "partial_update"]:
            return AccountUpdateSerializer
        return AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(
            user=self.request.user.id,  # type: ignore[union-attr] # TODO: fix types
        ).order_by(
            "-created_at",
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @swagger_auto_schema(
        request_body=StatisticsRequestSerializer(),
        methods=[
            "post",
        ],
        responses={200: StatisticsResponse, 400: "Ошибка"},
    )
    @action(detail=False, methods=["post"], url_path="statistics")
    def statistics(self, request: Request):
        serializer = StatisticsRequestSerializer(data=request.data or request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data

        current_date = timezone.localdate()
        start_date: _date = params.get("start_date") or current_date
        end_date: _date = params.get("end_date") or current_date + timedelta(days=90)
        only_confirmed: bool = params["only_confirmed"]
        accounts_ids: list[Account] = [account.id for account in params.get("accounts", [])]

        user_accounts = Account.objects.filter(user=request.user)
        if accounts_ids:
            user_accounts = user_accounts.filter(id__in=accounts_ids)

        date_range_existing_transactions: QuerySet[Transaction] = (
            Transaction.objects.filter(user=request.user)
            .filter(date__gte=min(current_date, start_date))
            .filter(date__lte=max(current_date, end_date))
        )
        if only_confirmed:
            date_range_existing_transactions.filter(confirmed=True)
        if accounts_ids:
            date_range_existing_transactions.filter(
                Q(from_account__in=accounts_ids) | Q(to_account__in=accounts_ids)
            )

        balances: dict[str, dict[str, Decimal]] = {}

        for account in user_accounts:
            account_values_by_days: dict[str, Decimal] = {}
            balances[str(account.id)] = account_values_by_days

            account_transactions = date_range_existing_transactions.filter(
                Q(from_account=account) | Q(to_account=account)
            )
            account_current_balance = account.current_balance + _calculate_account_start_delta(
                account,
                date_range_existing_transactions,
                start_date,
                current_date,
            )
            for dt in rrule(DAILY, dtstart=start_date, until=end_date):
                selected_date = dt.date()
                current_date_transactions = account_transactions.filter(date=selected_date)
                for transaction in current_date_transactions:
                    if transaction.to_account == account:
                        account_current_balance += transaction.amount
                    if transaction.from_account == account:
                        account_current_balance -= transaction.amount
                account_values_by_days[selected_date.isoformat()] = account_current_balance

        return Response(
            StatisticsResponse(instance={"balances": balances}).data,
            status=status.HTTP_200_OK,
        )


def _calculate_account_start_delta(
    account: Account,
    actual_transactions: QuerySet[Transaction],
    start_date: _date,
    current_date: _date,
) -> Decimal:
    start_transactions = (
        actual_transactions.filter(date__gte=min(start_date, current_date))
        .filter(date__lt=max(start_date, current_date))
        .filter(Q(from_account=account) | Q(to_account=account))
    )

    zero = Value(Decimal("0"))
    minus_one = Value(Decimal("-1"))

    result = start_transactions.aggregate(
        balance=Coalesce(
            Sum(
                Case(
                    When(to_account=account, then=F("amount")),  # приход
                    When(from_account=account, then=F("amount") * minus_one),  # расход
                    default=zero,
                ),
            ),
            zero,
        )
    )

    start_balance_delta = result["balance"]

    if start_date < current_date:
        return -start_balance_delta
    return start_balance_delta
