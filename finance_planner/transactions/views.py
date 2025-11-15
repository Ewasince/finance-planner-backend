import calendar
from datetime import date, date as _date, datetime, timedelta
from decimal import Decimal

from accounts.models import Account
from dateutil.rrule import DAILY, rrule
from django.db import transaction, transaction as db_transaction
from django.db.models import F, Q, QuerySet
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from regular_operations.models import (
    RegularOperation,
    RegularOperationPeriodType,
    RegularOperationType,
)
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from serializers import StartEndInputSerializer
from transactions.models import Transaction, TransactionType
from transactions.serializers import (
    CalculateResponse,
    TransactionCreateSerializer,
    TransactionSerializer,
    TransactionUpdateSerializer,
)
from utils import field_updated, get_result_field


OPERATION_TO_TRANSACTION_TYPE: dict[str, str] = {
    RegularOperationType.INCOME: TransactionType.INCOME,
    RegularOperationType.EXPENSE: TransactionType.EXPENSE,
}


class TransactionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = {
        "type": ["exact", "in"],
        "confirmed": ["exact"],
        "date": ["exact", "gte", "lte"],
        "amount": ["gte", "lte"],
        "from_account": ["exact"],
        "to_account": ["exact"],
    }
    search_fields = ["description"]
    ordering_fields = ["date", "amount", "created_at"]
    ordering = ["-date"]

    def get_serializer_class(self):
        if self.action in ["create"]:
            return TransactionCreateSerializer
        if self.action in ["update", "partial_update"]:
            return TransactionUpdateSerializer
        return TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(
            user=self.request.user,
        ).select_related(
            "from_account",
            "to_account",
        )

    def perform_create(self, serializer: TransactionCreateSerializer):  # type: ignore[override]
        with transaction.atomic():
            datetime_now = timezone.now()
            if (
                serializer.validated_data["confirmed"]
                and serializer.validated_data["date"] <= datetime_now.date()
            ):
                amount = serializer.validated_data["amount"]

                to_account = serializer.validated_data.get("to_account")
                if to_account is not None:
                    self._change_account_balance(to_account, amount, datetime_now)

                from_account = serializer.validated_data.get("from_account")
                if from_account is not None:
                    self._change_account_balance(from_account, -amount, datetime_now)
            serializer.save(user=self.request.user)

    def perform_update(self, serializer: TransactionCreateSerializer):  # type: ignore[override]
        with transaction.atomic():
            datetime_now = timezone.now()
            if (
                get_result_field("confirmed", serializer)
                and get_result_field("date", serializer) <= datetime_now.date()  # type: ignore[operator]
                and (
                    field_updated("amount", serializer)
                    or field_updated("to_account", serializer)
                    or field_updated("from_account", serializer)
                )
            ):
                if not serializer.instance:
                    raise ValueError(
                        f"No transaction instance for {serializer.validated_data.get('id')}"
                    )
                old_amount = serializer.instance.amount
                new_amount = serializer.validated_data.get("amount", old_amount)

                old_to_account = serializer.instance.to_account
                new_to_account = serializer.validated_data.get("to_account", old_to_account)
                self._change_account_balance(old_to_account, -old_amount, datetime_now)
                self._change_account_balance(new_to_account, new_amount, datetime_now)

                old_from_account = serializer.instance.from_account
                new_from_account = serializer.validated_data.get("from_account", old_from_account)
                self._change_account_balance(old_from_account, old_amount, datetime_now)
                self._change_account_balance(new_from_account, -new_amount, datetime_now)

            serializer.save(user=self.request.user)

    def _change_account_balance(
        self, account: Account | None, amount: Decimal, datetime_now: datetime
    ) -> None:
        if not account:
            return
        rows = Account.objects.filter(user=self.request.user, id=account.id).update(
            current_balance=F("current_balance") + amount,
            current_balance_updated=datetime_now,
        )
        if not rows:
            raise ValueError(f"User '{self.request.user}' doesn't have account '{account}'")

    @swagger_auto_schema(
        request_body=StartEndInputSerializer(),
        methods=[
            "post",
        ],
        responses={200: CalculateResponse, 400: "Ошибка"},
    )
    @action(detail=False, methods=["post"], url_path="calculate")
    def calculate(self, request: Request):
        """Создать транзакции на основе регулярных операций."""
        # 1) Валидируем входные параметры через сериализатор
        serializer = StartEndInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data

        current_date = timezone.localdate()
        start_date: _date = params.get("start_date") or current_date
        end_date: _date = params.get("end_date") or current_date + timedelta(days=90)

        now = timezone.now()
        # 2) Дальше — логика создания/планирования
        date_range_regular_operations: QuerySet[RegularOperation] = (
            RegularOperation.available_objects.filter(
                user=request.user, active_before__gt=now.date()
            )
            .filter(start_date__date__lte=end_date)
            .filter(end_date__date__gte=start_date)
            .filter(Q(deleted_at__date__lt=end_date) | Q(deleted_at__isnull=True))
            .select_related("from_account", "to_account")
            .prefetch_related("scenario", "scenario__rules")
        )
        date_range_existing_transactions = (
            Transaction.objects.filter(user=request.user)
            .filter(planned_date__gte=start_date)
            .filter(planned_date__lte=end_date)
        )

        with db_transaction.atomic():
            all_transaction_ids = []
            transactions = []
            for regular_operation in date_range_regular_operations:
                scenario_rules = []
                if hasattr(regular_operation, "scenario"):
                    scenario_rules = regular_operation.scenario.rules.all()

                # noinspection PyTypeChecker
                for dt in rrule(DAILY, dtstart=start_date, until=end_date):
                    selected_date = dt.date()

                    if not _is_transaction_day(
                        regular_operation.created_at.date(),
                        regular_operation.deleted_at.date()
                        if regular_operation.deleted_at
                        else None,
                        selected_date,
                        regular_operation.period_type,
                        regular_operation.period_interval,
                    ):
                        continue
                    if date_range_existing_transactions.filter(
                        operation=regular_operation,
                        planned_date=selected_date,
                    ).exists():
                        continue

                    transaction = Transaction.objects.create(
                        user=request.user,
                        date=selected_date,
                        planned_date=selected_date,
                        type=OPERATION_TO_TRANSACTION_TYPE[regular_operation.type],
                        amount=regular_operation.amount,
                        from_account=regular_operation.from_account,
                        to_account=regular_operation.to_account,
                        operation=regular_operation,
                        confirmed=False,
                    )
                    transactions.append(transaction)
                    all_transaction_ids.append(transaction.id)

                    for rule in scenario_rules:
                        if date_range_existing_transactions.filter(
                            scenario_rule=rule,
                            planned_date=selected_date,
                        ).exists():
                            continue

                        transaction = Transaction.objects.create(
                            user=request.user,
                            date=selected_date,
                            planned_date=selected_date,
                            type=TransactionType.TRANSFER,
                            amount=rule.amount,
                            from_account=regular_operation.to_account,
                            to_account=rule.target_account,
                            scenario_rule=rule,
                            confirmed=False,
                        )
                        transactions.append(transaction)
                        all_transaction_ids.append(transaction.id)

        return Response(
            CalculateResponse(
                {
                    "transactions_created": len(all_transaction_ids),
                }
            ).data,
            status=status.HTTP_200_OK,
        )


def _is_transaction_day(  # noqa: PLR0911
    created_date: date,
    deleted_date: date | None,
    current_date: date,
    period_type: str,
    period_interval: int,
) -> bool:
    if current_date < created_date:
        return False
    if deleted_date is not None and current_date >= deleted_date:
        return False

    match period_type:
        case RegularOperationPeriodType.DAY:
            delta_days = (current_date - created_date).days
            return delta_days % period_interval == 0
        case RegularOperationPeriodType.WEEK:
            if current_date.weekday() != created_date.weekday():
                return False
            delta_days = (current_date - created_date).days
            weeks = delta_days // 7
            return weeks % period_interval == 0
        case RegularOperationPeriodType.MONTH:
            months_from_start = (current_date.year - created_date.year) * 12 + (
                current_date.month - created_date.month
            )
            if months_from_start % period_interval != 0:
                return False
            last_day_this_month = calendar.monthrange(current_date.year, current_date.month)[1]
            due_day = min(created_date.day, last_day_this_month)

            return current_date.day == due_day

        case _:
            raise ValueError(f"Unknown period type: {period_type}")
