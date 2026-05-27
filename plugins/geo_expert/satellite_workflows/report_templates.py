from __future__ import annotations

from typing import Any


def _user_data_summary(user_rag: dict[str, Any]) -> dict[str, Any]:
    if user_rag.get("status") == "ok":
        return {
            "status": "ok",
            "collection": user_rag.get("collection"),
            "dataset_ids": user_rag.get("dataset_ids") or [],
            "citations": user_rag.get("citations") or [],
            "summary": f"Retrieved {len(user_rag.get('hits') or [])} user-data evidence hits.",
        }
    return {
        "status": user_rag.get("status") or "no_user_data_available",
        "collection": user_rag.get("collection"),
        "dataset_ids": user_rag.get("dataset_ids") or [],
        "citations": [],
        "summary": "No user data was provided, so this section relies on system and satellite evidence only.",
    }


def build_pack_report(
    pack: dict[str, Any],
    user_request: str,
    inputs: dict[str, Any],
    satellite_evidence: dict[str, Any],
    user_rag: dict[str, Any],
    analysis: dict[str, Any],
    *,
    legal_grounding: dict[str, Any] | None = None,
    system_legal_rag: dict[str, Any] | None = None,
    legal_sections: dict[str, Any] | None = None,
    openeo_acquisition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    legal_grounding = dict(legal_grounding or {})
    system_legal_rag = dict(system_legal_rag or {})
    legal_sections = dict(legal_sections or {})
    evidence_matrix = {
        "satellite_evidence": satellite_evidence,
        "user_data_evidence": _user_data_summary(user_rag),
        "legal_citation_evidence": legal_grounding.get("citations") or [],
        "spatial_evidence": inputs.get("spatial_evidence") or {},
    }
    sections = [
        {"heading": "Purpose", "content": pack.get("title_zh") or pack.get("title")},
        {"heading": "Input Summary", "content": {"user_request": user_request, "inputs": inputs}},
        {"heading": "Satellite Evidence", "content": satellite_evidence},
        {"heading": "User Data Evidence", "content": _user_data_summary(user_rag)},
        {"heading": "Domain Observations", "content": analysis.get("observations") or []},
        {"heading": "Legal Basis", "content": legal_sections.get("Legal Basis") or []},
        {"heading": "Applicability Checklist", "content": legal_sections.get("Applicability Checklist") or []},
        {"heading": "Evidence Matrix", "content": evidence_matrix},
        {"heading": "Production Readiness", "content": "production_ready_partial"},
        {"heading": "Approval Required Actions", "content": ["GeoTIFF acquisition requires explicit approval."] if openeo_acquisition else []},
        {"heading": "Reproducibility Manifest", "content": {"deterministic_templates": True, "human_review_required": True}},
        {"heading": "Human Review Required", "content": True},
        {
            "heading": "Formality Level",
            "content": legal_sections.get("Formality Level") or ["preliminary_screening", "expert_review_draft", "not_official_decision"],
        },
        {"heading": "Risks or Caveats", "content": analysis.get("risks") or []},
        {"heading": "Next Actions", "content": analysis.get("next_actions") or []},
    ]
    return {
        "title": pack.get("title"),
        "title_zh": pack.get("title_zh"),
        "pack_id": pack.get("pack_id"),
        "sections": sections,
        "report_sections": list(pack.get("report_sections") or []),
        "sections_map": {section["heading"]: section["content"] for section in sections},
        "user_request": user_request,
        "human_review_required": True,
        "formality_level": ["preliminary_screening", "expert_review_draft", "not_official_decision"],
        "system_legal_rag": system_legal_rag,
        "legal_grounding": legal_grounding,
        "openeo_acquisition": openeo_acquisition,
    }
