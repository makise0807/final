"""Preview-safe real detector adapters for provided vectors or metadata."""

from __future__ import annotations

from typing import Any


def has_openeo_vectors(raw_request: dict[str, Any] | None) -> bool:
    payload = raw_request or {}
    openeo_result = payload.get("openeo_result")
    return isinstance(openeo_result, dict) and bool(openeo_result.get("vectorized_polygons"))


def has_gee_thumbnail_preview(raw_request: dict[str, Any] | None) -> bool:
    payload = raw_request or {}
    return bool(payload.get("image_url")) or str(payload.get("image_source") or "").strip() == "gee_thumbnail"

