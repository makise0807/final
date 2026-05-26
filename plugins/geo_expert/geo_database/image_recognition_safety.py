"""Safety validation for preliminary detection outputs."""

from __future__ import annotations

from typing import Any

_BANNED_PHRASES = (
    "確定違法",
    "已判定違章",
    "主管機關認定",
    "裁罰確定",
)


def _flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return str(value or "")


def validate_detection_result_safety(result: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if not bool(result.get("not_formal_analysis")):
        issues.append("not_formal_analysis_must_be_true")
    if not bool(result.get("requires_verification")):
        issues.append("requires_verification_must_be_true")

    detector_used = str(result.get("detector_used") or "")
    landuse_context = result.get("landuse_context") if isinstance(result.get("landuse_context"), dict) else {}
    legal_building_layer_available = bool((landuse_context or {}).get("legal_building_layer_available", True))

    for feature in result.get("detections") or []:
        if not isinstance(feature, dict):
            continue
        legal_status = str(feature.get("legal_status") or "")
        risk_label = str(feature.get("risk_label") or "")
        confidence = float(feature.get("confidence") or 0.0)
        if legal_status == "confirmed_illegal":
            issues.append("confirmed_illegal_not_allowed")
        if risk_label == "illegal_confirmed":
            issues.append("illegal_confirmed_not_allowed")
        if detector_used == "mock" and confidence > 0.7:
            issues.append("mock_confidence_too_high")
        if detector_used == "gee_thumbnail" and confidence > 0.65:
            issues.append("gee_thumbnail_confidence_too_high")
        if not legal_building_layer_available and (
            "confirmed" in legal_status.lower() or "illegal" in risk_label.lower()
        ):
            issues.append("legal_layer_missing_stronger_claim_not_allowed")

    text_blob = _flatten_text(result)
    for phrase in _BANNED_PHRASES:
        if phrase in text_blob:
            issues.append(f"banned_phrase:{phrase}")

    return {"success": not issues, "issues": list(dict.fromkeys(issues))}


__all__ = ["validate_detection_result_safety"]
