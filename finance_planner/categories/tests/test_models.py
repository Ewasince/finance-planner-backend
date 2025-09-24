from django.contrib.auth import get_user_model
from django.test import TestCase

from categories.models import Category


class CategoryModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="categorizer",
            email="cat@example.com",
            password="password123",
        )

    def test_string_representation_uses_display_name(self):
        category = Category.objects.create(
            user=self.user,
            name="Продукты",
            type=Category.CategoryType.EXPENSE,
        )

        self.assertEqual(str(category), "Продукты (Расход)")

    def test_is_root_and_has_children_properties(self):
        parent = Category.objects.create(
            user=self.user,
            name="Дом",
            type=Category.CategoryType.EXPENSE,
        )
        child = Category.objects.create(
            user=self.user,
            name="Коммунальные",
            type=Category.CategoryType.EXPENSE,
            parent=parent,
        )

        self.assertTrue(parent.is_root)
        self.assertTrue(parent.has_children)
        self.assertFalse(child.is_root)
        self.assertFalse(child.has_children)
