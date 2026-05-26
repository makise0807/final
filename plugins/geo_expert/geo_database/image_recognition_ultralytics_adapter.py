"""Ultralytics YOLO adapter for preliminary image recognition."""

from __future__ import annotations

import importlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .image_recognition_contracts import DetectionFeature
from .image_recognition_model_output import (
    bbox_to_geo_polygon,
    mask_polygon_to_geo_polygon,
    model_class_to_detection_label,
    model_class_to_evidence,
    pixel_to_lonlat,
    polygon_bbox,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ALLOWED_IMAGE_ROOTS = [
    _REPO_ROOT / "tests",
    _REPO_ROOT / ".hermes",
    _REPO_ROOT / "assets",
    _REPO_ROOT / "data",
    Path(tempfile.gettempdir()),
]
_MAX_LOCAL_IMAGE_BYTES = 5_000_000


@dataclass(frozen=True)
class UltralyticsConfig:
    enabled: bool
    model_name: str
    fallback_model: str
    conf: float
    max_detections: int
    allow_download: bool


def get_ultralytics_config() -> UltralyticsConfig:
    return UltralyticsConfig(
        enabled=str(os.getenv("ULTRALYTICS_ENABLED") or "false").strip().lower() == "true",
        model_name=str(os.getenv("ULTRALYTICS_MODEL") or "yolo26n-seg.pt").strip(),
        fallback_model=str(os.getenv("ULTRALYTICS_FALLBACK_MODEL") or "yolo26n.pt").strip(),
        conf=float(str(os.getenv("ULTRALYTICS_CONF") or "0.25").strip() or 0.25),
        max_detections=int(str(os.getenv("ULTRALYTICS_MAX_DETECTIONS") or "50").strip() or 50),
        allow_download=str(os.getenv("ULTRALYTICS_ALLOW_DOWNLOAD") or "false").strip().lower() == "true",
    )


def _import_ultralytics() -> Any | None:
    try:
        return importlib.import_module("ultralytics")
    except Exception:
        return None


def _safe_resolve_local_path(path_value: str) -> Path | None:
    if not path_value:
        return None
    try:
        candidate = Path(path_value).expanduser().resolve()
    except Exception:
        return None
    for root in _ALLOWED_IMAGE_ROOTS:
        try:
            root_resolved = root.resolve()
        except Exception:
            continue
        if candidate == root_resolved or root_resolved in candidate.parents:
            return candidate
    return None


def _is_allowed_local_image(path_value: str) -> bool:
    candidate = _safe_resolve_local_path(path_value)
    if candidate is None or not candidate.exists() or not candidate.is_file():
        return False
    if candidate.stat().st_size > _MAX_LOCAL_IMAGE_BYTES:
        return False
    return candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}


def _resolve_model_reference(model_name: str, allow_download: bool) -> tuple[str | None, str | None]:
    candidate = _safe_resolve_local_path(model_name)
    if candidate and candidate.exists():
        return str(candidate), None
    relative = (_REPO_ROOT / model_name).resolve()
    if relative.exists():
        return str(relative), None
    if allow_download:
        return model_name, None
    return None, "ultralytics_model_download_disabled"


def _read_image_size(local_image_path: str, request: dict[str, Any]) -> tuple[int, int] | None:
    width = int(request.get("image_width") or 0)
    height = int(request.get("image_height") or 0)
    if width > 0 and height > 0:
        return width, height
    try:
        from PIL import Image
    except Exception:
        return None
    with Image.open(local_image_path) as image:
        image_width, image_height = image.size
    if image_width > 4096 or image_height > 4096:
        return None
    return int(image_width), int(image_height)


def _to_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        try:
            return value.tolist()
        except Exception:
            pass
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def ultralytics_result_to_model_output(result: Any, aoi: dict[str, Any], image_size: tuple[int, int]) -> dict[str, Any]:
    image_width, image_height = image_size
    names = getattr(result, "names", {}) or {}
    model_task = "detect"
    features: list[dict[str, Any]] = []

    masks = getattr(result, "masks", None)
    boxes = getattr(result, "boxes", None)

    mask_polygons = getattr(masks, "xy", None) if masks is not None else None
    box_coords = _to_list(getattr(boxes, "xyxy", None)) if boxes is not None else []
    box_classes = _to_list(getattr(boxes, "cls", None)) if boxes is not None else []
    box_confs = _to_list(getattr(boxes, "conf", None)) if boxes is not None else []

    if mask_polygons:
        model_task = "segment"
        for index, polygon_points in enumerate(mask_polygons, start=1):
            points = [[float(point[0]), float(point[1])] for point in _to_list(polygon_points)]
            if len(points) < 3:
                continue
            class_id = int(_to_list(box_classes)[index - 1]) if len(box_classes) >= index else 0
            confidence = float(_to_list(box_confs)[index - 1]) if len(box_confs) >= index else 0.5
            class_name = str(names.get(class_id) or class_id)
            geometry = mask_polygon_to_geo_polygon(points, aoi, image_width, image_height)
            features.append(
                {
                    "feature_id": f"det-yolo-{index:03d}",
                    "geometry": geometry,
                    "bbox": polygon_bbox(geometry),
                    "pixel_bbox": [
                        min(float(point[0]) for point in points),
                        min(float(point[1]) for point in points),
                        max(float(point[0]) for point in points),
                        max(float(point[1]) for point in points),
                    ] if points else [],
                    "raw_class_id": class_id,
                    "raw_class_name": class_name,
                    "class_name": class_name,
                    "mapped_class_label": model_class_to_detection_label(class_name),
                    "confidence": round(confidence, 4),
                    "evidence": model_class_to_evidence(class_name),
                }
            )
    else:
        for index, bbox in enumerate(box_coords, start=1):
            if len(bbox) < 4:
                continue
            class_id = int(box_classes[index - 1]) if len(box_classes) >= index else 0
            confidence = float(box_confs[index - 1]) if len(box_confs) >= index else 0.5
            class_name = str(names.get(class_id) or class_id)
            geometry = bbox_to_geo_polygon(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]), aoi, image_width, image_height)
            features.append(
                {
                    "feature_id": f"det-yolo-{index:03d}",
                    "geometry": geometry,
                    "bbox": polygon_bbox(geometry),
                    "pixel_bbox": [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])],
                    "raw_class_id": class_id,
                    "raw_class_name": class_name,
                    "class_name": class_name,
                    "mapped_class_label": model_class_to_detection_label(class_name),
                    "confidence": round(confidence, 4),
                    "evidence": model_class_to_evidence(class_name),
                }
            )
    return {"model_task": model_task, "features": features}


def _estimate_area_m2(bbox: list[float]) -> float:
    west, south, east, north = bbox
    width_m = abs(east - west) * 111_320.0
    height_m = abs(north - south) * 110_540.0
    return round(width_m * height_m, 2)


class UltralyticsYOLODetector:
    name = "ultralytics_yolo"
    mode = "ultralytics_yolo"
    requires_network = False
    requires_approval = False

    def can_run(self, request: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        cfg = get_ultralytics_config()
        if not cfg.enabled:
            return False
        if not request.get("aoi") or not request.get("local_image_path"):
            return False
        if not _is_allowed_local_image(str(request.get("local_image_path") or "")):
            return False
        if _import_ultralytics() is None:
            return False
        model_name = str(request.get("model_name") or cfg.model_name).strip()
        model_reference, error = _resolve_model_reference(model_name, cfg.allow_download)
        if model_reference:
            return True
        fallback_reference, _ = _resolve_model_reference(cfg.fallback_model, cfg.allow_download)
        return error is None or bool(fallback_reference)

    def run(self, request: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        cfg = get_ultralytics_config()
        ultralytics_module = _import_ultralytics()
        if ultralytics_module is None:
            return {"success": False, "error": "detector_unavailable", "warnings": ["Ultralytics package is not installed."]}
        local_image_path = str(request.get("local_image_path") or "").strip()
        if not _is_allowed_local_image(local_image_path):
            return {"success": False, "error": "detector_unavailable", "warnings": ["Ultralytics YOLO requires an allowed local image path."]}
        if not request.get("aoi"):
            return {"success": False, "error": "detector_unavailable", "warnings": ["Ultralytics YOLO requires AOI metadata to build polygons."]}

        image_size = _read_image_size(local_image_path, request)
        if image_size is None:
            return {"success": False, "error": "detector_unavailable", "warnings": ["Ultralytics YOLO requires image_width/image_height or a readable small local image."]}

        requested_model = str(request.get("model_name") or cfg.model_name).strip()
        model_reference, _ = _resolve_model_reference(requested_model, cfg.allow_download)
        model_task_name = "segment" if "-seg" in requested_model else "detect"
        if model_reference is None:
            fallback_reference, fallback_error = _resolve_model_reference(cfg.fallback_model, cfg.allow_download)
            if fallback_reference is None:
                return {"success": False, "error": "detector_unavailable", "warnings": [fallback_error or "Ultralytics model is unavailable."]}
            model_reference = fallback_reference
            requested_model = cfg.fallback_model
            model_task_name = "detect"

        YOLO = getattr(ultralytics_module, "YOLO", None)
        if YOLO is None:
            return {"success": False, "error": "detector_unavailable", "warnings": ["Ultralytics.YOLO is unavailable."]}

        model = YOLO(model_reference)
        raw_results = model.predict(
            source=local_image_path,
            conf=cfg.conf,
            max_det=cfg.max_detections,
            verbose=False,
        )
        first_result = raw_results[0] if raw_results else None
        if first_result is None:
            return {"success": False, "error": "detector_unavailable", "warnings": ["Ultralytics YOLO returned no result object."]}

        model_output = ultralytics_result_to_model_output(first_result, request["aoi"], image_size)
        detections: list[dict[str, Any]] = []
        for feature in model_output["features"]:
            detections.append(
                DetectionFeature(
                    feature_id=feature["feature_id"],
                    geometry=feature["geometry"],
                    bbox=feature["bbox"],
                    class_label=feature["mapped_class_label"],
                    confidence=float(feature["confidence"]),
                    area_m2=_estimate_area_m2(feature["bbox"]),
                    evidence=list(feature["evidence"]) + ["visual_indicator_only", "generic_pretrained_model"],
                    legal_status="unknown",
                    risk_label="preliminary_suspected_area",
                    requires_verification=True,
                    notes=[
                        f"Model class: {feature['class_name']}",
                        "Ultralytics pretrained model is a visual detector only.",
                        "Not trained specifically for illegal buildings or formal legal screening.",
                    ],
                ).to_dict()
            )

        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": item["feature_id"],
                    "properties": {
                        "feature_id": item["feature_id"],
                        "class_label": item["class_label"],
                        "confidence": item["confidence"],
                        "area_m2": item["area_m2"],
                        "evidence": item["evidence"],
                        "legal_status": item["legal_status"],
                        "risk_label": item["risk_label"],
                        "requires_verification": item["requires_verification"],
                        "notes": item["notes"],
                    },
                    "geometry": item["geometry"],
                }
                for item in detections
            ],
        }
        return {
            "success": True,
            "mode": self.mode,
            "sop_id": str(request.get("sop_id") or ""),
            "image_source": str(request.get("image_source") or "local_image"),
            "detector_used": self.name,
            "model_name": requested_model,
            "model_task": model_output["model_task"] or model_task_name,
            "fallback_used": False,
            "detections": detections,
            "geojson": geojson,
            "overlay_summary": {
                "detection_count": len(detections),
                "total_area_m2": round(sum(float(item["area_m2"]) for item in detections), 2),
            },
            "limitations": [
                "Preliminary detection only.",
                "YOLO pretrained model may not be trained for illegal buildings.",
                "Visual indicator only.",
                "Cadastral / permit / landuse layers required.",
                "Field verification required.",
                "No GeoTIFF/export/download performed.",
            ],
            "warnings": [
                "Ultralytics YOLO output is a visual indicator only, not a legal conclusion.",
            ],
            "not_formal_analysis": True,
            "requires_verification": True,
            "target_classes": list(request.get("target_classes") or []),
            "landuse_context": dict(request.get("landuse_context") or {}),
        }


__all__ = [
    "UltralyticsYOLODetector",
    "bbox_to_geo_polygon",
    "get_ultralytics_config",
    "mask_polygon_to_geo_polygon",
    "pixel_to_lonlat",
    "ultralytics_result_to_model_output",
]
