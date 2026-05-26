"""Local-only audit trail for OpenEO submit request decisions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_SUBMIT_AUDIT_PATH = Path(".hermes/openeo/submit_audit.jsonl")


def write_submit_audit_event(
    *,
    event_type: str,
    request_id: str,
    preview_id: str,
    backend_url: str | None,
    capabilities_source: str,
    decision_status: str,
    reasons: list[str],
    risks: list[str],
    explicit_submit: bool | None = None,
    job_id: str | None = None,
    location: str | None = None,
    downloaded: bool | None = None,
    polling_started: bool | None = None,
    raw_response_summary: dict[str, Any] | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    audit_path = Path(path) if path is not None else DEFAULT_SUBMIT_AUDIT_PATH
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "event_type": event_type,
        "request_id": request_id,
        "preview_id": preview_id,
        "backend_url": backend_url,
        "capabilities_source": capabilities_source,
        "decision_status": decision_status,
        "reasons": list(reasons),
        "risks": list(risks),
        "explicit_submit": explicit_submit,
        "job_id": job_id,
        "location": location,
        "downloaded": downloaded,
        "polling_started": polling_started,
        "raw_response_summary": dict(raw_response_summary or {}),
        "secret_fields_present": False,
    }
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return payload
