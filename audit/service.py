from .models import AuditEvent


def record(request, *, action, unit, resource=None, details=None):
    return AuditEvent.objects.create(
        actor=request.user,
        unit=unit,
        classification=getattr(resource, "classification", 0),
        action=action,
        resource_type="case" if resource is not None else "scope",
        resource_id=resource.pk if resource is not None else None,
        request_id=request.request_id,
        details=details or {},
    )
