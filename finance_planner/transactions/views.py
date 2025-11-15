import calendar
from datetime import date, date as _date, timedelta

from dateutil.rrule import DAILY, rrule
from django.db import transaction as db_transaction
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
)


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
        if self.action in ["create", "update", "partial_update"]:
            return TransactionCreateSerializer
        return TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(
            user=self.request.user,
        ).select_related(
            "from_account",
            "to_account",
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

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

        # 2) Дальше — логика создания/планирования
        date_range_regular_operations = (
            RegularOperation.objects.filter(user=request.user, active_before__gt=start_date)
            .filter(start_date__date__lte=end_date)
            .filter(end_date__date__gte=start_date)
            .select_related("from_account", "to_account")
            .prefetch_related("scenario", "scenario__rules")
        )
        date_range_existing_transactions = (
            Transaction.objects.filter(user=request.user)
            .filter(created_at__date__gte=start_date)
            .filter(created_at__date__lte=end_date)
        )

        # # 2) Дальше — логика создания/планирования
        # date_range_regular_operations = (
        #     RegularOperation.available_objects.filter(user=request.user, active_before=True)
        #     .filter(start_date__date__lte=end_date)
        #     .filter(end_date__date__gte=start_date)
        #     .filter(Q(deleted_at__date__lt=end_date) | Q(deleted_at__isnull=True))
        #     .select_related("from_account", "to_account")
        #     .prefetch_related("scenario", "scenario__rules")
        # )
        # date_range_existing_transactions = (
        #     Transaction.objects.filter(user=request.user)
        #     .filter(planned_date__date__gte=start_date)
        #     .filter(planned_date__date__lte=end_date)
        # )

        with db_transaction.atomic():
            all_transaction_ids = []
            transactions = []
            for regular_operation in date_range_regular_operations:
                # TODO: затираются confirmed транзакции, надо исправить
                date_range_existing_transactions.filter(operation=regular_operation).delete()

                scenario_rules = []
                if hasattr(regular_operation, "scenario"):
                    scenario_rules = regular_operation.scenario.rules.all()
                    date_range_existing_transactions.filter(
                        scenario_rule__in=scenario_rules
                    ).delete()

                for dt in rrule(DAILY, dtstart=start_date, until=end_date):
                    selected_date = dt.date()

                    if not _is_transaction_day(
                        regular_operation.created_at.date(),
                        selected_date,
                        regular_operation.period_type,
                        regular_operation.period_interval,
                    ):
                        continue

                    transaction = Transaction.objects.create(
                        user=request.user,
                        date=selected_date,
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
                        transaction = Transaction.objects.create(
                            user=request.user,
                            date=selected_date,
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


def _is_transaction_day(
    created_date: date,
    current_date: date,
    period_type: str,
    period_interval: int,
) -> bool:
    if current_date < created_date:
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
