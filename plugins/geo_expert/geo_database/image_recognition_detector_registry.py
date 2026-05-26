"""Detector registry for preliminary image-recognition workflows."""

from __future__ import annotations

from typing import Any

from .image_recognition_detector import ImageDetector, get_detector


def select_detector(request: dict[str, Any], context: dict[str, Any] | None = None) -> ImageDetector:
    payload = dict(request or {})
    ctx = dict(context or {})
    preferred = str(
        payload.get("mode")
        or payload.get("detector_preference")
        or ctx.get("detector_preference")
        or "auto"
    ).strip()
    if preferred == "auto":
        for mode in ("ultralytics_yolo", "local_segmentation", "openeo_landcover", "gee_thumbnail", "landcover", "mock"):
            detector = get_detector(mode)
            if detector.can_run(payload, ctx):
                return detector
        return get_detector("mock")
    detector = get_detector(preferred)
    if detector.can_run(payload, ctx):
        return detector
    return get_detector("mock")


__all__ = ["select_detector"]
