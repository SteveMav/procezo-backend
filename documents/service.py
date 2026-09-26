import hashlib
import os
import subprocess
import uuid
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.exceptions import PermissionDenied

from audit.service import record
from identity.policy import can
from platform_api.errors import DependencyUnavailable

from .models import Document, FileOperation


MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_DOCUMENTS_PER_PARENT = 20
TYPES = {"application/pdf": b"%PDF-", "image/png": b"\x89PNG\r\n\x1a\n", "image/jpeg": b"\xff\xd8\xff"}


def private_path(storage_name):
    root = Path(settings.PROCEZO_PRIVATE_FILES_ROOT)
    return root / "quarantine" / str(storage_name)


def scan(path):
    scanner = settings.PROCEZO_CLAMSCAN_PATH
    if not scanner:
        return "unavailable"
    try:
        result = subprocess.run([scanner, "--no-summary", str(path)], capture_output=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"
    return {0: "clean", 1: "infected"}.get(result.returncode, "unavailable")


def _write_upload(upload, path):
    digest = hashlib.sha256()
    size = 0
    header = b""
    try:
        with path.open("xb") as output:
            for chunk in upload.chunks():
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise ValidationError({"file": ["Fichier trop volumineux."]})
                if len(header) < 8:
                    header = (header + chunk)[:8]
                digest.update(chunk)
                output.write(chunk)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    content_type = next((name for name, magic in TYPES.items() if header.startswith(magic)), None)
    if not size or content_type is None:
        path.unlink(missing_ok=True)
        raise ValidationError({"file": ["Type de fichier non autorisé."]})
    return size, digest.hexdigest(), content_type


def upload_document(request, *, parent, upload):
    filter_arg = {"case": parent} if parent._meta.model_name == "case" else {"intelligence": parent}
    if Document.objects.filter(**filter_arg).count() >= MAX_DOCUMENTS_PER_PARENT:
        raise ValidationError({"file": ["Nombre maximal de pièces atteint."]})
    if upload.size > MAX_FILE_SIZE:
        raise ValidationError({"file": ["Fichier trop volumineux."]})
    storage_name = uuid.uuid4()
    path = private_path(storage_name)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        size, digest, content_type = _write_upload(upload, path)
    except OSError:
        raise DependencyUnavailable()
    name = Path(upload.name.replace("\\", "/")).name[:240]
    try:
        with transaction.atomic():
            parent.refresh_from_db()
            action = "case.update" if parent._meta.model_name == "case" else "source.write"
            if not can(request.user, action, parent):
                raise PermissionDenied()
            occupied = set(Document.objects.filter(**filter_arg).values_list("slot", flat=True))
            slot = next((value for value in range(1, MAX_DOCUMENTS_PER_PARENT + 1) if value not in occupied), None)
            if slot is None:
                raise ValidationError({"file": ["Nombre maximal de pièces atteint."]})
            document = Document.objects.create(**filter_arg, slot=slot, original_name=name, content_type=content_type, size=size, sha256=digest, storage_name=storage_name, uploaded_by=request.user)
            FileOperation.objects.create(document=document, kind="upload", result="quarantine")
            record(request, action="document.uploaded", unit=parent.unit, resource=parent, details={"document_id": str(document.pk), "sha256": digest})
    except IntegrityError:
        path.unlink(missing_ok=True)
        raise ValidationError({"file": ["Dépôt concurrent ; réessayez."]})
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return rescan_document(request, document)


def rescan_document(request, document):
    if document.state in {Document.State.ACCEPTED, Document.State.REJECTED}:
        return document
    path = private_path(document.storage_name)
    if not path.is_file():
        result = "missing"
    else:
        try:
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            result = scan(path) if digest.hexdigest() == document.sha256 else "missing"
        except OSError:
            result = "missing"
    state = {"clean": Document.State.ACCEPTED, "infected": Document.State.REJECTED, "missing": Document.State.MISSING, "unavailable": Document.State.QUARANTINE}[result]
    parent = document.parent
    with transaction.atomic():
        parent.refresh_from_db()
        action = "case.update" if parent._meta.model_name == "case" else "source.write"
        if not can(request.user, action, parent):
            raise PermissionDenied()
        # A previously accepted or rejected result is final for this immutable upload.
        changed = Document.objects.filter(pk=document.pk, state__in=[Document.State.QUARANTINE, Document.State.MISSING]).update(state=state, scanned_at=timezone.now() if result in {"clean", "infected"} else None)
        if changed:
            FileOperation.objects.create(document=document, kind="scan", result=result)
            record(request, action="document.scanned", unit=parent.unit, resource=parent, details={"document_id": str(document.pk), "result": result})
        document.refresh_from_db()
    if result == "infected":
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    return document
