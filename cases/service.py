import time

from django.contrib.auth import get_user_model
from django.db import OperationalError, connection, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from audit.service import record
from identity.models import Membership
from identity.policy import active_memberships, can
from platform_api.errors import Conflict

from .models import Case, CaseAction, CaseAssignment


def _get_valid_assignee(user_id, unit, classification):
    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    if user is None or not active_memberships(user, unit=unit).filter(role=Membership.Role.INVESTIGATOR, clearance__gte=classification).exists():
        raise ValidationError({"assignee": ["Agent non habilité pour cette unité et classification."]})
    return user


def _retry_sqlite_lock(operation):
    # Draft mutations are guarded by a version compare-and-set. Retrying a
    # rolled-back SQLite lock can therefore resolve to the expected 409.
    for attempt in range(3):
        try:
            return operation()
        except OperationalError as exc:
            if connection.vendor != "sqlite" or "locked" not in str(exc).lower() or attempt == 2:
                raise
            time.sleep(0.05 * (attempt + 1))


def create_case(request, *, unit, classification, assignee, next_action, assignment_reason):
    with transaction.atomic():
        if not can(request.user, "case.create", context={"unit": unit, "classification": classification}):
            raise PermissionDenied()
        if not can(request.user, "case.assign", context={"unit": unit, "classification": classification}):
            raise PermissionDenied()
        assignee = _get_valid_assignee(assignee, unit, classification)
        case = Case.objects.create(unit=unit, classification=classification, assignee=assignee, next_action=next_action, created_by=request.user)
        CaseAssignment.objects.create(case=case, new_assignee=assignee, author=request.user, reason=assignment_reason, version=case.version)
        CaseAction.objects.create(case=case, kind="created", actor=request.user, next_action=case.next_action, status=case.status, version=case.version)
        record(request, action="case.created", unit=unit, resource=case, details={"version": case.version, "assignee_id": assignee.pk})
    return case


def update_case(request, case, *, version, next_action=None, status=None):
    changed = {}
    if next_action is not None:
        changed["next_action"] = next_action
    if status is not None:
        changed["status"] = status
    changed["version"] = version + 1
    changed["updated_at"] = timezone.now()
    def operation():
        case.refresh_from_db()
        with transaction.atomic():
            if not can(request.user, "case.update", case):
                raise PermissionDenied()
            if Case.objects.filter(pk=case.pk, version=version).update(**changed) != 1:
                raise Conflict()
            case.refresh_from_db()
            CaseAction.objects.create(case=case, kind="updated", actor=request.user, next_action=case.next_action, status=case.status, version=case.version)
            record(request, action="case.updated", unit=case.unit, resource=case, details={"version": case.version, "fields": sorted(set(changed) - {"version", "updated_at"})})
        return case

    return _retry_sqlite_lock(operation)


def assign_case(request, case, *, version, assignee, reason):
    def operation():
        case.refresh_from_db()
        previous = case.assignee
        with transaction.atomic():
            if not can(request.user, "case.assign", case):
                raise PermissionDenied()
            new_assignee = _get_valid_assignee(assignee, case.unit, case.classification)
            if new_assignee.pk == case.assignee_id:
                raise ValidationError({"assignee": ["Cet agent est déjà responsable du dossier."]})
            if Case.objects.filter(pk=case.pk, version=version).update(assignee=new_assignee, version=version + 1, updated_at=timezone.now()) != 1:
                raise Conflict()
            case.refresh_from_db()
            CaseAssignment.objects.create(case=case, previous_assignee=previous, new_assignee=new_assignee, author=request.user, reason=reason, version=case.version)
            CaseAction.objects.create(case=case, kind="assigned", actor=request.user, next_action=case.next_action, status=case.status, version=case.version)
            record(request, action="case.assigned", unit=case.unit, resource=case, details={"version": case.version, "previous_assignee_id": previous.pk, "new_assignee_id": new_assignee.pk})
        return case

    return _retry_sqlite_lock(operation)
