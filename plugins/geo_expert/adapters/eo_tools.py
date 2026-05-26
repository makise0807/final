from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .config import dependency_error, eo_cache_config, openeo_config

_EO_CACHE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def _resolve_local_image_path(path_like: str | None) -> Path | None:
    if not path_like:
        return None
    candidate = Path(path_like)
    if candidate.exists():
        return candidate
    return None


def _read_sidecar_metadata(image_path: Path) -> dict[str, Any]:
    for candidate in (
        image_path.with_suffix(".json"),
        image_path.with_name(f"{image_path.stem}.metadata.json"),
    ):
        if not candidate.exists():
            continue
        try:
            return json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue
    return {}


def list_eo_cache_images() -> dict[str, Any]:
    cfg = eo_cache_config()
    if not cfg["configured"]:
        return dependency_error(
            "eo_cache",
            "EO cache directory is not configured.",
            required_config=cfg["required_config"],
            error="eo_cache_unconfigured",
            status="degraded",
        )
    cache_dir = Path(str(cfg["path"]))
    if not cache_dir.exists():
        return dependency_error(
            "eo_cache",
            f"EO cache directory not found: {cache_dir}",
            required_config=cfg["required_config"],
            error="eo_cache_missing",
            status="degraded",
        )
    items: list[dict[str, Any]] = []
    for path in sorted(cache_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _EO_CACHE_SUFFIXES:
            continue
        metadata = _read_sidecar_metadata(path)
        items.append(
            {
                "image_path": str(path),
                "filename": path.name,
                "source": "eo_cache",
                "used_real_input": True,
                "metadata": metadata,
                "aoi": metadata.get("aoi"),
                "timestamp": metadata.get("timestamp") or metadata.get("date"),
                "size_bytes": path.stat().st_size,
            }
        )
    return {
        "success": True,
        "status": "success",
        "service": "eo_cache",
        "cache_dir": str(cache_dir),
        "image_count": len(items),
        "images": items,
        "used_real_service": False,
        "used_real_input": bool(items),
        "warnings": [] if items else ["EO cache directory is readable but contains no supported image files."],
        "limitations": ["EO cache inputs are local read-only references, not formal satellite analysis."],
    }


def select_eo_cache_image(
    *,
    workflow_id: str | None = None,
    case_id: str | None = None,
    preferred_name: str | None = None,
) -> dict[str, Any]:
    listed = list_eo_cache_images()
    if not listed.get("success"):
        return listed
    images = list(listed.get("images") or [])
    if not images:
        listed["status"] = "degraded"
        listed["error"] = "eo_cache_empty"
        return listed
    wanted = [str(value).lower() for value in (preferred_name, case_id, workflow_id) if value]
    selected = None
    for token in wanted:
        selected = next((item for item in images if token in str(item.get("filename", "")).lower()), None)
        if selected:
            break
    if selected is None:
        selected = images[0]
    return {
        "success": True,
        "status": "success",
        "service": "eo_cache",
        "selected_image": selected,
        "used_real_service": False,
        "used_real_input": True,
        "warnings": [],
        "limitations": ["EO cache image selection is a local read-only fallback path."],
    }


def _file_not_found(path_like: str | None) -> dict[str, Any]:
    return {
        "success": False,
        "error": "local_input_missing",
        "message": f"Local input image not found: {path_like}",
    }


def generate_openeo_bbox(lon: float, lat: float, size_meters: float = 100.0) -> dict[str, Any]:
    if size_meters <= 0:
        return {
            "success": False,
            "error": "invalid_size_meters",
            "message": "size_meters must be greater than 0.",
        }
    meters_per_degree = 111_320.0
    half_deg = (size_meters / 2.0) / meters_per_degree
    return {
        "success": True,
        "operation": "bbox",
        "bbox": {
            "west": round(lon - half_deg, 8),
            "south": round(lat - half_deg, 8),
            "east": round(lon + half_deg, 8),
            "north": round(lat + half_deg, 8),
        },
        "approximation": "simple_wgs84_degree_approximation",
    }


def calculate_local_vari(image_path: str) -> dict[str, Any]:
    path = _resolve_local_image_path(image_path)
    if path is None:
        return _file_not_found(image_path)
    return {
        "success": True,
        "operation": "vari",
        "mode": "local_only",
        "input_path": str(path.resolve()),
        "analysis_summary": "Local VARI analysis prepared from an existing image path without external services.",
    }


def detect_local_change(image_before_path: str, image_after_path: str) -> dict[str, Any]:
    before = _resolve_local_image_path(image_before_path)
    after = _resolve_local_image_path(image_after_path)
    if before is None:
        return _file_not_found(image_before_path)
    if after is None:
        return _file_not_found(image_after_path)
    return {
        "success": True,
        "operation": "change",
        "mode": "local_only",
        "before_path": str(before.resolve()),
        "after_path": str(after.resolve()),
        "analysis_summary": "Local change analysis prepared from two existing image paths without external services.",
    }


def extract_local_water_features(image_path: str) -> dict[str, Any]:
    path = _resolve_local_image_path(image_path)
    if path is None:
        return _file_not_found(image_path)
    return {
        "success": True,
        "operation": "water",
        "mode": "local_only",
        "input_path": str(path.resolve()),
        "analysis_summary": "Local visible-band water feature extraction prepared without external services.",
    }


def classify_local_kmeans(image_path: str, n_clusters: int = 3) -> dict[str, Any]:
    path = _resolve_local_image_path(image_path)
    if path is None:
        return _file_not_found(image_path)
    if int(n_clusters) <= 1:
        return {
            "success": False,
            "error": "invalid_cluster_count",
            "message": "n_clusters must be greater than 1.",
        }
    return {
        "success": True,
        "operation": "kmeans",
        "mode": "local_only",
        "input_path": str(path.resolve()),
        "n_clusters": int(n_clusters),
        "analysis_summary": "Local K-means preparation completed without external services.",
    }


def eo_local_analysis(operation: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    params = dict(parameters or {})
    op = str(operation or "").strip().lower()
    if op == "bbox":
        return generate_openeo_bbox(
            lon=float(params.get("lon", 0.0)),
            lat=float(params.get("lat", 0.0)),
            size_meters=float(params.get("size_meters", 100.0)),
        )
    if op == "vari":
        return calculate_local_vari(str(params.get("image_path") or params.get("tiff_path") or ""))
    if op == "change":
        return detect_local_change(
            str(params.get("image_before_path") or ""),
            str(params.get("image_after_path") or ""),
        )
    if op == "water":
        return extract_local_water_features(str(params.get("image_path") or params.get("tiff_path") or ""))
    if op == "kmeans":
        return classify_local_kmeans(
            str(params.get("image_path") or params.get("tiff_path") or ""),
            n_clusters=int(params.get("n_clusters", 3)),
        )
    return {
        "success": False,
        "error": "unsupported_operation",
        "message": f"Unsupported eo_local_analysis operation: {operation}",
        "supported_operations": ["bbox", "vari", "change", "water", "kmeans"],
    }


def openeo_status() -> dict[str, Any]:
    cfg = openeo_config()
    if not cfg["configured"]:
        return dependency_error(
            "openeo",
            "OpenEO is not configured or unavailable.",
            required_config=cfg["required_config"],
            configured=False,
            disabled_by_default=True,
            submit_enabled=False,
            download_enabled=False,
        )
    return {
        "success": True,
        "dependency": "openeo",
        "configured": True,
        "disabled_by_default": True,
        "submit_enabled": False,
        "download_enabled": False,
        "service_url_present": bool(cfg.get("url")),
    }


def prepare_openeo_request(operation: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = openeo_config()
    params = dict(parameters or {})
    if not cfg["configured"]:
        return dependency_error(
            "openeo",
            "OpenEO is not configured or unavailable.",
            required_config=cfg["required_config"],
            operation=operation,
            approval_required=True,
        )
    fingerprint = hashlib.sha256(f"{operation}|{params}".encode("utf-8")).hexdigest()[:12]
    return {
        "success": True,
        "operation": str(operation or "").strip(),
        "parameters": params,
        "prepare_only": True,
        "approval_required": True,
        "submit_performed": False,
        "download_performed": False,
        "request_fingerprint": fingerprint,
        "message": "OpenEO request prepared only. Submit/download/export remain disabled-by-default.",
    }


__all__ = [
    "calculate_local_vari",
    "classify_local_kmeans",
    "detect_local_change",
    "eo_local_analysis",
    "extract_local_water_features",
    "generate_openeo_bbox",
    "list_eo_cache_images",
    "openeo_status",
    "prepare_openeo_request",
    "select_eo_cache_image",
]
