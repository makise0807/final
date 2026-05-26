"""Render a lightweight PNG preview for detection overlays."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _load_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None
    return Image, ImageDraw, ImageFont


def _as_feature_collection(detections_geojson: Any) -> dict[str, Any]:
    if isinstance(detections_geojson, dict) and detections_geojson.get("type") == "FeatureCollection":
        return dict(detections_geojson)
    return {"type": "FeatureCollection", "features": []}


def _collect_points(feature_collection: dict[str, Any]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for feature in feature_collection.get("features") or []:
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "Polygon":
            continue
        for ring in geometry.get("coordinates") or []:
            for point in ring or []:
                if isinstance(point, (list, tuple)) and len(point) >= 2:
                    try:
                        points.append((float(point[0]), float(point[1])))
                    except Exception:
                        continue
    return points


def _bounds(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    if not points:
        return (0.0, 0.0, 100.0, 100.0)
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    if min_x == max_x:
        max_x += 1.0
    if min_y == max_y:
        max_y += 1.0
    return (min_x, min_y, max_x, max_y)


def _normalize_point(
    point: tuple[float, float],
    bounds: tuple[float, float, float, float],
    canvas_width: int,
    canvas_height: int,
    margin: int,
) -> tuple[float, float]:
    min_x, min_y, max_x, max_y = bounds
    usable_width = canvas_width - margin * 2
    usable_height = canvas_height - margin * 2
    x = margin + ((point[0] - min_x) / (max_x - min_x)) * usable_width
    y = margin + ((max_y - point[1]) / (max_y - min_y)) * usable_height
    return (x, y)


def _draw_placeholder_background(draw: Any, width: int, height: int) -> None:
    draw.rectangle((0, 0, width, height), fill="#F8F5EC")
    draw.ellipse((width - 220, 28, width - 40, 208), fill="#F4C97A")
    draw.ellipse((36, height - 180, 250, height + 20), fill="#D7F0EE")
    draw.rounded_rectangle((36, 36, width - 36, height - 36), radius=32, outline="#D8B36A", width=3, fill="#FFFDFC")
    for y in range(110, height - 90, 56):
        draw.line((70, y, width - 70, y), fill="#E8E1D0", width=1)
    for x in range(90, width - 90, 74):
        draw.line((x, 80, x, height - 80), fill="#EEF3F2", width=1)


def render_detection_overlay_preview(
    detections_geojson: Any,
    output_path: str | Path,
    background_image_path: str | Path | None = None,
    overlay_aoi: dict[str, Any] | None = None,
    title: str = "Hermes Geo-Legal Preliminary Detection",
) -> dict[str, Any]:
    pillow = _load_pillow()
    if pillow is None:
        return {"success": False, "error": "pillow_not_available", "fallback": "geojson_only"}

    Image, ImageDraw, ImageFont = pillow
    width, height = 1280, 720
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    background_mode = "placeholder"
    if background_image_path and Path(background_image_path).exists():
        image = Image.open(background_image_path).convert("RGBA").resize((width, height))
        background_mode = "image"
    else:
        image = Image.new("RGBA", (width, height), "#F8F5EC")
        placeholder_draw = ImageDraw.Draw(image, "RGBA")
        _draw_placeholder_background(placeholder_draw, width, height)

    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.load_default()
    feature_collection = _as_feature_collection(detections_geojson)
    features = feature_collection.get("features") or []
    all_points = _collect_points(feature_collection)
    if isinstance(overlay_aoi, dict) and {
        "west",
        "south",
        "east",
        "north",
    }.issubset(overlay_aoi):
        try:
            bounds = (
                float(overlay_aoi["west"]),
                float(overlay_aoi["south"]),
                float(overlay_aoi["east"]),
                float(overlay_aoi["north"]),
            )
        except Exception:
            bounds = _bounds(all_points)
    else:
        bounds = _bounds(all_points)

    stroke = "#F97316"
    fill = (253, 186, 116, 90)
    label_fill = "#7C2D12"
    margin = 90

    for index, feature in enumerate(features, start=1):
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "Polygon":
            continue
        rings = geometry.get("coordinates") or []
        if not rings:
            continue
        ring = rings[0] or []
        normalized_ring: list[tuple[float, float]] = []
        for point in ring:
            if isinstance(point, (list, tuple)) and len(point) >= 2:
                try:
                    normalized_ring.append(
                        _normalize_point((float(point[0]), float(point[1])), bounds, width, height, margin)
                    )
                except Exception:
                    continue
        if len(normalized_ring) < 3:
            continue
        draw.polygon(normalized_ring, outline=stroke, fill=fill, width=4)
        label = "Suspected area"
        label_point = normalized_ring[0]
        label_box = (label_point[0] + 8, label_point[1] - 24, label_point[0] + 96, label_point[1] - 2)
        draw.rounded_rectangle(label_box, radius=8, fill="#FFF7ED", outline=stroke, width=2)
        draw.text((label_box[0] + 8, label_box[1] + 5), label, fill=label_fill, font=font)

    draw.rounded_rectangle((36, 24, 600, 78), radius=18, fill=(255, 255, 255, 235), outline="#D1D5DB", width=2)
    draw.text((56, 42), title, fill="#111827", font=font)

    badges = [
        ("Preliminary Detection", "#FFF7ED", "#9A3412"),
        ("Requires Verification", "#ECFEFF", "#155E75"),
        ("Not Legal Conclusion", "#F8FAFC", "#334155"),
        ("No GeoTIFF / Export", "#FEF2F2", "#991B1B"),
    ]
    badge_x = 46
    badge_y = height - 118
    for text, bg, fg in badges:
        badge_w = max(170, 12 + len(text) * 7)
        draw.rounded_rectangle((badge_x, badge_y, badge_x + badge_w, badge_y + 32), radius=14, fill=bg, outline="#CBD5E1")
        draw.text((badge_x + 10, badge_y + 9), text, fill=fg, font=font)
        badge_x += badge_w + 10

    legend_box = (width - 360, height - 142, width - 40, height - 38)
    draw.rounded_rectangle(legend_box, radius=18, fill=(255, 255, 255, 235), outline="#CBD5E1", width=2)
    draw.text((legend_box[0] + 18, legend_box[1] + 16), "Legend", fill="#111827", font=font)
    draw.rectangle((legend_box[0] + 18, legend_box[1] + 46, legend_box[0] + 44, legend_box[1] + 72), fill=fill, outline=stroke, width=3)
    draw.text((legend_box[0] + 56, legend_box[1] + 50), "疑似區塊 / suspected area", fill="#374151", font=font)

    if not features:
        draw.rounded_rectangle((430, 300, 850, 360), radius=18, fill=(255, 255, 255, 230), outline="#D1D5DB", width=2)
        draw.text((456, 324), "No detection features available. GeoJSON only fallback.", fill="#475569", font=font)

    image.convert("RGB").save(output, format="PNG")
    return {
        "success": True,
        "output_path": str(output),
        "feature_count": len(features),
        "background": background_mode,
        "bounds_used": {
            "west": float(bounds[0]),
            "south": float(bounds[1]),
            "east": float(bounds[2]),
            "north": float(bounds[3]),
        },
        "warnings": [],
    }


__all__ = ["render_detection_overlay_preview"]
