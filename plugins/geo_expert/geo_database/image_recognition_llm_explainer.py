"""Deterministic detection explanation helper for Geo Expert Pack.

This standalone fallback does not require Hermes agent modules or a live LLM.
It produces cautious, preliminary wording for image-recognition results.
"""

from __future__ import annotations

from typing import Any


def _count_detections(recognition_result: dict[str, Any] | None) -> int:
    recognition_result = recognition_result or {}

    overlay_summary = recognition_result.get("overlay_summary") or {}
    if "detection_count" in overlay_summary:
        try:
            return int(overlay_summary.get("detection_count") or 0)
        except Exception:
            return 0

    detections = recognition_result.get("detections") or []
    if isinstance(detections, list):
        return len(detections)

    geojson = recognition_result.get("geojson") or {}
    features = geojson.get("features") or []
    if isinstance(features, list):
        return len(features)

    return 0


def llm_explain_detections(
    recognition_result: dict[str, Any] | None,
    *,
    selected_sop: dict[str, Any] | None = None,
    legal_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Explain detections using safe deterministic fallback text.

    The function name keeps compatibility with the Hermes mainline version, but
    this standalone pack implementation does not call an LLM.
    """
    recognition_result = recognition_result or {}
    selected_sop = selected_sop or {}
    legal_context = legal_context or {}

    detection_count = _count_detections(recognition_result)
    detector_used = recognition_result.get("detector_used") or "mock"
    fallback_used = bool(recognition_result.get("fallback_used", False))
    sop_title = (
        selected_sop.get("title")
        or selected_sop.get("workflow_id")
        or "Geo Expert workflow"
    )

    summary = (
        f"Detected {detection_count} preliminary visual indicator(s) for {sop_title}. "
        "These indicators require verification and are not a formal legal conclusion."
    )

    if fallback_used or detector_used == "mock":
        summary += " Mock or fallback detection may have been used."

    return {
        "success": True,
        "method": "deterministic_fallback",
        "summary": summary,
        "detector_used": detector_used,
        "fallback_used": fallback_used,
        "detection_count": detection_count,
        "legal_context_status": legal_context.get("status") or "preliminary only",
        "limitations": [
            "Preliminary visual indicator only.",
            "Requires verification.",
            "Not a formal legal conclusion.",
        ],
        "warnings": recognition_result.get("warnings") or [],
    }


__all__ = ["llm_explain_detections"]
