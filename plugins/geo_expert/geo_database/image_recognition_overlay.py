"""Overlay builders for preliminary detection outputs."""

from __future__ import annotations

from typing import Any


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def build_detection_overlay(result: Any) -> dict[str, Any]:
    payload = _as_dict(result)
    if payload.get("mode") in {"export", "geotiff", "download"}:
        return {"success": False, "error": "image_recognition_overlay_export_mode_rejected"}
    if not payload.get("not_formal_analysis") or not payload.get("requires_verification"):
        return {"success": False, "error": "image_recognition_overlay_requires_preliminary_flags"}

    geojson = _as_dict(payload.get("geojson"))
    if geojson.get("type") != "FeatureCollection":
        geojson = {"type": "FeatureCollection", "features": list(geojson.get("features") or [])}

    return {
        "success": True,
        "overlay_type": "geojson_detection_overlay",
        "geojson": geojson,
        "style": {
            "suspected_building_or_concrete_surface": {
                "stroke": "#F97316",
                "fill": "#FDBA74",
                "fillOpacity": 0.35,
            },
            "suspected_solar_panel": {
                "stroke": "#0F766E",
                "fill": "#5EEAD4",
                "fillOpacity": 0.30,
            },
            "possible_bare_ground_or_construction_site": {
                "stroke": "#B45309",
                "fill": "#FDE68A",
                "fillOpacity": 0.30,
            },
        },
        "legend": [
            {
                "label": "疑似建物 / 水泥鋪面",
                "color": "#F97316",
                "meaning": "Preliminary suspected area, requires verification",
            }
        ],
        "safe_display": True,
        "warnings": list(payload.get("warnings") or []),
        "limitations": list(payload.get("limitations") or []),
    }


__all__ = ["build_detection_overlay"]
