from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .geotiff_metadata import build_geotiff_metadata
from .openeo_config import openeo_runtime_config


def _cache_dir() -> Path:
    return Path(openeo_runtime_config()["cache_dir"])


def list_geotiff_cache() -> dict[str, Any]:
    root = _cache_dir()
    root.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    for sidecar in sorted(root.glob("*.json")):
        try:
            items.append(json.loads(sidecar.read_text(encoding="utf-8")))
        except Exception:
            items.append({"path": str(sidecar), "error": "invalid_sidecar"})
    return {"success": True, "cache_dir": str(root), "count": len(items), "items": items}


def find_geotiff_cache(aoi: dict[str, Any] | None, date_range: dict[str, Any] | None, bands: list[str] | None) -> dict[str, Any]:
    listing = list_geotiff_cache()
    for item in listing.get("items") or []:
        if item.get("aoi") == aoi and item.get("date_range") == (date_range or {}) and list(item.get("bands") or []) == list(bands or []):
            return {"success": True, "status": "success", "cache_hit": True, "metadata": item}
    return {"success": True, "status": "degraded", "cache_hit": False, "reason": "geotiff_cache_miss"}


def write_geotiff_sidecar(
    *,
    artifact_id: str,
    path: str,
    aoi: dict[str, Any] | None,
    date_range: dict[str, Any] | None,
    bands: list[str] | None,
    provider: str | None,
    crs: str | None = None,
    resolution: int = 10,
) -> dict[str, Any]:
    root = _cache_dir()
    root.mkdir(parents=True, exist_ok=True)
    metadata = build_geotiff_metadata(
        artifact_id=artifact_id,
        path=path,
        aoi=aoi,
        date_range=date_range,
        bands=bands,
        provider=provider,
        crs=crs,
        resolution=resolution,
    )
    sidecar = Path(path).with_suffix(".json")
    sidecar.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "metadata": metadata, "sidecar_path": str(sidecar)}
