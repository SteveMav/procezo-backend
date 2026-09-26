"""SQLite and private-file snapshots for a quiesced single-host installation."""

import hashlib
import json
import os
import shutil
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


FORMAT = "procezo-snapshot-v1"
TABLES = ("audit_auditevent", "documents_document", "requests_app_actversion", "requests_app_requestresponse", "inspections_sheetproject", "inspections_defense", "decisions_decision", "decisions_gelectransfer")


class SnapshotError(Exception):
    pass


def _hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files(root):
    if not root.exists():
        return []
    if not root.is_dir() or root.is_symlink():
        raise SnapshotError("Racine des pièces invalide.")
    found = []

    def fail_walk(error):
        raise error

    for parent, dirs, names in os.walk(root, followlinks=False, onerror=fail_walk):
        for name in dirs + names:
            path = Path(parent) / name
            if path.is_symlink():
                raise SnapshotError("Lien symbolique interdit dans les pièces privées.")
            if path.is_file():
                found.append(path.relative_to(root).as_posix())
    return sorted(found)


def _database_checks(db_path, files_root):
    with closing(sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise SnapshotError("Intégrité SQLite invalide.")
        if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise SnapshotError("Clés étrangères SQLite invalides.")
        counts = {}
        existing = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in TABLES:
            if table not in existing:
                raise SnapshotError(f"Table attendue absente : {table}.")
        for table in sorted(existing - {"sqlite_sequence"}):
            quoted_table = '"' + table.replace('"', '""') + '"'
            counts[table] = db.execute(f"SELECT count(*) FROM {quoted_table}").fetchone()[0]
        references = []
        for storage, digest, state in db.execute("SELECT storage_name, sha256, state FROM documents_document"):
            if state not in ("rejected", "missing"):
                references.append((f"quarantine/{uuid.UUID(storage)}", digest))
        for storage, digest in db.execute("SELECT storage_name, sha256 FROM requests_app_actversion WHERE storage_name IS NOT NULL"):
            references.append((f"acts/{uuid.UUID(storage)}", digest))
        for storage, digest in db.execute("SELECT storage_name, sha256 FROM inspections_sheetproject"):
            references.append((f"sheets/{uuid.UUID(storage)}", digest))
    for relative, digest in references:
        path = files_root / relative
        if not path.is_file() or path.is_symlink() or _hash(path) != digest:
            raise SnapshotError(f"Pièce référencée absente ou altérée : {relative}.")
    return counts, len(references)


def create_snapshot(db_path, private_root, target):
    if Path(db_path).is_symlink() or Path(private_root).is_symlink():
        raise SnapshotError("Lien symbolique interdit pour les données source.")
    db_path, private_root, target = (Path(value).resolve() for value in (db_path, private_root, target))
    if not db_path.is_file():
        raise SnapshotError("Base SQLite source absente ou invalide.")
    if target.exists() or target == private_root or private_root in target.parents or target == db_path.parent or db_path.parent in target.parents:
        raise SnapshotError("La destination doit être nouvelle et hors des données source.")
    target.mkdir(parents=True, mode=0o700)
    try:
        os.chmod(target, 0o700)
        backup_db = target / "database.sqlite3"
        with closing(sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(backup_db)) as destination:
                source.backup(destination)
        os.chmod(backup_db, 0o600)
        files_root = target / "files"
        files_root.mkdir(mode=0o700)
        entries = {}
        for relative in _files(private_root):
            source = private_root / relative
            dest = files_root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            os.chmod(dest, 0o600)
            entries[relative] = {"sha256": _hash(dest), "size": dest.stat().st_size}
        counts, references = _database_checks(backup_db, files_root)
        manifest = {"format": FORMAT, "created_at": datetime.now(timezone.utc).isoformat(), "database_sha256": _hash(backup_db), "files": entries, "counts": counts, "referenced_files": references}
        manifest_path = target / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        os.chmod(manifest_path, 0o600)
        verify_snapshot(target)
        return manifest
    except Exception:
        shutil.rmtree(target)
        raise


def verify_snapshot(source):
    source = Path(source).resolve()
    try:
        manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("format") != FORMAT:
            raise SnapshotError("Format de sauvegarde inconnu.")
        db_path, files_root = source / "database.sqlite3", source / "files"
        if db_path.is_symlink() or (source / "manifest.json").is_symlink():
            raise SnapshotError("Lien symbolique interdit dans la sauvegarde.")
        if _hash(db_path) != manifest["database_sha256"]:
            raise SnapshotError("Empreinte de la base invalide.")
        entries = manifest["files"]
        if not isinstance(entries, dict) or set(_files(files_root)) != set(entries):
            raise SnapshotError("Inventaire des pièces divergent.")
        for relative, expected in entries.items():
            path = files_root / relative
            if path.stat().st_size != expected["size"] or _hash(path) != expected["sha256"]:
                raise SnapshotError(f"Empreinte de pièce invalide : {relative}.")
        counts, references = _database_checks(db_path, files_root)
        if counts != manifest["counts"] or references != manifest["referenced_files"]:
            raise SnapshotError("Références ou nombres d'objets divergents.")
        return manifest
    except (OSError, KeyError, TypeError, ValueError, sqlite3.DatabaseError) as exc:
        raise SnapshotError("Sauvegarde illisible ou incohérente.") from exc


def restore_snapshot(source, database, private_root):
    source, database, private_root = (Path(value).resolve() for value in (source, database, private_root))
    manifest = verify_snapshot(source)
    if database.exists() or private_root.exists() or database == private_root or private_root in database.parents or database in private_root.parents or source in database.parents or source in private_root.parents:
        raise SnapshotError("Les destinations de restauration doivent être nouvelles et séparées de la sauvegarde.")
    database.parent.mkdir(parents=True, exist_ok=True)
    private_root.mkdir(parents=True, mode=0o700)
    try:
        shutil.copyfile(source / "database.sqlite3", database)
        os.chmod(database, 0o600)
        for relative in manifest["files"]:
            dest = private_root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / "files" / relative, dest)
            os.chmod(dest, 0o600)
        counts, references = _database_checks(database, private_root)
        if counts != manifest["counts"] or references != manifest["referenced_files"]:
            raise SnapshotError("Restauration incohérente.")
        return manifest
    except Exception:
        database.unlink(missing_ok=True)
        shutil.rmtree(private_root)
        raise
