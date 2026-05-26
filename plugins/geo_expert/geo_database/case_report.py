"""Case report builders for SOP-driven geo/legal workflows."""

from __future__ import annotations

import json
from typing import Any

try:
    from agent.local_llm_client import chat_json
except ModuleNotFoundError:
    def chat_json(*_args, **_kwargs):
        return {
            "success": True,
            "data": {
                "summary": (
                    "Standalone Geo Expert Pack fallback report. "
                    "This is a preliminary visual/legal-risk screening only."
                ),
                "draft": (
                    "This result is preliminary only, requires verification, "
                    "and is not a formal legal conclusion."
                ),
                "limitations": [
                    "Preliminary only.",
                    "Requires verification.",
                    "Not a formal legal conclusion.",
                ],
            },
            "error": None,
        }

_BASE_LIMITATIONS = [
    "temporary preview only",
    "not a formal analysis result",
    "no GeoTIFF/export/download performed",
    "OpenEO workflow remains the primary target",
]

_DEFAULT_NEXT_STEPS = [
    "Return to OpenEO workflow validation.",
    "Use GEE only as a temporary preview provider.",
    "Request authority verification or field verification before making any formal claim.",
    "Collect missing inputs before making any formal claim.",
]


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            data = value.to_dict()
            if isinstance(data, dict):
                return dict(data)
        except Exception:
            pass
    try:
        data = dict(value)
        if isinstance(data, dict):
            return dict(data)
    except Exception:
        pass
    return {}


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _as_list(*values: Any) -> list[str]:
    merged: list[str] = []
    for value in values:
        if not value:
            continue
        items = value if isinstance(value, (list, tuple, set)) else [value]
        for item in items:
            text = str(item).strip()
            if text and text not in merged:
                merged.append(text)
    return merged


def _merge_citations(*values: Any) -> list[Any]:
    merged: list[Any] = []
    for value in values:
        if not value:
            continue
        items = value if isinstance(value, (list, tuple, set)) else [value]
        for item in items:
            if isinstance(item, dict):
                if item not in merged:
                    merged.append(dict(item))
            else:
                text = _normalize_text(item)
                if text and text not in merged:
                    merged.append(text)
    return merged


def case_report_llm_draft_report(
    case_report_facts: Any,
    citations: Any | None = None,
    limitations: Any | None = None,
) -> dict[str, Any]:
    facts = _as_dict(case_report_facts)
    citation_list = _merge_citations(citations)
    limitation_list = _as_list(_BASE_LIMITATIONS, limitations)

    llm_result = chat_json(
        system_prompt=(
            "You draft a preliminary geo/legal case report from provided facts only. "
            "Do not make legal conclusions, do not claim final analysis, and do not mention downloads or exports. "
            "Use cautious wording such as preliminary, possible, suspicious, and needs verification."
        ),
        user_prompt=json.dumps(
            {"facts": facts, "citations": citation_list, "limitations": limitation_list},
            ensure_ascii=False,
            indent=2,
        ),
        schema_hint={
            "type": "object",
            "properties": {
                "draft_report": {"type": "string"},
                "safety_warnings": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["draft_report"],
        },
    )
    if llm_result.get("success") and isinstance(llm_result.get("data"), dict):
        draft = _normalize_text(llm_result["data"].get("draft_report"))
        if draft:
            return {
                "success": True,
                "draft_report": draft,
                "safety_warnings": _as_list(llm_result["data"].get("safety_warnings")),
                "fallback_used": False,
            }

    lines = [
        "Preliminary case report",
        f"Selected SOP: {facts.get('selected_sop_title') or facts.get('sop_title') or 'unknown'}",
        f"Workflow status: {facts.get('workflow_status') or 'read-only / pending approval'}",
    ]
    if citation_list:
        lines.append(f"Citations: {len(citation_list)} provided")
    lines.append("This summary is preliminary only and does not establish a formal legal conclusion.")
    return {
        "success": True,
        "draft_report": "\n".join(lines),
        "safety_warnings": [
            "Draft generated from provided facts only.",
            "No formal legal conclusion should be inferred.",
        ],
        "fallback_used": True,
    }


def build_case_report(
    selected_sop: Any,
    compiled_plan: Any,
    readonly_results: Any | None = None,
    imagery_preview_report: Any | None = None,
    legal_answer: Any | None = None,
    recognition_result: Any | None = None,
    recognition_overlay: Any | None = None,
    detection_explanation: Any | None = None,
    citations: Any | None = None,
    missing_inputs: Any | None = None,
    limitations: Any | None = None,
) -> dict[str, Any]:
    sop = _as_dict(selected_sop)
    plan = _as_dict(compiled_plan)
    readonly = _as_dict(readonly_results)
    imagery = _as_dict(imagery_preview_report)
    legal = _as_dict(legal_answer)
    recognition = _as_dict(recognition_result)
    overlay = _as_dict(recognition_overlay)
    detection_explainer = _as_dict(detection_explanation)

    sop_title = _normalize_text(sop.get("title") or sop.get("workflow_id") or "unknown SOP")
    workflow_id = _normalize_text(sop.get("workflow_id") or "unknown")
    report_citations = _merge_citations(citations, sop.get("source_citation"), readonly.get("citations"), legal.get("citations"))
    report_limitations = _as_list(_BASE_LIMITATIONS, limitations, readonly.get("limitations"))
    missing = _as_list(missing_inputs, readonly.get("missing_inputs"), plan.get("missing_inputs"))
    next_steps = _as_list(plan.get("next_steps"), readonly.get("next_steps"), _DEFAULT_NEXT_STEPS)

    draft = case_report_llm_draft_report(
        {
            "selected_sop_title": sop_title,
            "workflow_status": _as_dict(readonly.get("summary")).get("status") or plan.get("mode") or "read-only / pending approval",
            "missing_inputs": missing,
            "imagery_status": "temporary preview only" if imagery else "not yet available",
            "legal_status": "preliminary only" if legal else "not yet retrieved",
            "recognition_detection_count": _as_dict(recognition.get("overlay_summary")).get("detection_count") or 0,
            "recognition_preliminary_only": True,
        },
        citations=report_citations,
        limitations=report_limitations,
    )

    recognition_summary = _as_dict(recognition.get("overlay_summary"))
    recognition_count = int(recognition_summary.get("detection_count") or 0)
    recognition_area = float(recognition_summary.get("total_area_m2") or 0.0)
    recognition_target_classes = _as_list(recognition.get("target_classes"))
    recognition_limitations = _as_list(recognition.get("limitations"))
    recognition_detector_used = _normalize_text(recognition.get("detector_used")) or "mock"
    recognition_fallback_used = bool(recognition.get("fallback_used"))
    recognition_mode = _normalize_text(recognition.get("mode")) or "mock"
    recognition_model_name = _normalize_text(recognition.get("model_name")) or "n/a"
    recognition_model_task = _normalize_text(recognition.get("model_task")) or "n/a"
    recognition_confidences = [
        float(_as_dict(item).get("confidence") or 0.0)
        for item in recognition.get("detections") or []
        if isinstance(item, dict)
    ]
    recognition_confidence_range = (
        f"{min(recognition_confidences):.2f} - {max(recognition_confidences):.2f}"
        if recognition_confidences
        else "n/a"
    )
    legal_layer_status = (
        "available"
        if _as_dict(recognition.get("landuse_context")).get("legal_building_layer_available", False)
        else "missing"
    )

    if overlay and "GeoJSON overlay generated for safe display." not in recognition_limitations:
        recognition_limitations.append("GeoJSON overlay generated for safe display.")
    if recognition_fallback_used:
        recognition_limitations.append("The preferred detector was unavailable, so Hermes fell back to a mock preliminary overlay.")
    if recognition_detector_used == "gee_thumbnail":
        recognition_limitations.append("This result is based on thumbnail preview only and is not suitable for formal detection.")
    if recognition_detector_used == "openeo_landcover":
        recognition_limitations.append("OpenEO-derived polygons still require legal building, permit, cadastral, and field verification data.")
    if recognition_detector_used == "ultralytics_yolo":
        recognition_limitations.extend(
            [
                "YOLO pretrained model may not be trained for illegal buildings.",
                "Visual indicator only.",
                "Cadastral / permit / landuse layers required.",
                "Field verification required.",
            ]
        )

    flow_tools = [
        _normalize_text(step.get("tool"))
        for step in plan.get("steps") or []
        if isinstance(step, dict) and _normalize_text(step.get("tool"))
    ]
    flow_summary = (
        "Read-only flow: " + " -> ".join(flow_tools)
        if flow_tools
        else "Read-only SOP flow is compiled but no executable step summary is available yet."
    )

    sections = [
        {
            "title": "Task Summary",
            "content": f"SOP: {sop_title}\nWorkflow ID: {workflow_id}\nThis report is preliminary and read-only.",
        },
        {
            "title": "SOP Source",
            "content": json.dumps(sop.get("source_citation") or {}, ensure_ascii=False, indent=2),
        },
        {
            "title": "Executed Read-only Steps",
            "content": json.dumps(readonly.get("executed_steps") or [], ensure_ascii=False, indent=2),
        },
        {
            "title": "Pending Approvals",
            "content": json.dumps(readonly.get("approval_checkpoints") or plan.get("approval_checkpoints") or [], ensure_ascii=False, indent=2),
        },
        {
            "title": "EO/GIS Preliminary Flow",
            "content": flow_summary,
        },
        {
            "title": "OpenEO Workflow Status",
            "content": json.dumps(
                _as_dict(readonly.get("summary")).get("openeo")
                or plan.get("openeo_status")
                or {"primary_workflow": "openeo", "submitted": False},
                ensure_ascii=False,
                indent=2,
            ),
        },
        {
            "title": "GEE Preview Status",
            "content": json.dumps(imagery or {"status": "temporary preview only"}, ensure_ascii=False, indent=2),
        },
        {
            "title": "Image Recognition Preliminary Results",
            "content": (
                f"Detection count: {recognition_count}\n"
                f"Total suspected area (m2): {recognition_area:.2f}\n"
                f"Target classes: {', '.join(recognition_target_classes) if recognition_target_classes else 'not specified'}\n"
                f"Detector used: {recognition_detector_used}\n"
                f"Mode: {recognition_mode}\n"
                f"Model name: {recognition_model_name}\n"
                f"Model task: {recognition_model_task}\n"
                f"Fallback used: {recognition_fallback_used}\n"
                f"Confidence range: {recognition_confidence_range}\n"
                f"Legal layer status: {legal_layer_status}\n"
                "Status: preliminary detection only, requires verification.\n"
                "Interpretation: suspected areas only; not a formal legal conclusion.\n"
                "Missing legal building layer or permit data means Hermes cannot confirm a violation.\n"
                "Follow-up: field verification plus cadastral, building-permit, and authority data are still required."
            ),
        },
        {
            "title": "Detection Explanation",
            "content": _normalize_text(
                detection_explainer.get("explanation")
                or "Preliminary detection explanation is not available yet. Use detector output, legal layers, and field verification together."
            ),
        },
        {
            "title": "Legal RAG Preview",
            "content": json.dumps(legal or {"status": "preliminary only"}, ensure_ascii=False, indent=2),
        },
        {
            "title": "Missing Inputs",
            "content": ", ".join(missing) if missing else "None",
        },
        {
            "title": "Limitations",
            "content": "\n".join(_as_list(report_limitations, recognition_limitations)),
        },
        {
            "title": "Next Steps",
            "content": "\n".join(next_steps),
        },
        {
            "title": "Draft Narrative",
            "content": draft["draft_report"],
        },
    ]

    return {
        "success": True,
        "report_type": "geo_legal_preliminary_case_report",
        "title": f"Preliminary Geo/Legal Case Report: {sop_title}",
        "selected_sop": sop,
        "compiled_plan": plan,
        "readonly_results": readonly,
        "imagery_preview_report": imagery,
        "legal_answer": legal,
        "recognition_result": recognition,
        "recognition_overlay": overlay,
        "detection_explanation": detection_explainer,
        "sections": sections,
        "citations": _merge_citations(report_citations, readonly.get("citations"), legal.get("citations")),
        "limitations": _as_list(report_limitations, recognition_limitations),
        "next_steps": next_steps,
        "missing_inputs": missing,
        "safety_warnings": _as_list(draft.get("safety_warnings")),
    }


__all__ = ["build_case_report", "case_report_llm_draft_report"]
