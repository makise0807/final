from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import dependency_error, detector_config
from .eo_tools import select_eo_cache_image
from ..geo_database.image_recognition_detector import run_detector
from ..geo_database.image_recognition_ultralytics_adapter import ultralytics_result_to_model_output


def _domain_hint_for_workflow(workflow_id: str) -> str:
    mapping = {
        "WF-001": "可見物件/結構線索，不可判定工廠性質或違法狀態。",
        "WF-004": "可見堆置/裸露地線索，不可直接判定污染或廢棄物違規。",
        "WF-005": "可見規則排列/反光面線索，不可直接判定光電設施合法性。",
        "WF-009": "可見影像異常區，不可直接判定災害成因或損害程度。",
    }
    return mapping.get(workflow_id, "僅能提供一般物件偵測線索，不可直接形成法律或專業定性。")


def _read_image_size(image_path: Path) -> tuple[int, int] | None:
    try:
        from PIL import Image

        with Image.open(image_path) as image:
            return tuple(int(value) for value in image.size)
    except Exception:
        return None


def detector_status() -> dict[str, Any]:
    cfg = detector_config()
    return {
        "success": True,
        "dependency": "model",
        "backend": cfg["backend"],
        "configured": bool(cfg["model_path"]),
        "real_model_configured": bool(cfg["model_path"] and cfg["model_exists"]),
        "model_path_exists": cfg["model_exists"],
        "model_basename": cfg["model_basename"],
        "fallback_available": True,
        "message": "Real detector model is optional. Mock detector fallback remains available.",
    }


def _to_detection_payload(
    request: dict[str, Any],
    model_output: dict[str, Any],
    *,
    detector_name: str,
    model_basename: str,
) -> dict[str, Any]:
    detections: list[dict[str, Any]] = []
    for feature in model_output.get("features") or []:
        bbox = list(feature.get("bbox") or [])
        if len(bbox) != 4:
            continue
        west, south, east, north = [float(value) for value in bbox]
        width_m = abs(east - west) * 111_320.0
        height_m = abs(north - south) * 110_540.0
        area_m2 = round(width_m * height_m, 2)
        detections.append(
            {
                "feature_id": feature.get("feature_id"),
                "geometry": feature.get("geometry"),
                "bbox": bbox,
                "pixel_bbox": list(feature.get("pixel_bbox") or []),
                "raw_class_id": feature.get("raw_class_id"),
                "raw_class_name": feature.get("raw_class_name") or feature.get("class_name"),
                "class_label": feature.get("mapped_class_label") or feature.get("class_name") or "unknown",
                "confidence": float(feature.get("confidence") or 0.0),
                "area_m2": area_m2,
                "evidence": list(feature.get("evidence") or []),
                "legal_status": "unknown",
                "risk_label": "preliminary_suspected_area",
                "requires_verification": True,
                "model_name": model_basename,
                "model_scope": "general_object_detector",
                "domain_specific": False,
                "georeference_available": True,
                "interpretation_allowed": False,
                "mock_georef": False,
                "notes": [
                    f"Detector backend: {detector_name}",
                    f"Model: {model_basename}",
                    "Generic pretrained detector output is a visual indicator only.",
                    "YOLO output is pixel-space unless georeference metadata is available.",
                    _domain_hint_for_workflow(str(request.get("sop_id") or "")),
                ],
            }
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
                    "raw_class_id": item["raw_class_id"],
                    "raw_class_name": item["raw_class_name"],
                    "pixel_bbox": item["pixel_bbox"],
                    "model_name": item["model_name"],
                    "model_scope": item["model_scope"],
                    "domain_specific": item["domain_specific"],
                    "georeference_available": item["georeference_available"],
                    "interpretation_allowed": item["interpretation_allowed"],
                    "mock_georef": item["mock_georef"],
                    "notes": item["notes"],
                },
                "geometry": item["geometry"],
            }
            for item in detections
        ],
    }
    return {
        "success": True,
        "detector_used": detector_name,
        "used_real_model": True,
        "used_real_service": False,
        "fallback_used": False,
        "model_name": model_basename,
        "detections": detections,
        "geojson": geojson,
        "overlay_summary": {
            "detection_count": len(detections),
            "total_area_m2": round(sum(float(item.get("area_m2") or 0.0) for item in detections), 2),
        },
        "warnings": [
            "Generic YOLO detector output is a visual indicator only, not a legal conclusion.",
            "YOLO output is pixel-space unless georeference metadata is available.",
            _domain_hint_for_workflow(str(request.get("sop_id") or "")),
        ],
        "limitations": [
            "Preliminary detection only.",
            "Generic pretrained detector may not be trained for illegal buildings or domain-specific targets.",
            "YOLO general model is not trained specifically for illegal factory, solar facility, or waste-site detection.",
            "Not a formal legal conclusion.",
            "No GeoTIFF/export/download performed.",
        ],
        "detection_limitations": [
            "Requires human visual review.",
            "Domain-specific training recommended for production use.",
            "Interpretation is not allowed as a legal conclusion.",
        ],
        "not_formal_analysis": True,
        "requires_verification": True,
        "image_source": str(request.get("image_source") or "local_image"),
        "landuse_context": dict(request.get("landuse_context") or {}),
        "target_classes": list(request.get("target_classes") or []),
    }


def _run_yolo_detection(payload: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    model_path = Path(str(cfg["model_path"] or ""))
    if not model_path.exists():
        return {
            "success": False,
            "status": "degraded",
            "error": "model_path_missing",
            "detector_used": "yolo",
            "used_real_model": False,
            "warnings": ["Configured YOLO model path does not exist."],
        }
    local_image_path = Path(str(payload.get("local_image_path") or ""))
    if not local_image_path.exists():
        return {
            "success": False,
            "status": "degraded",
            "error": "local_input_missing",
            "detector_used": "yolo",
            "used_real_model": False,
            "warnings": ["Detector requires a readable local image path."],
        }
    if not payload.get("aoi"):
        return {
            "success": False,
            "status": "degraded",
            "error": "aoi_missing",
            "detector_used": "yolo",
            "used_real_model": False,
            "warnings": ["Detector requires AOI metadata to convert detections into map polygons."],
        }
    try:
        from ultralytics import YOLO
    except Exception:
        return {
            "success": False,
            "status": "degraded",
            "error": "yolo_dependency_missing",
            "detector_used": "yolo",
            "used_real_model": False,
            "warnings": ["Ultralytics is not installed. Run: py -3.11 -m pip install ultralytics"],
        }
    image_size = _read_image_size(local_image_path)
    if image_size is None:
        return {
            "success": False,
            "status": "degraded",
            "error": "image_size_unavailable",
            "detector_used": "yolo",
            "used_real_model": False,
            "warnings": ["Image size could not be read for detector polygon conversion."],
        }
    model = YOLO(str(model_path))
    results = model.predict(
        source=str(local_image_path),
        conf=float(cfg["confidence"]),
        device=str(cfg["device"]),
        verbose=False,
    )
    first_result = results[0] if results else None
    if first_result is None:
        return {
            "success": False,
            "status": "degraded",
            "error": "detector_no_result",
            "detector_used": "yolo",
            "used_real_model": False,
            "warnings": ["YOLO returned no result object."],
        }
    model_output = ultralytics_result_to_model_output(first_result, dict(payload.get("aoi") or {}), image_size)
    result = _to_detection_payload(payload, model_output, detector_name="yolo", model_basename=model_path.name)
    return result


def _annotate_generic_detector_result(result: dict[str, Any], workflow_id: str) -> dict[str, Any]:
    result.setdefault("model_scope", "general_object_detector")
    result.setdefault("domain_specific", False)
    result.setdefault("interpretation_allowed", False)
    result.setdefault("detection_limitations", [])
    result["detection_limitations"] = list(dict.fromkeys(list(result.get("detection_limitations") or []) + [
        "Requires human visual review.",
        "Domain-specific training recommended for production use.",
        "Interpretation is not allowed as a legal conclusion.",
    ]))
    detections = []
    for detection in list(result.get("detections") or []):
        item = dict(detection)
        item.setdefault("model_scope", "general_object_detector")
        item.setdefault("domain_specific", False)
        item.setdefault("interpretation_allowed", False)
        item.setdefault("georeference_available", bool(item.get("geometry")))
        item.setdefault("raw_class_name", item.get("class_label"))
        item.setdefault("raw_class_id", None)
        item.setdefault("pixel_bbox", list(item.get("pixel_bbox") or []))
        item.setdefault("notes", [])
        item["notes"] = list(dict.fromkeys(list(item.get("notes") or []) + [_domain_hint_for_workflow(workflow_id)]))
        detections.append(item)
    if detections:
        result["detections"] = detections
    return result


def _maybe_fill_image_from_eo_cache(payload: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(payload)
    if enriched.get("local_image_path"):
        return enriched
    selected = select_eo_cache_image(
        workflow_id=str(enriched.get("sop_id") or ""),
        case_id=str(enriched.get("image_case_id") or ""),
        preferred_name=str(enriched.get("preferred_image_name") or ""),
    )
    if not selected.get("success"):
        return enriched
    image = dict(selected.get("selected_image") or {})
    enriched["local_image_path"] = image.get("image_path")
    enriched["image_source"] = "eo_cache"
    enriched["used_real_input"] = True
    if image.get("aoi") and not enriched.get("aoi"):
        enriched["aoi"] = image.get("aoi")
    return enriched


def run_detection(request: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = _maybe_fill_image_from_eo_cache(dict(request or {}))
    cfg = detector_config()
    if cfg["backend"] == "yolo":
        result = _run_yolo_detection(payload, cfg)
        if result.get("success"):
            return _annotate_generic_detector_result(result, str(payload.get("sop_id") or ""))
        fallback = run_detector(payload)
        fallback.setdefault("warnings", [])
        fallback["warnings"] = list(fallback["warnings"]) + [
            f"YOLO detector degraded: {result.get('error')}",
        ]
        fallback["detector_requested"] = "yolo"
        fallback["used_real_model"] = False
        fallback["degraded_reason"] = result.get("error")
        fallback["model_scope"] = "general_object_detector"
        fallback["domain_specific"] = False
        fallback["interpretation_allowed"] = False
        return _annotate_generic_detector_result(fallback, str(payload.get("sop_id") or ""))

    result = run_detector(payload)
    detector_used = str(result.get("detector_used") or "mock")
    result.setdefault("used_real_model", detector_used not in {"mock", "landcover", "thumbnail", "thumbnail_demo"})
    if detector_used == "mock":
        result.setdefault("warnings", [])
        result["warnings"] = list(result["warnings"]) + ["Real detector model not configured; mock detector fallback used."]
    if payload.get("image_source") == "eo_cache":
        result["image_source"] = "eo_cache"
        result["used_real_input"] = True
    return _annotate_generic_detector_result(result, str(payload.get("sop_id") or ""))


__all__ = ["detector_status", "run_detection"]
