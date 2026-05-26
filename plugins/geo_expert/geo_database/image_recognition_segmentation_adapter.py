"""Local segmentation adapter skeleton for preliminary image recognition."""

from __future__ import annotations

from typing import Any


def has_segmentation_fixture(payload: Any) -> bool:
    return isinstance(payload, dict) and bool(payload.get("polygons"))


def segmentation_supports_local_run(raw_request: dict[str, Any] | None) -> bool:
    payload = raw_request or {}
    return bool(payload.get("local_image_path")) and bool(payload.get("model_path"))

