from __future__ import annotations

from typing import Any

from ..adapters.rag_tools import search_regulations
from ..adapters.satellite_tools import acquire_satellite_preview
from ..legal_grounding import build_applicability_check, build_legal_report_sections
from ..openeo_acquisition import create_openeo_acquisition_plan
from ..production import append_audit_log, calculate_readiness_score, create_run_manifest
from ..user_data.user_data_rag import answer_user_data_question, search_user_data
from .pack_registry import load_pack
from .report_templates import build_pack_report


PACK_ANALYSIS_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "real_estate_insight": {
        "observations": [
            "Surrounding environment should be reviewed together with parcel and access context.",
            "Green and open-space cues may support amenity-oriented evaluation.",
            "Road and access observations remain preliminary without field validation.",
            "Buyer risk should be framed as a checklist, not a transaction conclusion.",
            "Sales angle should be grounded in observable context rather than legal claims.",
        ],
        "risks": ["Satellite context may not reflect parcel-level use or legal status."],
        "opportunities": ["Visible open-space and access context can support a structured buyer briefing."],
        "next_actions": ["Verify parcel status, access, and nearby land-use conditions with official records."],
    },
    "geo_classroom": {
        "observations": [
            "Learning objective should focus on reading land patterns from satellite imagery.",
            "Observation questions can ask students to compare land cover and access routes.",
            "Student worksheet items should separate observation from interpretation.",
            "Teacher notes should flag uncertainty and missing metadata.",
            "Extension activities can connect imagery to maps, regulations, and field notes.",
        ],
        "risks": ["Classroom interpretation may overreach if treated as factual land-use proof."],
        "opportunities": ["The pack can support place-based learning with grounded visual evidence."],
        "next_actions": ["Pair the preview with maps, discussion prompts, and local reference materials."],
    },
    "public_inspection": {
        "observations": [
            "Suspicious indicators should remain preliminary until field verification.",
            "Inspection priority can be ranked from visible anomalies and missing facts.",
            "A field verification checklist should be prepared before any enforcement step.",
            "Required evidence should include official records, permits, and site photos.",
            "Limitation statements should explain that imagery alone is insufficient.",
        ],
        "risks": ["Public-inspection use carries legal and evidentiary sensitivity."],
        "opportunities": ["The pack can help organize field-inspection preparation."],
        "next_actions": ["Collect records, confirm jurisdiction, and schedule field verification if needed."],
    },
    "agriculture_monitor": {
        "observations": [
            "Vegetation and land-use observation should stay at broad screening level.",
            "Bare land or field-pattern changes can be flagged as monitoring cues.",
            "Crop stress hints require temporal comparison or field agronomy input.",
            "Monitoring interval should be adapted to season and crop cycle.",
            "Farmer or agency next actions should focus on verification and follow-up imagery.",
        ],
        "risks": ["Single-scene imagery cannot confirm crop health or causality."],
        "opportunities": ["Repeated preview checks can support monitoring workflows."],
        "next_actions": ["Add date-series imagery and local field observations for stronger review."],
    },
    "disaster_rapid_scan": {
        "observations": [
            "Possible affected areas should be framed as rapid-screening hints.",
            "Road and access concerns can be highlighted for follow-up routing.",
            "Flood or landslide hints need corroboration from official disaster data.",
            "Priority check zones should be sorted by accessibility and visible anomaly.",
            "Response checklist should emphasize safety and multi-source confirmation.",
        ],
        "risks": ["Rapid-scan imagery may lag behind on-the-ground disaster conditions."],
        "opportunities": ["The pack can support early prioritization of verification zones."],
        "next_actions": ["Combine with official disaster feeds and field-response updates."],
    },
    "esg_environment": {
        "observations": [
            "Environmental context should be summarized with clear uncertainty notes.",
            "Land-change notes should avoid implying regulatory breach by default.",
            "Green, water, and open-space cues can inform ESG narrative framing.",
            "ESG disclosure hints should point to follow-up evidence needs.",
            "Risk caveats should state that satellite context is not an ESG audit.",
        ],
        "risks": ["ESG interpretation can be overstated without supporting disclosures and records."],
        "opportunities": ["The pack can structure an early ESG environmental context note."],
        "next_actions": ["Pair imagery with disclosures, permits, and site-specific documentation."],
    },
    "outdoor_safety": {
        "observations": [
            "Terrain context should be described conservatively.",
            "Water and slope proximity can signal review points for route safety.",
            "Access route notes should remain tentative until local confirmation.",
            "Possible hazards should be framed as situational alerts, not determinations.",
            "Safety disclaimers should emphasize on-site judgment and official advisories.",
        ],
        "risks": ["Outdoor risk can change faster than cached or preview imagery."],
        "opportunities": ["The pack can provide a structured pre-trip review checklist."],
        "next_actions": ["Check local advisories, weather, and route conditions before travel."],
    },
    "media_investigation": {
        "observations": [
            "Visual observations should be separated from narrative claims.",
            "Timeline hints need date-aware corroboration from other sources.",
            "Evidence checklist should include records, interviews, and on-site materials.",
            "Verification questions should remain open-ended and grounded.",
            "Source caveats should explain image, metadata, and legal limits.",
        ],
        "risks": ["Media use increases reputational and evidentiary sensitivity."],
        "opportunities": ["The pack can help build a disciplined verification workflow."],
        "next_actions": ["Cross-check imagery with records, witnesses, and field reporting."],
    },
    "urban_planning": {
        "observations": [
            "Current land-use context should be read as a spatial snapshot.",
            "Development opportunity notes should be conditional on planning rules.",
            "Transportation and open-space context can support planning discussion.",
            "Constraint hints should point to zoning, access, and environmental review.",
            "Planning next steps should emphasize official plan and permit checks.",
        ],
        "risks": ["Urban-planning interpretation requires authoritative land-use data."],
        "opportunities": ["The pack can frame early-stage planning questions."],
        "next_actions": ["Review planning maps, zoning text, and infrastructure constraints."],
    },
    "climate_land_change": {
        "observations": [
            "Change observation should focus on visible land-cover pattern shifts.",
            "Land-cover hints should avoid overclaiming causality from one scene.",
            "Environmental indicators should be positioned as research prompts.",
            "Research questions should identify what temporal or field data is missing.",
            "Monitoring recommendations should prioritize repeatable follow-up methods.",
        ],
        "risks": ["Climate and land-change claims need multi-temporal evidence."],
        "opportunities": ["The pack can support research-style screening and documentation."],
        "next_actions": ["Add time-series imagery and external datasets before drawing stronger conclusions."],
    },
}


def _satellite_status(satellite_evidence: dict[str, Any]) -> str:
    return str(satellite_evidence.get("status") or satellite_evidence.get("match_strategy") or "satellite_context_unavailable")


def _build_analysis(pack: dict[str, Any], satellite_evidence: dict[str, Any], user_rag: dict[str, Any]) -> dict[str, Any]:
    template = PACK_ANALYSIS_TEMPLATES.get(str(pack.get("pack_id") or ""), {})
    observations = list(template.get("observations") or [])
    risks = list(template.get("risks") or [])
    opportunities = list(template.get("opportunities") or [])
    next_actions = list(template.get("next_actions") or [])
    observations.append(f"Satellite status: {_satellite_status(satellite_evidence)}.")
    if user_rag.get("status") == "ok":
        observations.append(f"User data contributed {len(user_rag.get('hits') or [])} grounded evidence hits.")
    else:
        risks.append("No imported user data was available, so user-data evidence remains absent.")
        next_actions.append("Import runtime user data if the pack needs project-specific evidence.")
    return {
        "observations": observations[:8],
        "risks": list(dict.fromkeys(risks)),
        "opportunities": list(dict.fromkeys(opportunities)),
        "next_actions": list(dict.fromkeys(next_actions)),
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
        workflow_id=str(inputs.get("workflow_id") or pack_id),
        mode="prepare_only" if mode == "dry_run" else "cache_only",
    )
    dataset_ids = [str(item) for item in list(inputs.get("dataset_ids") or []) if str(item).strip()]
    user_rag = search_user_data(
        pack["pack_id"],
        user_request,
        dataset_ids=dataset_ids,
        top_k=5,
        collection_name=str(pack.get("user_data_collection") or ""),
    )
    rag_answer = answer_user_data_question(
        pack["pack_id"],
        user_request,
        dataset_ids=dataset_ids,
        top_k=3,
        collection_name=str(pack.get("user_data_collection") or ""),
    )
    system_legal_rag = search_regulations(user_request or pack_id, top_k=3)
    legal_grounding = build_applicability_check(
        user_request=user_request,
        workflow_id=str(inputs.get("workflow_id") or ""),
        pack_id=pack["pack_id"],
        facts=inputs,
    )
    legal_sections = build_legal_report_sections(legal_grounding)
    openeo_acquisition = None
    if inputs.get("require_geotiff"):
        openeo_acquisition = create_openeo_acquisition_plan(
            inputs.get("aoi") or inputs.get("bbox"),
            dict(inputs.get("date_range") or {}),
            [str(item) for item in list(inputs.get("bands") or ["B04", "B03", "B02", "B08"])],
            int(inputs.get("resolution") or 10),
        )
    analysis = _build_analysis(pack, satellite_evidence, user_rag)
    report = build_pack_report(
        pack,
        user_request,
        inputs,
        satellite_evidence,
        user_rag,
        analysis,
        legal_grounding=legal_grounding,
        system_legal_rag=system_legal_rag,
        legal_sections=legal_sections,
        openeo_acquisition=openeo_acquisition,
    )

    degraded_reasons: list[str] = []
    if satellite_evidence.get("status") == "degraded":
        degraded_reasons.append("satellite_evidence_degraded")
    if user_rag.get("status") != "ok":
        degraded_reasons.append(str(user_rag.get("status") or "user_rag_degraded"))

    warnings = list(dict.fromkeys([*(satellite_evidence.get("warnings") or []), *(user_rag.get("warnings") or []), *(rag_answer.get("warnings") or [])]))
    limitations = list(
        dict.fromkeys(
            [
                *(satellite_evidence.get("limitations") or []),
                *(user_rag.get("limitations") or []),
                "Deterministic domain template only.",
                "Not a formal satellite analysis.",
                "No formal legal conclusion.",
            ]
        )
    )
    next_actions = list(dict.fromkeys(analysis.get("next_actions") or []))

    result = {
        "success": True,
        "pack_id": pack["pack_id"],
        "title": pack.get("title"),
        "title_zh": pack.get("title_zh"),
        "status": "degraded" if degraded_reasons else "success",
        "mode": mode,
        "inputs": inputs,
        "satellite_evidence": satellite_evidence,
        "user_rag": user_rag,
        "system_legal_rag": system_legal_rag,
        "legal_grounding": legal_grounding,
        "openeo_acquisition": openeo_acquisition,
        "analysis": analysis,
        "report": report,
        "rag_answer": rag_answer,
        "warnings": warnings,
        "limitations": limitations,
        "next_actions": next_actions,
    }
    result["production_readiness"] = calculate_readiness_score()
    result["run_manifest"] = create_run_manifest(result)
    if openeo_acquisition:
        result["approval_required_actions"] = ["openeo_submit", "geotiff_download"]
        result["warnings"] = list(dict.fromkeys(list(result["warnings"]) + ["GeoTIFF acquisition requires explicit approval."]))
        result["limitations"] = list(dict.fromkeys(list(result["limitations"]) + ["OpenEO submit/download is approval-gated and disabled by default."]))
    try:
        append_audit_log(
            {
                "action": "pack_run",
                "handler": "pack_runner",
                "run_id": result["run_manifest"].get("run_id"),
                "approved_actions": [],
                "external_fetch": False,
                "generated_artifacts": result["run_manifest"].get("artifacts"),
                "errors": [],
            }
        )
    except Exception:
        pass
    return result
