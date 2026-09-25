import uuid

from django.conf import settings
from django.db import models


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Les événements d'audit sont immuables")

    def delete(self):
        raise TypeError("Les événements d'audit sont immuables")


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    occurred_at = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    unit = models.ForeignKey("identity.Unit", on_delete=models.PROTECT)
    classification = models.PositiveSmallIntegerField(default=0)
    action = models.CharField(max_length=64)
    resource_type = models.CharField(max_length=32)
    resource_id = models.UUIDField(null=True, blank=True)
    request_id = models.UUIDField()
    details = models.JSONField(default=dict, blank=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ["-occurred_at", "-id"]
        indexes = [models.Index(fields=["unit", "occurred_at"]), models.Index(fields=["resource_type", "resource_id"])]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise TypeError("Les événements d'audit sont immuables")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Les événements d'audit sont immuables")
