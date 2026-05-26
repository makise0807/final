"""Deterministic local image fixtures for overlay and detector tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _normalize_aoi(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    try:
        west = float(value["west"])
        south = float(value["south"])
        east = float(value["east"])
        north = float(value["north"])
    except Exception:
        return None
    if west >= east or south >= north:
        return None
    return {
        "west": west,
        "south": south,
        "east": east,
        "north": north,
    }


def load_local_image_fixture(
    case_id: str,
    fixtures_root: str | Path = "data/geo_fixtures",
) -> dict[str, Any]:
    fixture_root = Path(fixtures_root) / str(case_id or "").strip()
    if not str(case_id or "").strip() or not fixture_root.exists():
        return {"success": False, "error": "fixture_not_found"}

    metadata_path = fixture_root / "metadata.json"
    if not metadata_path.exists():
        return {"success": False, "error": "metadata_missing"}

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except Exception:
        return {"success": False, "error": "metadata_missing"}

    image_ref = str(metadata.get("image_path") or "").strip()
    if not image_ref:
        return {"success": False, "error": "image_missing"}

    image_path = (fixture_root / image_ref).resolve()
    if not image_path.exists() or not image_path.is_file():
        return {"success": False, "error": "image_missing"}

    aoi = _normalize_aoi(metadata.get("aoi"))
    if aoi is None:
        return {"success": False, "error": "invalid_aoi"}

    expected_geojson_path = fixture_root / "expected_detections.geojson"
    result = {
        "success": True,
        "case_id": str(metadata.get("case_id") or case_id),
        "image_path": str(image_path),
        "aoi": aoi,
        "crs": str(metadata.get("crs") or "EPSG:4326"),
        "source": str(metadata.get("source") or "local_fixture"),
        "warnings": [],
        "limitations": [
            "Local fixture image only",
            "Preliminary visual indicator only",
            "Not a formal legal conclusion",
        ],
        "is_geotiff": False,
        "is_export": False,
        "is_formal_analysis": False,
        "description": str(
            metadata.get("description")
            or "Local fixture image for deterministic overlay testing"
        ),
        "metadata_path": str(metadata_path.resolve()),
    }
    if expected_geojson_path.exists():
        result["expected_detections_geojson_path"] = str(expected_geojson_path.resolve())
    return result


__all__ = ["load_local_image_fixture"]
