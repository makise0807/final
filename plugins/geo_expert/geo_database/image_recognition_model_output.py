"""Model-output conversion helpers for image-recognition adapters."""

from __future__ import annotations

from typing import Any


def pixel_to_lonlat(x: float, y: float, aoi: dict[str, Any], image_width: int, image_height: int) -> tuple[float, float]:
    west = float(aoi["west"])
    south = float(aoi["south"])
    east = float(aoi["east"])
    north = float(aoi["north"])
    lon = west + (float(x) / float(image_width)) * (east - west)
    lat = north - (float(y) / float(image_height)) * (north - south)
    return round(lon, 8), round(lat, 8)


def mask_polygon_to_geo_polygon(points: list[list[float]], aoi: dict[str, Any], image_width: int, image_height: int) -> dict[str, Any]:
    coordinates = [list(pixel_to_lonlat(x, y, aoi, image_width, image_height)) for x, y in points]
    if coordinates and coordinates[0] != coordinates[-1]:
        coordinates.append(list(coordinates[0]))
    return {"type": "Polygon", "coordinates": [coordinates]}


def bbox_to_geo_polygon(x1: float, y1: float, x2: float, y2: float, aoi: dict[str, Any], image_width: int, image_height: int) -> dict[str, Any]:
    west_south = pixel_to_lonlat(x1, y2, aoi, image_width, image_height)
    east_north = pixel_to_lonlat(x2, y1, aoi, image_width, image_height)
    west = west_south[0]
    south = west_south[1]
    east = east_north[0]
    north = east_north[1]
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


def polygon_bbox(geometry: dict[str, Any]) -> list[float]:
    coords = (((geometry or {}).get("coordinates") or [[]])[0]) if isinstance(geometry, dict) else []
    xs = [float(point[0]) for point in coords if isinstance(point, (list, tuple)) and len(point) >= 2]
    ys = [float(point[1]) for point in coords if isinstance(point, (list, tuple)) and len(point) >= 2]
    if not xs or not ys:
        return [0.0, 0.0, 0.0, 0.0]
    return [min(xs), min(ys), max(xs), max(ys)]


def model_class_to_detection_label(class_name: str) -> str:
    lowered = str(class_name or "").strip().lower()
    if lowered in {"building", "house", "roof", "structure"}:
        return "suspected_building_or_concrete_surface"
    if lowered in {"car", "truck", "bus"}:
        return "vehicle_or_activity_indicator"
    if lowered in {"parking lot", "parking_lot", "road", "pavement", "concrete", "concrete_surface"}:
        return "concrete_surface_indicator"
    if lowered in {"solar panel", "solar_panel"}:
        return "suspected_solar_panel"
    return "unknown_object"


def model_class_to_evidence(class_name: str) -> list[str]:
    lowered = str(class_name or "").strip().lower()
    if lowered in {"building", "house", "roof", "structure"}:
        return ["generic_object_detection", "roof_or_structure_indicator", "requires_landuse_review"]
    if lowered in {"car", "truck", "bus"}:
        return ["generic_object_detection", "vehicle_or_activity_indicator", "requires_context_review"]
    if lowered in {"parking lot", "parking_lot", "road", "pavement", "concrete", "concrete_surface"}:
        return ["generic_object_detection", "concrete_surface_indicator", "requires_context_review"]
    if lowered in {"solar panel", "solar_panel"}:
        return ["generic_object_detection", "panel_like_signature", "requires_landuse_review"]
    return ["generic_object_detection", "unknown_object", "requires_context_review"]


__all__ = [
    "bbox_to_geo_polygon",
    "mask_polygon_to_geo_polygon",
    "model_class_to_detection_label",
    "model_class_to_evidence",
    "pixel_to_lonlat",
    "polygon_bbox",
]
