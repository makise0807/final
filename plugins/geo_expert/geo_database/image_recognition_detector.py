"""Preliminary image-recognition detectors for SOP-driven demos and adapters."""

from __future__ import annotations

import hashlib
from typing import Any

from .image_recognition_contracts import DetectionFeature, ImageRecognitionRequest, ImageRecognitionResult
from .image_recognition_landcover_adapter import build_landcover_evidence, map_landcover_class
from .image_recognition_real_adapter import has_gee_thumbnail_preview, has_openeo_vectors
from .image_recognition_safety import validate_detection_result_safety
from .image_recognition_segmentation_adapter import has_segmentation_fixture, segmentation_supports_local_run
from .image_recognition_ultralytics_adapter import UltralyticsYOLODetector

_BASE_LIMITATIONS = [
    "Preliminary detection only.",
    "Needs verification.",
    "Not a formal legal conclusion.",
    "No GeoTIFF/export/download performed.",
]

_DEFAULT_TARGET_CLASSES = ["building", "concrete_surface", "non_vegetation_surface"]


class ImageDetector:
    name = "base"
    mode = "mock"
    requires_network = False
    requires_approval = False

    def can_run(self, request: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        raise NotImplementedError

    def run(self, request: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError


def _as_request(value: Any) -> tuple[ImageRecognitionRequest, dict[str, Any]]:
    if isinstance(value, ImageRecognitionRequest):
        return value, value.to_dict()
    payload = dict(value or {}) if isinstance(value, dict) else {}
    request = ImageRecognitionRequest(
        task=str(payload.get("task") or ""),
        sop_id=str(payload.get("sop_id") or ""),
        image_source=str(payload.get("image_source") or "mock"),
        image_url=payload.get("image_url"),
        local_image_path=payload.get("local_image_path"),
        aoi=dict(payload.get("aoi") or {}),
        time_range=list(payload.get("time_range") or []),
        target_classes=list(payload.get("target_classes") or []),
        landuse_context=dict(payload.get("landuse_context") or {}),
        mode=str(payload.get("mode") or "mock"),
        image_width=payload.get("image_width"),
        image_height=payload.get("image_height"),
        model_name=payload.get("model_name"),
    )
    return request, payload


def _bbox_from_aoi(aoi: dict[str, Any]) -> tuple[float, float, float, float]:
    west = float(aoi.get("west"))
    south = float(aoi.get("south"))
    east = float(aoi.get("east"))
    north = float(aoi.get("north"))
    if west >= east or south >= north:
        raise ValueError("image_recognition_invalid_aoi")
    return west, south, east, north


def _rect_polygon(west: float, south: float, east: float, north: float) -> dict[str, Any]:
    return {
        "type": "Polygon",
        "coordinates": [[
            [west, south],
            [east, south],
            [east, north],
            [west, north],
            [west, south],
        ]],
    }


def _estimate_area_m2(west: float, south: float, east: float, north: float) -> float:
    width_m = abs(east - west) * 111_320.0
    height_m = abs(north - south) * 110_540.0
    return round(width_m * height_m, 2)


def _build_detection_feature(
    *,
    feature_id: str,
    bbox: list[float],
    class_label: str,
    confidence: float,
    evidence: list[str],
    notes: list[str],
) -> dict[str, Any]:
    west, south, east, north = bbox
    return DetectionFeature(
        feature_id=feature_id,
        geometry=_rect_polygon(west, south, east, north),
        bbox=[west, south, east, north],
        class_label=class_label,
        confidence=round(float(confidence), 2),
        area_m2=_estimate_area_m2(west, south, east, north),
        evidence=evidence,
        legal_status="unknown",
        risk_label="preliminary_suspected_area",
        requires_verification=True,
        notes=notes,
    ).to_dict()


def _build_geojson(detections: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": detection["feature_id"],
                "properties": {
                    "feature_id": detection["feature_id"],
                    "class_label": detection["class_label"],
                    "confidence": detection["confidence"],
                    "area_m2": detection["area_m2"],
                    "evidence": detection["evidence"],
                    "legal_status": detection["legal_status"],
                    "risk_label": detection["risk_label"],
                    "requires_verification": detection["requires_verification"],
                    "notes": detection["notes"],
                },
                "geometry": detection["geometry"],
            }
            for detection in detections
        ],
    }


def _build_result(
    *,
    request: ImageRecognitionRequest,
    mode: str,
    detections: list[dict[str, Any]],
    warnings: list[str] | None = None,
    limitations: list[str] | None = None,
    detector_used: str,
    fallback_used: bool,
) -> dict[str, Any]:
    payload = ImageRecognitionResult(
        success=True,
        mode=mode,
        sop_id=request.sop_id,
        image_source=request.image_source or "mock",
        detections=detections,
        geojson=_build_geojson(detections),
        overlay_summary={
            "detection_count": len(detections),
            "total_area_m2": round(sum(float(item.get("area_m2") or 0.0) for item in detections), 2),
        },
        limitations=list(limitations or _BASE_LIMITATIONS),
        warnings=list(warnings or []),
        not_formal_analysis=True,
        requires_verification=True,
        target_classes=request.target_classes or list(_DEFAULT_TARGET_CLASSES),
    ).to_dict()
    payload["detector_used"] = detector_used
    payload["fallback_used"] = fallback_used
    payload["landuse_context"] = dict(request.landuse_context or {})
    return payload


def _detection_seed(request: ImageRecognitionRequest) -> int:
    blob = "|".join(
        [
            request.task,
            request.sop_id,
            request.image_source,
            request.mode,
            str(request.aoi),
            ",".join(request.time_range),
            ",".join(request.target_classes),
        ]
    )
    return int(hashlib.sha256(blob.encode("utf-8")).hexdigest()[:8], 16)


def _build_mock_bboxes(request: ImageRecognitionRequest) -> list[list[float]]:
    west, south, east, north = _bbox_from_aoi(request.aoi)
    dx = east - west
    dy = north - south
    variant = _detection_seed(request) % 3
    layouts = [
        [
            [west + dx * 0.12, south + dy * 0.18, west + dx * 0.28, south + dy * 0.33],
            [west + dx * 0.46, south + dy * 0.40, west + dx * 0.66, south + dy * 0.56],
            [west + dx * 0.62, south + dy * 0.18, west + dx * 0.78, south + dy * 0.30],
            [west + dx * 0.30, south + dy * 0.62, west + dx * 0.44, south + dy * 0.76],
        ],
        [
            [west + dx * 0.18, south + dy * 0.22, west + dx * 0.34, south + dy * 0.38],
            [west + dx * 0.50, south + dy * 0.28, west + dx * 0.69, south + dy * 0.46],
            [west + dx * 0.30, south + dy * 0.58, west + dx * 0.46, south + dy * 0.72],
            [west + dx * 0.68, south + dy * 0.62, west + dx * 0.82, south + dy * 0.76],
        ],
        [
            [west + dx * 0.10, south + dy * 0.50, west + dx * 0.24, south + dy * 0.68],
            [west + dx * 0.36, south + dy * 0.16, west + dx * 0.54, south + dy * 0.32],
            [west + dx * 0.58, south + dy * 0.48, west + dx * 0.76, south + dy * 0.64],
            [west + dx * 0.74, south + dy * 0.18, west + dx * 0.88, south + dy * 0.34],
        ],
    ]
    return layouts[variant]


def _class_from_hint(class_hint: str) -> str:
    if class_hint == "solar_panel":
        return "suspected_solar_panel"
    if class_hint in {"bare_soil", "non_vegetation_surface"}:
        return "possible_bare_ground_or_construction_site"
    return "suspected_building_or_concrete_surface"


class MockDetector(ImageDetector):
    name = "mock"
    mode = "mock"

    def can_run(self, request: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        return True

    def run(self, request: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        recognition_request, _ = _as_request(request)
        target_classes = recognition_request.target_classes or list(_DEFAULT_TARGET_CLASSES)
        detections: list[dict[str, Any]] = []
        for index, bbox in enumerate(_build_mock_bboxes(recognition_request), start=1):
            class_hint = target_classes[(index - 1) % len(target_classes)]
            detections.append(
                _build_detection_feature(
                    feature_id=f"det-{index:03d}",
                    bbox=bbox,
                    class_label=_class_from_hint(class_hint),
                    confidence=min(0.56 + index * 0.04, 0.68),
                    evidence=[
                        "non_vegetation_signature",
                        "rectangular_shape",
                        "inside_agricultural_zone"
                        if recognition_request.landuse_context.get("zone_type") == "agricultural"
                        else "inside_target_zone",
                    ],
                    notes=[
                        "Mock detector output for workflow prototyping.",
                        "Requires parcel, permit, and field verification.",
                    ],
                )
            )
        return _build_result(
            request=recognition_request,
            mode=self.mode,
            detections=detections,
            warnings=["Mock detector used. Geometry is deterministic and preliminary only."],
            limitations=list(_BASE_LIMITATIONS),
            detector_used=self.name,
            fallback_used=False,
        )


class ThumbnailDemoDetector(ImageDetector):
    name = "thumbnail_demo"
    mode = "thumbnail_demo"

    def can_run(self, request: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        return True

    def run(self, request: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        recognition_request, payload = _as_request(request)
        mock_request = recognition_request.to_dict() | {"mode": self.mode}
        result = MockDetector().run(mock_request, context)
        result["mode"] = self.mode
        result["detector_used"] = self.name
        result["fallback_used"] = False
        result["image_source"] = recognition_request.image_source or "gee_thumbnail"
        result["warnings"] = list(
            dict.fromkeys(
                [
                    *result.get("warnings", []),
                    "Thumbnail demo detector does not download imagery and does not run heavy CV.",
                    "If an image URL is present, it is treated as a display reference only.",
                ]
            )
        )
        if payload.get("image_url"):
            result["image_url"] = payload.get("image_url")
        return result


class LandcoverDetectorSkeleton(ImageDetector):
    name = "landcover"
    mode = "landcover"

    def can_run(self, request: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        payload = dict(request or {})
        landcover_data = payload.get("landcover_data")
        return isinstance(landcover_data, dict) and bool(landcover_data.get("vectorized_polygons"))

    def run(self, request: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        recognition_request, payload = _as_request(request)
        landcover_data = payload.get("landcover_data")
        if not isinstance(landcover_data, dict) or not landcover_data.get("vectorized_polygons"):
            return {
                "success": False,
                "error": "detector_unavailable",
                "detector_used": self.name,
                "fallback_used": False,
                "warnings": ["Landcover detector skeleton requires landcover_data.vectorized_polygons."],
            }
        detections: list[dict[str, Any]] = []
        for index, polygon in enumerate(landcover_data.get("vectorized_polygons") or [], start=1):
            if not isinstance(polygon, dict):
                continue
            bbox = polygon.get("bbox") or []
            if len(bbox) != 4:
                continue
            mapped = _class_from_hint(str(polygon.get("class_label") or polygon.get("class_name") or "building"))
            detections.append(
                _build_detection_feature(
                    feature_id=str(polygon.get("feature_id") or f"det-land-{index:03d}"),
                    bbox=[float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])],
                    class_label=mapped,
                    confidence=float(polygon.get("confidence") or 0.61),
                    evidence=["landcover_vectorized_polygon", "preclassified_surface", "requires_rule_review"],
                    notes=[
                        "Landcover detector skeleton converted vectorized polygons only.",
                        "No raster or GeoTIFF was read.",
                    ],
                )
            )
        return _build_result(
            request=recognition_request,
            mode=self.mode,
            detections=detections,
            warnings=["Landcover detector skeleton used vectorized polygons only."],
            limitations=[*_BASE_LIMITATIONS, "No raster or GeoTIFF ingestion was performed."],
            detector_used=self.name,
            fallback_used=False,
        )


class SegmentationDetectorSkeleton(ImageDetector):
    name = "segmentation"
    mode = "segmentation"

    def can_run(self, request: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        payload = dict(request or {})
        return bool(payload.get("local_image_path")) and bool(payload.get("model_path"))

    def run(self, request: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(request or {})
        if not payload.get("local_image_path") or not payload.get("model_path"):
            return {
                "success": False,
                "error": "detector_unavailable",
                "detector_used": self.name,
                "fallback_used": False,
                "warnings": ["Segmentation detector skeleton requires local_image_path and model_path."],
            }
        return {
            "success": False,
            "error": "detector_unavailable",
            "detector_used": self.name,
            "fallback_used": False,
            "warnings": [
                "Segmentation detector skeleton is a placeholder only.",
                "No heavy dependencies are imported in ordinary pytest.",
            ],
        }


class OpenEOLandcoverDetector(ImageDetector):
    name = "openeo_landcover"
    mode = "openeo_landcover"

    def can_run(self, request: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        return has_openeo_vectors(request)

    def run(self, request: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        recognition_request, payload = _as_request(request)
        openeo_result = payload.get("openeo_result")
        if not isinstance(openeo_result, dict) or not openeo_result.get("vectorized_polygons"):
            return {
                "success": False,
                "error": "detector_unavailable",
                "detector_used": self.name,
                "fallback_used": False,
                "warnings": ["OpenEO landcover adapter needs provided vectorized_polygons only."],
            }
        detections: list[dict[str, Any]] = []
        inside_agri = bool((recognition_request.landuse_context or {}).get("zone_type") == "agricultural")
        for index, polygon in enumerate(openeo_result.get("vectorized_polygons") or [], start=1):
            if not isinstance(polygon, dict):
                continue
            bbox = polygon.get("bbox") or []
            if len(bbox) != 4:
                continue
            mapped = map_landcover_class(str(polygon.get("class_label") or polygon.get("class_name") or ""))
            if mapped == "background_or_low_risk":
                continue
            evidence = build_landcover_evidence(
                mapped_class=mapped,
                workflow_id=recognition_request.sop_id,
                inside_agricultural_zone=inside_agri,
            )
            evidence.append("rectangular_shape")
            detections.append(
                _build_detection_feature(
                    feature_id=str(polygon.get("feature_id") or f"det-openeo-{index:03d}"),
                    bbox=[float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])],
                    class_label=mapped,
                    confidence=float(polygon.get("confidence") or 0.71),
                    evidence=list(dict.fromkeys(evidence)),
                    notes=[
                        f"OpenEO vector adapter source: {str(openeo_result.get('source') or 'provided')}",
                        "Adapter only; no submit, no polling, no GeoTIFF, no download.",
                    ],
                )
            )
        return _build_result(
            request=recognition_request,
            mode=self.mode,
            detections=detections,
            warnings=["OpenEO landcover adapter used provided vectors only."],
            limitations=[*_BASE_LIMITATIONS, "Still needs legal building, permit, cadastral, and field verification data."],
            detector_used=self.name,
            fallback_used=False,
        )


class GeeThumbnailDetector(ImageDetector):
    name = "gee_thumbnail"
    mode = "gee_thumbnail"

    def can_run(self, request: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        return has_gee_thumbnail_preview(request)

    def run(self, request: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        recognition_request, payload = _as_request(request)
        result = ThumbnailDemoDetector().run(recognition_request.to_dict() | {"mode": self.mode}, context)
        result["mode"] = self.mode
        result["detector_used"] = self.name
        result["fallback_used"] = False
        result["image_source"] = "gee_thumbnail"
        result["warnings"] = list(
            dict.fromkeys(
                [
                    *result.get("warnings", []),
                    "thumbnail preview only",
                    "not suitable for formal detection",
                    "requires higher-resolution imagery / official layers",
                ]
            )
        )
        result["limitations"] = list(
            dict.fromkeys(
                [
                    *result.get("limitations", []),
                    "thumbnail preview only",
                    "not suitable for formal detection",
                    "requires higher-resolution imagery / official layers",
                ]
            )
        )
        if payload.get("image_url"):
            result["image_url"] = payload.get("image_url")
        for detection in result.get("detections", []):
            detection["confidence"] = min(float(detection.get("confidence") or 0.0), 0.65)
            detection["notes"] = list(dict.fromkeys([*(detection.get("notes") or []), "thumbnail_preview"]))
        return result


class LocalSegmentationDetector(ImageDetector):
    name = "local_segmentation"
    mode = "local_segmentation"

    def can_run(self, request: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        payload = dict(request or {})
        return segmentation_supports_local_run(payload) and has_segmentation_fixture(payload.get("segmentation_output"))

    def run(self, request: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        recognition_request, payload = _as_request(request)
        if not segmentation_supports_local_run(payload) or not has_segmentation_fixture(payload.get("segmentation_output")):
            return {
                "success": False,
                "error": "detector_unavailable",
                "detector_used": self.name,
                "fallback_used": False,
                "warnings": ["Local segmentation adapter requires local_image_path, model_path, and segmentation_output.polygons."],
            }
        detections: list[dict[str, Any]] = []
        for index, polygon in enumerate((payload.get("segmentation_output") or {}).get("polygons") or [], start=1):
            bbox = polygon.get("bbox") or []
            if len(bbox) != 4:
                continue
            detections.append(
                _build_detection_feature(
                    feature_id=str(polygon.get("feature_id") or f"det-seg-{index:03d}"),
                    bbox=[float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])],
                    class_label=str(polygon.get("class_label") or "suspected_building_or_concrete_surface"),
                    confidence=float(polygon.get("confidence") or 0.69),
                    evidence=["local_segmentation_fixture", "requires_rule_review"],
                    notes=[
                        f"Local segmentation model type: {str(payload.get('model_type') or 'custom')}",
                        "Fixture polygons only; no heavy model import here.",
                    ],
                )
            )
        return _build_result(
            request=recognition_request,
            mode=self.mode,
            detections=detections,
            warnings=["Local segmentation adapter used fixture polygons only."],
            limitations=[*_BASE_LIMITATIONS, "Optional local-model path only; ordinary pytest does not require model weights."],
            detector_used=self.name,
            fallback_used=False,
        )


_DETECTORS: dict[str, ImageDetector] = {
    "mock": MockDetector(),
    "thumbnail_demo": ThumbnailDemoDetector(),
    "landcover": LandcoverDetectorSkeleton(),
    "segmentation": SegmentationDetectorSkeleton(),
    "openeo_landcover": OpenEOLandcoverDetector(),
    "gee_thumbnail": GeeThumbnailDetector(),
    "local_segmentation": LocalSegmentationDetector(),
    "ultralytics_yolo": UltralyticsYOLODetector(),
}


def get_detector(mode: str) -> ImageDetector:
    return _DETECTORS.get(str(mode or "mock").strip(), _DETECTORS["mock"])


def run_mock_detector(request: Any) -> dict[str, Any]:
    _, payload = _as_request(request)
    return MockDetector().run(payload)


def run_thumbnail_demo_detector(request: Any) -> dict[str, Any]:
    _, payload = _as_request(request)
    return ThumbnailDemoDetector().run(payload)


def run_detector(request: Any) -> dict[str, Any]:
    recognition_request, payload = _as_request(request)
    requested_mode = str(payload.get("mode") or "mock").strip()
    detector = get_detector(requested_mode)

    if detector.can_run(payload):
        result = detector.run(payload)
        result.setdefault("detector_used", detector.name)
        result.setdefault("fallback_used", False)
        safety = validate_detection_result_safety(result)
        if safety.get("success"):
            return result
        result["warnings"] = list(
            dict.fromkeys(
                [
                    *(result.get("warnings") or []),
                    f"Detector output failed safety validation: {', '.join(safety.get('issues') or [])}",
                ]
            )
        )

    fallback = MockDetector().run(recognition_request.to_dict() | {"mode": "mock"})
    fallback["detector_used"] = "mock"
    fallback["fallback_used"] = True
    fallback["requested_mode"] = requested_mode
    fallback_message = (
        "Ultralytics YOLO unavailable; fallback to mock preliminary overlay."
        if requested_mode == "ultralytics_yolo"
        else f"Requested detector '{requested_mode}' is unavailable. Fallback to mock preliminary overlay."
    )
    fallback["warnings"] = list(
        dict.fromkeys(
            [
                fallback_message,
                "fallback_used=true",
                *(fallback.get("warnings") or []),
            ]
        )
    )
    return fallback


__all__ = [
    "ImageDetector",
    "GeeThumbnailDetector",
    "LandcoverDetectorSkeleton",
    "LocalSegmentationDetector",
    "MockDetector",
    "OpenEOLandcoverDetector",
    "SegmentationDetectorSkeleton",
    "ThumbnailDemoDetector",
    "_as_request",
    "get_detector",
    "run_detector",
    "run_mock_detector",
    "run_thumbnail_demo_detector",
]
