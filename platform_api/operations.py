"""Aggregate health signals without returning case or source data."""

import json
import shutil
from datetime import timedelta, datetime, timezone as utc
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.utils import timezone

from audit.models import AuditEvent
from documents.models import Document, FileOperation


def log_metrics(path, since):
    result = {"api_5xx": 0, "database_locked": 0, "audit_failure": 0, "pdf_5xx": 0, "request_count": 0, "tail_truncated": False}
    with Path(path).open("rb") as stream:
        stream.seek(0, 2)
        result["tail_truncated"] = stream.tell() > 10 * 1024 * 1024
        stream.seek(max(0, stream.tell() - 10 * 1024 * 1024))
        if stream.tell():
            stream.readline()
        for line in stream:
            try:
                row = json.loads(line)
                occurred = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
                if occurred < since:
                    continue
                event = row.get("event")
                if event in ("database_locked", "audit_failure"):
                    result[event] += 1
                elif event == "request":
                    result["request_count"] += 1
                    if row.get("status", 0) >= 500:
                        result["api_5xx"] += 1
                        if "preparer" in row.get("route", ""):
                            result["pdf_5xx"] += 1
            except (ValueError, KeyError, TypeError):
                continue
    return result


def health_snapshot(*, request_log=None, window_minutes=15, min_free_bytes=1024**3, max_quarantine=0, max_scan_failures=0, max_api_5xx=0, max_database_locks=0, require_log=False):
    now = timezone.now()
    since = now - timedelta(minutes=window_minutes)
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    root = Path(settings.PROCEZO_PRIVATE_FILES_ROOT)
    disk_path = root if root.exists() else root.parent
    free_bytes = shutil.disk_usage(disk_path).free
    quarantine = Document.objects.filter(state=Document.State.QUARANTINE).count()
    scan_failures = FileOperation.objects.filter(kind="scan", result="unavailable", occurred_at__gte=since).count()
    latest_audit = AuditEvent.objects.order_by("-occurred_at").values_list("occurred_at", flat=True).first()
    logs = log_metrics(request_log, since.astimezone(utc.utc)) if request_log else None
    alerts = []
    if free_bytes < min_free_bytes:
        alerts.append("disk_low")
    if quarantine > max_quarantine:
        alerts.append("quarantine_backlog")
    if scan_failures > max_scan_failures:
        alerts.append("scanner_unavailable")
    scanner = settings.PROCEZO_CLAMSCAN_PATH
    scanner_configured = bool(scanner and shutil.which(scanner))
    if not scanner_configured:
        alerts.append("scanner_unconfigured")
    if require_log and logs is None:
        alerts.append("request_log_missing")
    if logs:
        if logs["tail_truncated"]:
            alerts.append("request_log_truncated")
        if logs["api_5xx"] > max_api_5xx:
            alerts.append("api_errors")
        if logs["database_locked"] > max_database_locks:
            alerts.append("database_locks")
        if logs["audit_failure"]:
            alerts.append("audit_failure")
        if logs["pdf_5xx"]:
            alerts.append("pdf_failure")
    return {
        "checked_at": now.isoformat(), "window_minutes": window_minutes,
        "free_bytes": free_bytes, "quarantine_count": quarantine,
        "scan_failures": scan_failures, "scanner_configured": scanner_configured, "latest_audit_at": latest_audit.isoformat() if latest_audit else None,
        "requests": logs, "alerts": alerts,
    }
