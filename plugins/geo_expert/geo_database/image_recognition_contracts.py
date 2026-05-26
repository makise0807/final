"""Contracts for preliminary image-recognition workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _normalize_aoi(aoi: Any) -> dict[str, Any]:
    if not isinstance(aoi, dict):
        return {}
    return {
        "west": aoi.get("west"),
        "south": aoi.get("south"),
        "east": aoi.get("east"),
        "north": aoi.get("north"),
        "crs": aoi.get("crs") or "EPSG:4326",
    }


@dataclass(slots=True)
class ImageRecognitionRequest:
    task: str
    sop_id: str
    image_source: str = "mock"
    image_url: str | None = None
    local_image_path: str | None = None
    aoi: dict[str, Any] = field(default_factory=dict)
    time_range: list[str] = field(default_factory=list)
    target_classes: list[str] = field(default_factory=list)
    landuse_context: dict[str, Any] = field(default_factory=dict)
    mode: str = "mock"
    image_width: int | None = None
    image_height: int | None = None
    model_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["task"] = _normalize_text(payload["task"])
        payload["sop_id"] = _normalize_text(payload["sop_id"])
        payload["image_source"] = _normalize_text(payload["image_source"]) or "mock"
        payload["image_url"] = _normalize_text(payload["image_url"]) or None
        payload["local_image_path"] = _normalize_text(payload["local_image_path"]) or None
        payload["aoi"] = _normalize_aoi(payload["aoi"])
        payload["time_range"] = [str(item) for item in _normalize_list(payload["time_range"]) if _normalize_text(item)]
        payload["target_classes"] = [str(item) for item in _normalize_list(payload["target_classes"]) if _normalize_text(item)]
        payload["landuse_context"] = dict(payload["landuse_context"] or {})
        payload["mode"] = _normalize_text(payload["mode"]) or "mock"
        payload["image_width"] = int(payload["image_width"]) if payload["image_width"] else None
        payload["image_height"] = int(payload["image_height"]) if payload["image_height"] else None
        payload["model_name"] = _normalize_text(payload["model_name"]) or None
        return payload


@dataclass(slots=True)
class DetectionFeature:
    feature_id: str
    geometry: dict[str, Any]
    bbox: list[float]
    class_label: str
    confidence: float
    area_m2: float
    evidence: list[str] = field(default_factory=list)
    legal_status: str = "unknown"
    risk_label: str = "preliminary_suspected_area"
    requires_verification: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["feature_id"] = _normalize_text(payload["feature_id"])
        payload["class_label"] = _normalize_text(payload["class_label"])
        payload["confidence"] = float(payload["confidence"] or 0.0)
        payload["area_m2"] = float(payload["area_m2"] or 0.0)
        payload["evidence"] = [str(item) for item in _normalize_list(payload["evidence"]) if _normalize_text(item)]
        payload["legal_status"] = _normalize_text(payload["legal_status"]) or "unknown"
        payload["risk_label"] = _normalize_text(payload["risk_label"]) or "preliminary_suspected_area"
        payload["requires_verification"] = bool(payload["requires_verification"])
        payload["notes"] = [str(item) for item in _normalize_list(payload["notes"]) if _normalize_text(item)]
        return payload


@dataclass(slots=True)
class ImageRecognitionResult:
    success: bool
    mode: str
    sop_id: str
    image_source: str
    detections: list[dict[str, Any]] = field(default_factory=list)
    geojson: dict[str, Any] = field(default_factory=dict)
    overlay_summary: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    not_formal_analysis: bool = True
    requires_verification: bool = True
    target_classes: list[str] = field(default_factory=list)
    detector_used: str | None = None
    fallback_used: bool = False
    model_name: str | None = None
    model_task: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["success"] = bool(payload["success"])
        payload["mode"] = _normalize_text(payload["mode"]) or "mock"
        payload["sop_id"] = _normalize_text(payload["sop_id"])
        payload["image_source"] = _normalize_text(payload["image_source"]) or "mock"
        payload["detections"] = [dict(item) for item in _normalize_list(payload["detections"]) if isinstance(item, dict)]
        payload["geojson"] = dict(payload["geojson"] or {})
        payload["overlay_summary"] = dict(payload["overlay_summary"] or {})
        payload["limitations"] = [str(item) for item in _normalize_list(payload["limitations"]) if _normalize_text(item)]
        payload["warnings"] = [str(item) for item in _normalize_list(payload["warnings"]) if _normalize_text(item)]
        payload["not_formal_analysis"] = bool(payload["not_formal_analysis"])
        payload["requires_verification"] = bool(payload["requires_verification"])
        payload["target_classes"] = [str(item) for item in _normalize_list(payload["target_classes"]) if _normalize_text(item)]
        payload["detector_used"] = _normalize_text(payload["detector_used"]) or None
        payload["fallback_used"] = bool(payload["fallback_used"])
        payload["model_name"] = _normalize_text(payload["model_name"]) or None
        payload["model_task"] = _normalize_text(payload["model_task"]) or None
        return payload


__all__ = [
    "DetectionFeature",
    "ImageRecognitionRequest",
    "ImageRecognitionResult",
]
