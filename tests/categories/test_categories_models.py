import pytest
from django.contrib.auth import get_user_model

from categories.models import Category


pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return get_user_model().objects.create_user(
        username="categorizer",
        email="cat@example.com",
        password="password123",
    )


def test_string_representation_uses_display_name(user):
    category = Category.objects.create(
        user=user,
        name="Продукты",
        type=Category.CategoryType.EXPENSE,
    )

    assert str(category) == "Продукты (Расход)"


def test_is_root_and_has_children_properties(user):
    parent = Category.objects.create(
        user=user,
        name="Дом",
        type=Category.CategoryType.EXPENSE,
    )
    child = Category.objects.create(
        user=user,
        name="Коммунальные",
        type=Category.CategoryType.EXPENSE,
        parent=parent,
    )

    assert parent.is_root is True
    assert parent.has_children is True
    assert child.is_root is False
    assert child.has_children is False
