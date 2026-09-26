import hashlib
import uuid
from html import escape
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from rest_framework.exceptions import PermissionDenied, ValidationError

from audit.service import record
from documents.models import Document
from documents.service import private_path
from identity.policy import can
from platform_api.errors import Conflict, DependencyUnavailable

from .models import ActVersion, CommunicationRequest, ItemAssessment, RequestEvent, RequestIssuance, RequestedItem, RequestResponse, ResponseItemLink


def _can_edit(actor, request_obj):
    return actor.pk == request_obj.author_id and can(actor, "case.update", request_obj.case)


def _can_record(actor, request_obj):
    return can(actor, "case.update", request_obj.case)


def _document(case, document_id, *, pdf=False):
    document = Document.objects.filter(pk=document_id, case=case, state=Document.State.ACCEPTED).first()
    if document is None or (pdf and document.content_type != "application/pdf"):
        raise ValidationError({"document": ["Pièce PDF acceptée du dossier requise." if pdf else "Pièce acceptée du dossier requise."]})
    return document


def _verified_path(document):
    path = private_path(document.storage_name)
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        raise DependencyUnavailable()
    if digest != document.sha256:
        raise DependencyUnavailable()
    return path


def create_request(http_request, case, data):
    if not can(http_request.user, "case.update", case):
        raise PermissionDenied()
    with transaction.atomic():
        request_obj = CommunicationRequest.objects.create(
            case=case, author=http_request.user,
            target_type=data["target_type"], target_name=data["target_name"],
            represented_name=data["represented_name"], subject=data["subject"],
            mode=data["mode"], due_on=data.get("due_on"),
        )
        RequestedItem.objects.bulk_create([
            RequestedItem(request=request_obj, number=index, label=item["label"])
            for index, item in enumerate(data["items"], 1)
        ])
        record(http_request, action="request.created", unit=case.unit, resource=case, details={"request_id": str(request_obj.pk)})
    return request_obj


def update_request(http_request, request_obj, data):
    version = data["version"]
    if not _can_edit(http_request.user, request_obj):
        raise PermissionDenied()
    with transaction.atomic():
        changed = CommunicationRequest.objects.filter(pk=request_obj.pk, state=CommunicationRequest.State.DRAFT, version=version).update(
            **{key: value for key, value in data.items() if key not in ("version", "items")},
            version=version + 1, updated_at=timezone.now(),
        )
        if changed != 1:
            raise Conflict()
        if "items" in data:
            if request_obj.responses.exists() or ItemAssessment.objects.filter(item__request=request_obj).exists():
                raise ValidationError({"items": ["Les éléments liés à une réponse ne peuvent plus être modifiés."]})
            request_obj.items.all().delete()
            RequestedItem.objects.bulk_create([
                RequestedItem(request=request_obj, number=index, label=item["label"])
                for index, item in enumerate(data["items"], 1)
            ])
        record(http_request, action="request.updated", unit=request_obj.unit, resource=request_obj.case, details={"request_id": str(request_obj.pk), "version": version + 1, "fields": sorted(set(data) - {"version"})})
    request_obj.refresh_from_db()
    return request_obj


def act_path(storage_name):
    return Path(settings.PROCEZO_PRIVATE_FILES_ROOT) / "acts" / str(storage_name)


def _render_project(request_obj, path):
    styles = getSampleStyleSheet()
    styles["Title"].textColor = colors.HexColor("#17324d")
    story = [
        Paragraph("PROJET FICTIF - NON ÉMIS", styles["Title"]), Spacer(1, 20),
        Paragraph("Demande de communication - format de démonstration", styles["Heading1"]),
        Paragraph(f"Dossier : {escape(request_obj.case.reference)}", styles["Normal"]),
        Paragraph(f"Destinataire : {escape(request_obj.target_name)}", styles["Normal"]),
    ]
    if request_obj.represented_name:
        story.append(Paragraph(f"Pour le compte de : {escape(request_obj.represented_name)}", styles["Normal"]))
    story.extend([Spacer(1, 16), Paragraph(f"Objet : {escape(request_obj.subject)}", styles["Heading2"]), Spacer(1, 10)])
    for item in request_obj.items.all():
        story.append(Paragraph(f"{item.number}. {escape(item.label)}", styles["BodyText"]))
        story.append(Spacer(1, 7))
    story.append(Spacer(1, 18))
    story.append(Paragraph("Ce document est un projet du prototype Procezo. Il ne constate ni signature, ni émission, ni notification.", styles["Italic"]))
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=50, rightMargin=50, topMargin=55, bottomMargin=55).build(story)


def prepare_act(http_request, request_obj, *, version, document=None):
    if not _can_edit(http_request.user, request_obj):
        raise PermissionDenied()
    request_obj.refresh_from_db()
    if request_obj.state != CommunicationRequest.State.DRAFT or request_obj.version != version:
        raise Conflict()
    existing = request_obj.acts.filter(request_version=version).first()
    if existing:
        if document is not None and existing.imported_document_id != document:
            raise Conflict()
        return existing
    storage_name = None
    path = None
    if request_obj.mode == CommunicationRequest.Mode.IMPORTED:
        if document is None:
            raise ValidationError({"document": ["Document importé requis."]})
        imported = _document(request_obj.case, document, pdf=True)
        _verified_path(imported)
        digest = imported.sha256
    else:
        if document is not None:
            raise ValidationError({"document": ["Aucun import en mode généré."]})
        imported = None
        storage_name = uuid.uuid4()
        path = act_path(storage_name)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            _render_project(request_obj, path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except Exception:
            path.unlink(missing_ok=True)
            raise
    try:
        with transaction.atomic():
            request_obj.refresh_from_db()
            if not _can_edit(http_request.user, request_obj):
                raise PermissionDenied()
            if request_obj.state != CommunicationRequest.State.DRAFT or request_obj.version != version:
                raise Conflict()
            existing = request_obj.acts.filter(request_version=version).first()
            if existing:
                return existing
            act = ActVersion.objects.create(request=request_obj, request_version=version, mode=request_obj.mode, imported_document=imported, storage_name=storage_name, sha256=digest, prepared_by=http_request.user)
            record(http_request, action="request.act.prepared", unit=request_obj.unit, resource=request_obj.case, details={"request_id": str(request_obj.pk), "act_id": str(act.pk), "sha256": digest})
            return act
    except IntegrityError:
        # Two identical preparations may race on the unique request/version key.
        existing = request_obj.acts.filter(request_version=version).first()
        if existing and existing.imported_document_id == (imported.pk if imported else None):
            return existing
        raise
    finally:
        if path is not None and not ActVersion.objects.filter(storage_name=storage_name).exists():
            path.unlink(missing_ok=True)


def act_file(act):
    path = _verified_path(act.imported_document) if act.imported_document_id else act_path(act.storage_name)
    try:
        if hashlib.sha256(path.read_bytes()).hexdigest() != act.sha256:
            raise DependencyUnavailable()
    except OSError:
        raise DependencyUnavailable()
    return path


def _transition(http_request, request_obj, *, version, before, after, kind, act=None, comment="", proof=None, factual_at=None):
    if CommunicationRequest.objects.filter(pk=request_obj.pk, state=before, version=version).update(state=after, version=version + 1, updated_at=timezone.now()) != 1:
        raise Conflict()
    event = RequestEvent.objects.create(request=request_obj, kind=kind, actor=http_request.user, act=act, comment=comment, proof=proof, factual_at=factual_at, version=version + 1)
    record(http_request, action=f"request.{kind}", unit=request_obj.unit, resource=request_obj.case, details={"request_id": str(request_obj.pk), "event_id": str(event.pk), "version": version + 1})
    request_obj.refresh_from_db()
    return request_obj


def submit(http_request, request_obj, version):
    with transaction.atomic():
        if not _can_edit(http_request.user, request_obj):
            raise PermissionDenied()
        act = request_obj.acts.filter(request_version=version).first()
        if act is None:
            raise ValidationError({"act": ["Préparez l'acte de cette version."]})
        act_file(act)
        return _transition(http_request, request_obj, version=version, before=CommunicationRequest.State.DRAFT, after=CommunicationRequest.State.SUBMITTED, kind="submitted", act=act)


def validate(http_request, request_obj, version):
    with transaction.atomic():
        if not can(http_request.user, "request.validate", request_obj) or http_request.user.pk == request_obj.author_id:
            raise PermissionDenied()
        act = request_obj.events.filter(kind="submitted").last()
        if act is None:
            raise Conflict()
        return _transition(http_request, request_obj, version=version, before=CommunicationRequest.State.SUBMITTED, after=CommunicationRequest.State.VALIDATED, kind="validated", act=act.act)


def return_request(http_request, request_obj, version, comment):
    with transaction.atomic():
        if not can(http_request.user, "request.validate", request_obj) or http_request.user.pk == request_obj.author_id:
            raise PermissionDenied()
        return _transition(http_request, request_obj, version=version, before=CommunicationRequest.State.SUBMITTED, after=CommunicationRequest.State.DRAFT, kind="returned", comment=comment)


def sign(http_request, request_obj, version, proof, signed_at):
    with transaction.atomic():
        if not can(http_request.user, "request.sign", request_obj):
            raise PermissionDenied()
        document = _document(request_obj.case, proof, pdf=True)
        _verified_path(document)
        submitted = request_obj.events.filter(kind="submitted").last()
        if submitted is None:
            raise Conflict()
        return _transition(http_request, request_obj, version=version, before=CommunicationRequest.State.VALIDATED, after=CommunicationRequest.State.SIGNED, kind="signed", act=submitted.act, proof=document, factual_at=signed_at)


def issue(http_request, request_obj, version, key, dispatch_proof, sent_at):
    with transaction.atomic():
        if not can(http_request.user, "request.issue", request_obj):
            raise PermissionDenied()
        existing = RequestIssuance.objects.filter(request=request_obj).first()
        if existing:
            if existing.idempotency_key == key and existing.issued_by_id == http_request.user.pk and existing.dispatch_proof_id == dispatch_proof and existing.issued_at == sent_at:
                request_obj.refresh_from_db()
                return request_obj
            raise Conflict()
        document = _document(request_obj.case, dispatch_proof, pdf=True)
        _verified_path(document)
        signed = request_obj.events.filter(kind="signed").last()
        if signed is None or signed.proof_id is None or signed.act_id is None:
            raise Conflict()
        if signed.factual_at and sent_at < signed.factual_at:
            raise ValidationError({"sent_at": ["L'envoi précède la signature constatée."]})
        act_file(signed.act)
        result = _transition(http_request, request_obj, version=version, before=CommunicationRequest.State.SIGNED, after=CommunicationRequest.State.ISSUED, kind="issued", act=signed.act, proof=document, factual_at=sent_at)
        RequestIssuance.objects.create(request=request_obj, act=signed.act, signature_proof=signed.proof, dispatch_proof=document, idempotency_key=key, issued_by=http_request.user, issued_at=sent_at)
        return result


def create_response(http_request, request_obj, data):
    if not _can_record(http_request.user, request_obj):
        raise PermissionDenied()
    with transaction.atomic():
        letter = _document(request_obj.case, data["letter"])
        annex_ids = data["annexes"]
        if len(set(annex_ids)) != len(annex_ids) or letter.pk in annex_ids:
            raise ValidationError({"annexes": ["Pièces distinctes requises."]})
        annexes = [_document(request_obj.case, value) for value in annex_ids]
        item_ids = data["item_ids"]
        if len(set(item_ids)) != len(item_ids):
            raise ValidationError({"item_ids": ["Éléments distincts requis."]})
        items = list(request_obj.items.filter(pk__in=item_ids))
        if len(items) != len(item_ids):
            raise ValidationError({"item_ids": ["Élément de la demande requis."]})
        complement = None
        if "complement_of" in data:
            complement = request_obj.responses.filter(pk=data["complement_of"]).first()
            if complement is None:
                raise ValidationError({"complement_of": ["Réponse de la demande requise."]})
        response = RequestResponse.objects.create(request=request_obj, letter=letter, received_on=data["received_on"], recorded_by=http_request.user, complement_of=complement)
        response.annexes.set(annexes)
        ResponseItemLink.objects.bulk_create([ResponseItemLink(response=response, item=item, added_by=http_request.user) for item in items])
        record(http_request, action="request.response.received", unit=request_obj.unit, resource=request_obj.case, details={"request_id": str(request_obj.pk), "response_id": str(response.pk), "received_on": str(response.received_on)})
        return response


def rectify_links(http_request, response, data):
    request_obj = response.request
    if not _can_record(http_request.user, request_obj):
        raise PermissionDenied()
    with transaction.atomic():
        version = data["version"]
        if RequestResponse.objects.filter(pk=response.pk, version=version).update(version=version + 1) != 1:
            raise Conflict()
        removals = list(response.item_links.filter(pk__in=data["remove_link_ids"], voided_at__isnull=True))
        if len(removals) != len(set(data["remove_link_ids"])):
            raise ValidationError({"remove_link_ids": ["Lien actif requis."]})
        additions = list(request_obj.items.filter(pk__in=data["add_item_ids"]))
        if len(additions) != len(set(data["add_item_ids"])):
            raise ValidationError({"add_item_ids": ["Élément de la demande requis."]})
        active = set(response.item_links.filter(voided_at__isnull=True).values_list("item_id", flat=True)) - {link.item_id for link in removals}
        if len(data["add_item_ids"]) != len(set(data["add_item_ids"])) or active.intersection(data["add_item_ids"]):
            raise ValidationError({"add_item_ids": ["Lien déjà actif ou dupliqué."]})
        for link in removals:
            link.voided_by = http_request.user
            link.voided_at = timezone.now()
            link.reason = data["reason"]
            link.save(update_fields=["voided_by", "voided_at", "reason"])
        ResponseItemLink.objects.bulk_create([ResponseItemLink(response=response, item=item, added_by=http_request.user, reason=data["reason"]) for item in additions])
        record(http_request, action="request.response.links.rectified", unit=request_obj.unit, resource=request_obj.case, details={"response_id": str(response.pk), "version": version + 1})
    response.refresh_from_db()
    return response


def assess_item(http_request, item, data):
    request_obj = item.request
    if not _can_record(http_request.user, request_obj):
        raise PermissionDenied()
    with transaction.atomic():
        has_response = item.response_links.filter(voided_at__isnull=True).exists()
        if data["receipt"] == ItemAssessment.Receipt.RECEIVED and not has_response:
            raise ValidationError({"receipt": ["Aucune réponse liée à cet élément."]})
        if data["receipt"] == ItemAssessment.Receipt.NOT_RECEIVED and has_response:
            raise ValidationError({"receipt": ["Une réponse est liée à cet élément."]})
        version = data["version"]
        if RequestedItem.objects.filter(pk=item.pk, assessment_version=version).update(assessment_version=version + 1) != 1:
            raise Conflict()
        assessment = ItemAssessment.objects.create(item=item, version=version + 1, receipt=data["receipt"], completeness=data["completeness"], substance=data["substance"], reason=data["reason"], actor=http_request.user)
        record(http_request, action="request.item.assessed", unit=request_obj.unit, resource=request_obj.case, details={"request_id": str(request_obj.pk), "item_id": str(item.pk), "version": version + 1})
        return assessment
