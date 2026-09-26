import hashlib
import uuid
from html import escape
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from rest_framework.exceptions import PermissionDenied, ValidationError

from audit.service import record
from documents.models import Document
from documents.service import private_path
from identity.policy import can
from platform_api.errors import Conflict, DependencyUnavailable

from .models import Defense, InspectionEvent, InspectionMission, Observation, ObservationAssessment, ObservationSheet, SheetProject


def _editable(request, case):
    if not can(request.user, "case.update", case):
        raise PermissionDenied()


def _documents(case, ids, *, field="documents", pdf=False):
    if len(ids) != len(set(ids)):
        raise ValidationError({field: ["Pièces distinctes requises."]})
    result = list(Document.objects.filter(pk__in=ids, case=case, state=Document.State.ACCEPTED))
    if len(result) != len(ids) or (pdf and any(doc.content_type != "application/pdf" for doc in result)):
        raise ValidationError({field: ["Pièces acceptées du dossier requises."]})
    for doc in result:
        path = private_path(doc.storage_name)
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            raise DependencyUnavailable()
        if digest != doc.sha256:
            raise DependencyUnavailable()
    return result


def _event(request, case, kind, obj):
    InspectionEvent.objects.create(case=case, kind=kind, resource_id=obj.pk, actor=request.user)
    record(request, action=f"inspection.{kind}", unit=case.unit, resource=case, details={"resource_id": str(obj.pk)})


def create_mission(request, case, data):
    _editable(request, case)
    ids = data["participants"]
    if len(ids) != len(set(ids)):
        raise ValidationError({"participants": ["Participants distincts requis."]})
    # Participant identity must be an active user with a current, cleared unit membership.
    participants = list(get_user_model().objects.filter(pk__in=ids, is_active=True))
    if len(participants) != len(ids):
        raise ValidationError({"participants": ["Compte actif requis."]})
    from identity.models import Membership
    now = timezone.now()
    eligible = set(Membership.objects.filter(user_id__in=ids, unit=case.unit, role__in=[Membership.Role.MANAGER, Membership.Role.INVESTIGATOR], revoked_at__isnull=True, valid_from__lte=now, clearance__gte=case.classification).filter(
        Q(valid_until__isnull=True) | Q(valid_until__gt=now)
    ).values_list("user_id", flat=True))
    if set(ids) != eligible:
        raise ValidationError({"participants": ["Participant habilité dans l'unité requis."]})
    with transaction.atomic():
        _editable(request, case)
        documents = _documents(case, data["documents"])
        mission = InspectionMission.objects.create(case=case, author=request.user, context=data["context"], findings=data["findings"], occurred_on=data["occurred_on"])
        mission.participants.set(participants)
        mission.documents.set(documents)
        _event(request, case, "mission.created", mission)
    return mission


def _observations(sheet, data, case):
    for number, item in enumerate(data, 1):
        docs = _documents(case, item["documents"], field="observations")
        observation = Observation.objects.create(sheet=sheet, number=number, facts=item["facts"])
        observation.documents.set(docs)


def create_sheet(request, case, data):
    _editable(request, case)
    mission_id = data.get("mission")
    if mission_id:
        mission = InspectionMission.objects.filter(pk=mission_id, case=case).first()
        if mission is None:
            raise ValidationError({"mission": ["Mission du dossier requise."]})
        if data["origin"] != ObservationSheet.Origin.MISSION:
            raise ValidationError({"origin": ["Une mission exige l'origine mission."]})
    else:
        mission = None
        # DEC-03 is pending: only a fictional field finding is enabled without a mission.
        if data["origin"] != ObservationSheet.Origin.FIELD:
            raise ValidationError({"origin": ["Origine sans mission non autorisée pour ce prototype."]})
    with transaction.atomic():
        _editable(request, case)
        sheet = ObservationSheet.objects.create(case=case, author=request.user, mission=mission, origin=data["origin"], recipient_address=data["recipient_address"], concerned_party=data["concerned_party"], facts=data["facts"])
        _observations(sheet, data["observations"], case)
        _event(request, case, "sheet.created", sheet)
    return sheet


def update_sheet(request, sheet, data):
    _editable(request, sheet.case)
    if request.user.pk != sheet.author_id:
        raise PermissionDenied()
    version = data["version"]
    with transaction.atomic():
        if not ObservationSheet.objects.filter(pk=sheet.pk, version=version).exists():
            raise Conflict()
        if "observations" in data and sheet.defenses.exists():
            raise ValidationError({"observations": ["Des défenses sont déjà liées aux observations."]})
        changed = ObservationSheet.objects.filter(pk=sheet.pk, version=version).update(**{key: value for key, value in data.items() if key not in ("version", "observations")}, version=version + 1, updated_at=timezone.now())
        if not changed:
            raise Conflict()
        if "observations" in data:
            sheet.observations.all().delete()
            _observations(sheet, data["observations"], sheet.case)
        _event(request, sheet.case, "sheet.updated", sheet)
    sheet.refresh_from_db()
    return sheet


def project_path(storage_name):
    return Path(settings.PROCEZO_PRIVATE_FILES_ROOT) / "sheets" / str(storage_name)


def _render_project(sheet, path):
    styles = getSampleStyleSheet()
    story = [Paragraph("PROJET FICTIF - NON ÉMIS", styles["Title"]), Spacer(1, 16), Paragraph("Feuille d'observations", styles["Heading1"])]
    for label, value in [("Dossier", sheet.case.reference), ("Destinataire", sheet.recipient_address), ("Partie concernée", sheet.concerned_party), ("Origine", sheet.origin), ("Faits", sheet.facts)]:
        story.append(Paragraph(f"{label} : {escape(value)}", styles["BodyText"]))
        story.append(Spacer(1, 8))
    if sheet.mission_id:
        story.append(Paragraph(f"Mission : {sheet.mission_id}", styles["BodyText"]))
    for observation in sheet.observations.all():
        story.append(Paragraph(f"Observation {observation.number} : {escape(observation.facts)}", styles["BodyText"]))
        for document in observation.documents.all():
            story.append(Paragraph(f"Pièce : {document.pk}", styles["BodyText"]))
        story.append(Spacer(1, 8))
    story.append(Paragraph("Projet du prototype. Aucune signature, émission ou notification constatée.", styles["Italic"]))
    SimpleDocTemplate(str(path), pagesize=A4).build(story)


def prepare_project(request, sheet, version):
    _editable(request, sheet.case)
    if request.user.pk != sheet.author_id:
        raise PermissionDenied()
    sheet.refresh_from_db()
    if sheet.version != version:
        raise Conflict()
    existing = sheet.projects.filter(sheet_version=version).first()
    if existing:
        project_file(existing)
        return existing
    storage_name = uuid.uuid4()
    path = project_path(storage_name)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _render_project(sheet, path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        with transaction.atomic():
            _editable(request, sheet.case)
            if ObservationSheet.objects.filter(pk=sheet.pk, version=version).count() != 1:
                raise Conflict()
            existing = sheet.projects.filter(sheet_version=version).first()
            if existing:
                return existing
            project = SheetProject.objects.create(sheet=sheet, sheet_version=version, storage_name=storage_name, sha256=digest, prepared_by=request.user)
            _event(request, sheet.case, "sheet.project.prepared", project)
            return project
    except IntegrityError:
        existing = sheet.projects.filter(sheet_version=version).first()
        if existing:
            return existing
        raise
    finally:
        if not SheetProject.objects.filter(storage_name=storage_name).exists():
            path.unlink(missing_ok=True)


def project_file(project):
    path = project_path(project.storage_name)
    try:
        if hashlib.sha256(path.read_bytes()).hexdigest() != project.sha256:
            raise DependencyUnavailable()
    except OSError:
        raise DependencyUnavailable()
    return path


def create_defense(request, sheet, data):
    _editable(request, sheet.case)
    ids = data["observation_ids"]
    if len(ids) != len(set(ids)):
        raise ValidationError({"observation_ids": ["Observations distinctes requises."]})
    observations = list(sheet.observations.filter(pk__in=ids))
    if len(observations) != len(ids):
        raise ValidationError({"observation_ids": ["Observation de la feuille requise."]})
    complement = None
    if "complement_of" in data:
        complement = sheet.defenses.filter(pk=data["complement_of"]).first()
        if complement is None:
            raise ValidationError({"complement_of": ["Défense de la feuille requise."]})
    with transaction.atomic():
        _editable(request, sheet.case)
        letter = _documents(sheet.case, [data["letter"]], field="letter")[0]
        annexes = _documents(sheet.case, data["annexes"], field="annexes")
        if letter in annexes:
            raise ValidationError({"annexes": ["Le courrier ne peut être une annexe."]})
        defense = Defense.objects.create(sheet=sheet, letter=letter, received_on=data["received_on"], recorded_by=request.user, complement_of=complement)
        defense.annexes.set(annexes)
        defense.observations.set(observations)
        _event(request, sheet.case, "defense.received", defense)
    return defense


def assess(request, observation, data):
    sheet = observation.sheet
    _editable(request, sheet.case)
    defense = sheet.defenses.filter(pk=data["defense"], observations=observation).first()
    if defense is None:
        raise ValidationError({"defense": ["Défense liée à cette observation requise."]})
    with transaction.atomic():
        version = data["version"]
        if Observation.objects.filter(pk=observation.pk, assessment_version=version).update(assessment_version=version + 1) != 1:
            raise Conflict()
        result = ObservationAssessment.objects.create(observation=observation, defense=defense, version=version + 1, conclusion=data["conclusion"], reason=data["reason"], actor=request.user)
        _event(request, sheet.case, "observation.assessed", result)
    return result
