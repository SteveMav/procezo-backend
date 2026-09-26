"""Measure authorized case search and opening from a pilot network workstation."""

import argparse
import http.cookiejar
import json
import math
import os
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[math.ceil(len(ordered) * fraction) - 1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="URL HTTPS du site pilote, sans /api/v1")
    parser.add_argument("reference", help="Référence du dossier fictif mesuré")
    parser.add_argument("case_id", help="UUID du même dossier")
    parser.add_argument("--samples", type=int, default=50)
    parser.add_argument("--output", type=Path, help="Nouveau fichier JSON pour le compte rendu")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    if not base.startswith("https://") and not base.startswith("http://localhost") and not base.startswith("http://127.0.0.1"):
        parser.error("HTTPS requis hors du poste local.")
    if not 5 <= args.samples <= 1000:
        parser.error("--samples doit être compris entre 5 et 1000.")
    try:
        args.case_id = str(uuid.UUID(args.case_id))
    except ValueError:
        parser.error("case_id doit être un UUID.")
    if args.output and args.output.exists():
        parser.error("Le fichier de compte rendu doit être nouveau.")
    username, password = os.environ.get("PROCEZO_PILOT_USERNAME"), os.environ.get("PROCEZO_PILOT_PASSWORD")
    if not username or not password:
        parser.error("PROCEZO_PILOT_USERNAME et PROCEZO_PILOT_PASSWORD sont requis.")
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    session = f"{base}/api/v1/session/"

    def fetch(url, *, data=None, headers=None):
        request = urllib.request.Request(url, data=data, headers={"Connection": "close", **(headers or {})})
        try:
            with opener.open(request, timeout=15) as response:
                payload = bytearray()
                decoder = json.JSONDecoder()
                while len(payload) < 1024 * 1024:
                    chunk = response.read1(64 * 1024)
                    if not chunk:
                        break
                    payload.extend(chunk)
                    try:
                        body, end = decoder.raw_decode(payload.decode("utf-8"))
                        if not payload.decode("utf-8")[end:].strip():
                            return response.status, body
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                raise ValueError("Réponse JSON absente ou trop volumineuse.")
        except (urllib.error.URLError, ValueError) as exc:
            raise RuntimeError("Requête pilote échouée ; vérifier le réseau, l'API et le compte de mesure.") from exc

    fetch(session)
    csrf = next((cookie.value for cookie in jar if cookie.name == "csrftoken"), None)
    if not csrf:
        raise RuntimeError("Cookie CSRF absent.")
    status, body = fetch(session, data=json.dumps({"username": username, "password": password}).encode(), headers={"Content-Type": "application/json", "X-CSRFToken": csrf, "Origin": base})
    if status != 200 or body.get("authenticated") is not True:
        raise RuntimeError("Authentification pilote refusée.")
    search_url = f"{base}/api/v1/dossiers/?{urllib.parse.urlencode({'reference': args.reference, 'page_size': 20})}"
    detail_url = f"{base}/api/v1/dossiers/{args.case_id}/"
    timings = {"search_ms": [], "open_ms": []}
    for index in range(args.samples + 3):
        for key, url in (("search_ms", search_url), ("open_ms", detail_url)):
            started = time.perf_counter()
            status, body = fetch(url)
            elapsed = (time.perf_counter() - started) * 1000
            if status != 200:
                raise RuntimeError(f"Réponse inattendue pour {key}: {status}.")
            if key == "search_ms" and not any(row.get("id") == args.case_id for row in body.get("results", [])):
                raise RuntimeError("Le dossier attendu est absent de la recherche autorisée.")
            if key == "open_ms" and body.get("id") != args.case_id:
                raise RuntimeError("La fiche ouverte ne correspond pas au dossier de mesure.")
            if index >= 3:
                timings[key].append(elapsed)
    report = {
        "measured_at": datetime.now(timezone.utc).isoformat(), "base_url": base,
        "reference": args.reference, "case_id": args.case_id, "samples_per_operation": args.samples,
        "search": {"p50_ms": round(statistics.median(timings["search_ms"]), 1), "p95_ms": round(percentile(timings["search_ms"], .95), 1), "target_ms": 3000},
        "open": {"p50_ms": round(statistics.median(timings["open_ms"]), 1), "p95_ms": round(percentile(timings["open_ms"], .95), 1), "target_ms": 5000},
    }
    report["search"]["target_met"] = report["search"]["p95_ms"] <= 3000
    report["open"]["target_met"] = report["open"]["p95_ms"] <= 5000
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(rendered + "\n")
        os.chmod(args.output, 0o600)
    print(rendered)


if __name__ == "__main__":
    main()
