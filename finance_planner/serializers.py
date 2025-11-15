from rest_framework import serializers


class StartEndInputSerializer(serializers.Serializer):
    start_date = serializers.DateField(
        required=False,
        help_text="Начальная дата для генерации транзакций (по умолчанию — сегодня)",
    )
    end_date = serializers.DateField(
        required=False,
        help_text="Конечная дата для генерации транзакций (по умолчанию — сегодня)",
    )
