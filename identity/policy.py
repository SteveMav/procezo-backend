from django.db.models import Q
from django.utils import timezone

from .models import Delegation, Membership


def active_memberships(actor, *, unit=None, now=None):
    if not actor or not actor.is_authenticated or not actor.is_active:
        return Membership.objects.none()
    now = now or timezone.now()
    memberships = Membership.objects.filter(user=actor, revoked_at__isnull=True, valid_from__lte=now).filter(Q(valid_until__isnull=True) | Q(valid_until__gt=now))
    return memberships.filter(unit=unit) if unit is not None else memberships


def has_delegation(actor, action, unit, *, now=None):
    now = now or timezone.now()
    return Delegation.objects.filter(user=actor, unit=unit, action=action, revoked_at__isnull=True, valid_from__lte=now).filter(Q(valid_until__isnull=True) | Q(valid_until__gt=now)).exists()


def can(actor, action, resource=None, context=None):
    """Prototype policy. A missing membership, scope or clearance always denies."""
    context = context or {}
    unit = getattr(resource, "unit", None) or context.get("unit")
    if unit is None:
        return False
    classification = getattr(resource, "classification", context.get("classification"))
    if classification not in (0, 1):
        return False
    memberships = list(active_memberships(actor, unit=unit).filter(clearance__gte=classification))
    if not memberships:
        return False
    roles = {membership.role for membership in memberships}
    if action == "case.create":
        return Membership.Role.MANAGER in roles and has_delegation(actor, Delegation.Action.CASE_CREATE, unit)
    if action == "case.assign":
        return Membership.Role.MANAGER in roles and has_delegation(actor, Delegation.Action.CASE_ASSIGN, unit)
    if action in ("case.read", "case.update"):
        if Membership.Role.MANAGER in roles:
            return True
        return Membership.Role.INVESTIGATOR in roles and resource is not None and resource.assignee_id == actor.pk
    if action == "audit.read":
        return Membership.Role.AUDITOR in roles and has_delegation(actor, Delegation.Action.AUDIT_READ, unit)
    return False


def visible_cases(actor):
    from cases.models import Case

    memberships = list(active_memberships(actor))
    if not memberships:
        return Case.objects.none()
    scope = Q(pk__in=[])
    for membership in memberships:
        allowed = Q(unit=membership.unit, classification__lte=membership.clearance)
        if membership.role == Membership.Role.MANAGER:
            scope |= allowed
        elif membership.role == Membership.Role.INVESTIGATOR:
            scope |= allowed & Q(assignee=actor)
    return Case.objects.filter(scope).distinct()
