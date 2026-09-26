import logging

from django.db import OperationalError

from .models import AuditEvent


logger = logging.getLogger("procezo.requests")


def record(request, *, action, unit, resource=None, details=None):
    try:
        return AuditEvent.objects.create(
            actor=request.user,
            unit=unit,
            classification=getattr(resource, "classification", 0),
            action=action,
            resource_type=resource._meta.model_name if resource is not None else "scope",
            resource_id=resource.pk if resource is not None else None,
            request_id=request.request_id,
            details=details or {},
        )
    except OperationalError:
        logger.error("audit_failure", extra={"request_id": str(request.request_id)})
        raise
