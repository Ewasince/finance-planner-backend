from __future__ import annotations

from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.deletion import CASCADE
from django.db.models.fields.reverse_related import ForeignObjectRel
from django.utils.timezone import now
from model_utils.fields import AutoCreatedField, AutoLastModifiedField


class SoftDeletableModelManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class TimeWatchingModel(models.Model):
    created_at = AutoCreatedField("created_at")
    updated_at = AutoLastModifiedField("updated_at")
    deleted_at = models.DateTimeField(blank=True, null=True, default=None)  # type: ignore[var-annotated]

    objects: SoftDeletableModelManager = SoftDeletableModelManager()  # type: ignore[misc]
    available_objects: models.Manager[TimeWatchingModel] = models.Manager()

    class Meta:
        abstract = True

    def _soft_delete_related(self) -> None:
        for rel in self._meta.get_fields():
            if not isinstance(rel, ForeignObjectRel):
                continue

            if not (rel.auto_created and not rel.concrete and (rel.one_to_many or rel.one_to_one)):
                continue

            if rel.on_delete is not CASCADE:
                continue

            accessor_name = rel.get_accessor_name()
            if accessor_name is None:
                continue

            related = getattr(self, accessor_name)

            if rel.one_to_one:
                try:
                    obj = related
                except ObjectDoesNotExist:
                    obj = None

                if obj is not None:
                    obj.delete()
            else:
                for obj in related.all():
                    obj.delete()

    def delete(self, hard: bool = False, **kwargs: Any):  # type: ignore[override]
        if hard:
            return super().delete(**kwargs)

        self._soft_delete_related()

        self.deleted_at = now()
        self.save(update_fields={"deleted_at"})
        return None

    def restore(self) -> None:
        self.deleted_at = None
        self.save(update_fields={"deleted_at"})
