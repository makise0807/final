from __future__ import annotations

from typing import Any

from ..adapters.satellite_tools import acquire_satellite_preview
from ..user_data.user_data_rag import answer_user_data_question, search_user_data
from .pack_registry import load_pack
from .report_templates import build_pack_report


def _analysis_text(pack: dict[str, Any], user_request: str, satellite_evidence: dict[str, Any], user_rag: dict[str, Any]) -> dict[str, Any]:
    sat = satellite_evidence.get("reason") or satellite_evidence.get("match_strategy") or "satellite context unavailable"
    rag = "No user data available." if not user_rag.get("results") else f"Retrieved {len(user_rag.get('results') or [])} user-data evidence items."
    return {
        "domain_observations": f"{pack.get('title')} processed request '{user_request}'. Satellite context: {sat}. User data: {rag}",
        "risks_opportunities": "Deterministic template output only; verify with domain review before external use.",
        "limitations": [
            "Deterministic domain template only.",
            "Not a formal satellite analysis.",
            "No formal legal conclusion.",
        ],
        "next_actions": [
            "Review satellite evidence and citations manually.",
            "Verify any operational decision with domain experts or field evidence.",
        ],
    }


def run_pack(pack_id: str, user_request: str, inputs: dict[str, Any] | None = None, mode: str = "safe_run") -> dict[str, Any]:
    inputs = dict(inputs or {})
    loaded = load_pack(pack_id)
    if not loaded.get("success"):
        return loaded
    pack = dict(loaded["pack"])
    satellite_evidence = acquire_satellite_preview(
        aoi=inputs.get("aoi") or inputs.get("bbox"),
        bbox=inputs.get("bbox"),
        case_id=str(inputs.get("case_id") or ""),
        workflow_id=str(inputs.get("workflow_id") or ""),
        mode="prepare_only" if mode == "dry_run" else "cache_only",
    )
    dataset_ids = [str(item) for item in list(inputs.get("dataset_ids") or [])]
    user_rag = search_user_data(pack["pack_id"], user_request, dataset_ids=dataset_ids, top_k=5)
    rag_answer = answer_user_data_question(pack["pack_id"], user_request, dataset_ids=dataset_ids, top_k=3)
    analysis = _analysis_text(pack, user_request, satellite_evidence, user_rag)
    report = build_pack_report(pack, user_request, inputs, satellite_evidence, user_rag, analysis)
    status = "degraded" if satellite_evidence.get("status") == "degraded" or user_rag.get("status") == "degraded" else "success"
    return {
        "success": True,
        "pack_id": pack["pack_id"],
        "title": pack.get("title"),
        "title_zh": pack.get("title_zh"),
        "status": status,
        "mode": mode,
        "satellite_evidence": satellite_evidence,
        "user_rag": user_rag,
        "analysis": analysis,
        "report": report,
        "rag_answer": rag_answer,
        "warnings": list(dict.fromkeys([*(satellite_evidence.get("warnings") or []), *(user_rag.get("warnings") or []), *(rag_answer.get("warnings") or [])])),
        "limitations": list(dict.fromkeys([*(satellite_evidence.get("limitations") or []), *(user_rag.get("limitations") or []), *(analysis.get("limitations") or [])])),
    }
