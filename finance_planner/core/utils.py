from typing import Any

from rest_framework import serializers


def is_provided(value: Any) -> bool:
    return value is not serializers.empty and value is not None
