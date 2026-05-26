"""Landcover vector adapter for preliminary image recognition."""

from __future__ import annotations

from typing import Any


CLASS_MAP = {
    "urban": "suspected_building_or_concrete_surface",
    "building": "suspected_building_or_concrete_surface",
    "concrete_surface": "suspected_building_or_concrete_surface",
    "bare_soil": "possible_bare_ground_or_construction_site",
    "solar_panel": "suspected_solar_panel",
    "vegetation": "background_or_low_risk",
    "agriculture": "background_or_low_risk",
    "water": "background_or_low_risk",
}


def map_landcover_class(label: str) -> str:
    return CLASS_MAP.get(str(label or "").strip(), "suspected_building_or_concrete_surface")


def build_landcover_evidence(
    *,
    mapped_class: str,
    workflow_id: str,
    inside_agricultural_zone: bool = False,
) -> list[str]:
    evidence: list[str] = []
    if mapped_class in {"suspected_building_or_concrete_surface", "possible_bare_ground_or_construction_site"}:
        evidence.append("non_vegetation_signature")
    if mapped_class == "suspected_solar_panel":
        evidence.extend(["dark_rectangular_panel_signature", "high_reflectance_or_panel_pattern"])
    if inside_agricultural_zone:
        evidence.append("inside_agricultural_zone" if workflow_id == "WF-001" else "agricultural_zone_context")
    return evidence or ["preclassified_surface"]


def has_vectorized_polygons(payload: Any) -> bool:
    return isinstance(payload, dict) and bool(payload.get("vectorized_polygons"))

