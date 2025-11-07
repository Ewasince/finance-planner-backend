from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    created_at: models.DateTimeField = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата регистрации"
    )

    email = models.EmailField("email", blank=True, null=True, unique=True)

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self) -> str:
        return self.email or self.username
