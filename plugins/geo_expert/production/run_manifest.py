from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from .provenance import collect_data_provenance


def create_run_manifest(result: dict[str, Any]) -> dict[str, Any]:
    run_id = str(result.get("run_id") or uuid.uuid4().hex[:12])
    openeo = dict(result.get("openeo_acquisition") or {})
    services = {
        "chromadb": any((step.get("adapter") == "rag" and (step.get("used_real_service") or (step.get("evidence") or {}).get("selected_collection"))) for step in result.get("steps") or []),
        "postgis": any((step.get("adapter") == "spatial" and step.get("used_real_service")) for step in result.get("steps") or []),
        "satellite": bool(result.get("satellite_evidence")),
        "detector": any(step.get("adapter") == "detector" for step in result.get("steps") or []),
        "legal_grounding": bool(result.get("legal_grounding")),
        "openeo": bool(openeo.get("submitted")),
    }
    artifacts = []
    for key in ("report_path", "result_path", "result_json_path"):
        if result.get(key):
            artifacts.append({"artifact_type": key, "path": str(result.get(key))})
    for item in openeo.get("artifacts") or []:
        artifacts.append(item)
    return {
        "success": True,
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "workflow_id": result.get("workflow_id"),
        "pack_id": result.get("pack_id"),
        "mode": result.get("mode"),
        "inputs_summary": dict(result.get("inputs") or {}),
        "services_used": services,
        "data_sources": collect_data_provenance(result),
        "artifacts": artifacts,
        "warnings": list(result.get("warnings") or []),
        "limitations": list(result.get("limitations") or []),
        "approval_required": list(result.get("approval_required_steps") or []) + list(result.get("approval_required_actions") or []),
        "reproducibility": {
            "deterministic_templates": True,
            "requires_human_review": bool(result.get("legal_grounding") or result.get("human_review_required")),
            "report_formality_level": result.get("report", {}).get("formality_level") if isinstance(result.get("report"), dict) else None,
        },
    }
