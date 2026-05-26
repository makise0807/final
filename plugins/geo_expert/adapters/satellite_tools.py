from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import dependency_error, eo_cache_config, satellite_config

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def _normalize_bbox(value: Any) -> dict[str, float] | None:
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
    normalized = {
        "west": west,
        "south": south,
        "east": east,
        "north": north,
    }
    if value.get("crs"):
        normalized["crs"] = str(value.get("crs"))
    return normalized


def _bbox_overlap_score(left: dict[str, float], right: dict[str, float]) -> float:
    west = max(left["west"], right["west"])
    south = max(left["south"], right["south"])
    east = min(left["east"], right["east"])
    north = min(left["north"], right["north"])
    if west >= east or south >= north:
        return 0.0
    inter = (east - west) * (north - south)
    left_area = (left["east"] - left["west"]) * (left["north"] - left["south"])
    right_area = (right["east"] - right["west"]) * (right["north"] - right["south"])
    denom = max(left_area, right_area, 1e-9)
    return max(0.0, min(1.0, inter / denom))


def _safe_json_load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_sidecar_metadata(image_path: Path) -> tuple[dict[str, Any], str | None]:
    for candidate in (
        image_path.with_suffix(".json"),
        image_path.with_name(f"{image_path.stem}.metadata.json"),
    ):
        if not candidate.exists():
            continue
        metadata = _safe_json_load(candidate)
        if metadata:
            return metadata, str(candidate)
    return {}, None


def _infer_workflow_hint(filename: str) -> str | None:
    lowered = filename.lower()
    wf_match = re.search(r"wf[-_]?(\d{3})", lowered)
    if wf_match:
        return f"WF-{wf_match.group(1)}"
    if "slope" in lowered or "hill" in lowered:
        return "WF-002"
    if "river" in lowered or "flood" in lowered:
        return "WF-004"
    if "solar" in lowered or "panel" in lowered:
        return "WF-005"
    if "tod" in lowered or "metro" in lowered:
        return "WF-008"
    if "hazard" in lowered or "landslide" in lowered:
        return "WF-009"
    if "eco" in lowered or "habitat" in lowered:
        return "WF-010"
    return None


def _infer_provider(filename: str) -> str:
    lowered = filename.lower()
    if lowered.startswith("gee_") or "gee" in lowered:
        return "gee_preview"
    if lowered.startswith("s2_") or "sentinel" in lowered:
        return "gee_preview"
    return "unknown_or_gee_preview"


def _entry_from_image(path: Path, metadata: dict[str, Any], sidecar_path: str | None) -> dict[str, Any]:
    stat = path.stat()
    filename = path.name
    bbox = _normalize_bbox(metadata.get("aoi") or metadata.get("bbox"))
    case_id = str(metadata.get("case_id") or metadata.get("image_case_id") or "").strip() or None
    workflow_hint = str(metadata.get("workflow_hint") or _infer_workflow_hint(filename) or "").strip() or None
    provider = str(metadata.get("provider") or _infer_provider(filename))
    match_quality = str(metadata.get("match_quality") or ("precise_aoi" if bbox else ("workflow_hint_only" if workflow_hint else "unknown_aoi")))
    confidence = metadata.get("confidence")
    return {
        "image_path": str(path.resolve()),
        "filename": filename,
        "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "source": "eo_cache",
        "provider": provider,
        "aoi": bbox,
        "bbox": bbox,
        "case_id": case_id,
        "workflow_hint": workflow_hint,
        "is_formal_analysis": False,
        "sidecar_path": sidecar_path,
        "metadata_found": bool(sidecar_path),
        "match_quality": match_quality,
        "confidence": float(confidence) if confidence is not None else (0.95 if bbox else (0.6 if workflow_hint else 0.2)),
        "metadata": metadata,
    }


def build_eo_cache_index(*, cache_dir: str | None = None, output_path: str | None = None, write_output: bool = True) -> dict[str, Any]:
    cfg = eo_cache_config()
    resolved_cache_dir = Path(cache_dir or cfg.get("path") or "")
    if not resolved_cache_dir or not resolved_cache_dir.exists():
        return dependency_error(
            "eo_cache",
            f"EO cache directory not found: {resolved_cache_dir}" if resolved_cache_dir else "EO cache directory is not configured.",
            required_config=cfg["required_config"],
            error="eo_cache_missing" if resolved_cache_dir else "eo_cache_unconfigured",
            status="degraded",
        )

    entries: list[dict[str, Any]] = []
    for path in sorted(resolved_cache_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _IMAGE_SUFFIXES:
            continue
        metadata, sidecar_path = _read_sidecar_metadata(path)
        entries.append(_entry_from_image(path, metadata, sidecar_path))

    index_payload = {
        "success": True,
        "status": "success" if entries else "degraded",
        "cache_dir": str(resolved_cache_dir),
        "image_count": len(entries),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "images": entries,
        "warnings": [] if entries else ["No supported EO cache images found."],
    }

    if write_output:
        cfg_sat = satellite_config()
        target = Path(output_path or cfg_sat["cache_index_path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(index_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        index_payload["index_path"] = str(target)
    return index_payload


def _load_or_build_index(index_path: str | None = None) -> dict[str, Any]:
    target = Path(index_path or satellite_config()["cache_index_path"])
    current_cache_dir = str(Path(eo_cache_config().get("path") or "").resolve()) if eo_cache_config().get("path") else None
    if target.exists():
        payload = _safe_json_load(target)
        indexed_cache_dir = str(Path(payload.get("cache_dir")).resolve()) if payload.get("cache_dir") else None
        if payload.get("images") is not None and (not current_cache_dir or current_cache_dir == indexed_cache_dir):
            payload.setdefault("index_path", str(target))
            return payload
    return build_eo_cache_index(output_path=str(target), write_output=True)


def find_cached_satellite_image(
    aoi: dict[str, Any] | None = None,
    case_id: str | None = None,
    workflow_id: str | None = None,
    cache_index_path: str | None = None,
) -> dict[str, Any]:
    index_payload = _load_or_build_index(cache_index_path)
    if not index_payload.get("success"):
        return index_payload
    images = list(index_payload.get("images") or [])
    if not images:
        return {
            "success": False,
            "status": "degraded",
            "error": "eo_cache_empty",
            "message": "EO cache index is available but contains no images.",
            "cache_index_used": index_payload.get("index_path"),
        }

    requested_aoi = _normalize_bbox(aoi)
    case_token = str(case_id or "").strip().lower()
    workflow_token = str(workflow_id or "").strip().upper()

    selected: dict[str, Any] | None = None
    match_strategy = "latest_without_metadata"
    confidence = 0.2
    reason = "Fell back to the most recently modified cache image without AOI metadata."
    warnings = ["EO cache image selected without AOI metadata; not a precise AOI match."]

    if case_token:
        for item in images:
            item_case = str(item.get("case_id") or "").strip().lower()
            filename = str(item.get("filename") or "").lower()
            if item_case == case_token or case_token in filename:
                selected = item
                match_strategy = "case_id_exact"
                confidence = max(0.98, float(item.get("confidence") or 0.0))
                reason = f"Matched EO cache image by case_id '{case_id}'."
                warnings = []
                break

    if selected is None and workflow_token:
        for item in images:
            hint = str(item.get("workflow_hint") or "").strip().upper()
            if hint == workflow_token:
                selected = item
                match_strategy = "workflow_hint"
                confidence = max(0.78, float(item.get("confidence") or 0.0))
                reason = f"Matched EO cache image by workflow_hint '{workflow_id}'."
                warnings = []
                break

    if selected is None and requested_aoi is not None:
        best_score = 0.0
        for item in images:
            candidate = _normalize_bbox(item.get("aoi") or item.get("bbox"))
            if candidate is None:
                continue
            score = _bbox_overlap_score(requested_aoi, candidate)
            if score > best_score:
                best_score = score
                selected = item
        if selected is not None and best_score > 0:
            match_strategy = "bbox_overlap"
            confidence = round(max(float(selected.get("confidence") or 0.0), max(0.55, min(0.97, best_score))), 2)
            reason = f"Matched EO cache image by AOI bbox overlap ({best_score:.2f})."
            warnings = []
        else:
            selected = None

    if selected is None:
        selected = max(images, key=lambda item: str(item.get("modified_time") or ""))

    return {
        "success": True,
        "status": "success" if match_strategy != "latest_without_metadata" else "degraded",
        "service": "eo_cache",
        "source": "eo_cache",
        "used_real_service": False,
        "used_real_input": True,
        "selected_image": selected,
        "image_path": selected.get("image_path"),
        "aoi": selected.get("aoi"),
        "match_strategy": match_strategy,
        "confidence": confidence,
        "reason": reason,
        "aoi_used": requested_aoi,
        "cache_index_used": index_payload.get("index_path"),
        "sidecar_path": selected.get("sidecar_path"),
        "metadata_found": bool(selected.get("metadata_found")),
        "match_quality": selected.get("match_quality") or ("precise_aoi" if match_strategy == "bbox_overlap" else ("workflow_hint_only" if match_strategy == "workflow_hint" else "unknown_aoi")),
        "warnings": warnings,
        "limitations": ["EO cache preview is a read-only local input, not a formal satellite analysis product."],
    }


def _download_preview_image(url: str, target_path: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "GeoExpertSatellitePreview/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(data)


def _write_preview_sidecar(path: Path, payload: dict[str, Any]) -> str:
    sidecar = path.with_suffix(".json")
    sidecar.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(sidecar)


def acquire_satellite_preview(
    *,
    aoi: dict[str, Any] | None = None,
    bbox: dict[str, Any] | None = None,
    case_id: str | None = None,
    workflow_id: str | None = None,
    mode: str = "prepare_only",
    provider: str | None = None,
    time_range: list[str] | None = None,
    output_dir: str | None = None,
) -> dict[str, Any]:
    sat_cfg = satellite_config()
    effective_provider = str(provider or sat_cfg["provider"] or "cache_only").strip().lower()
    requested_aoi = _normalize_bbox(aoi or bbox)
    acquisition_plan = {
        "provider": effective_provider,
        "mode": mode,
        "aoi": requested_aoi,
        "case_id": case_id,
        "workflow_id": workflow_id,
        "time_range": list(time_range or ["2025-01-01", "2025-12-31"]),
        "allow_fetch": sat_cfg["allow_fetch"],
        "output_dir": output_dir or sat_cfg.get("output_dir"),
    }

    if mode == "prepare_only":
        return {
            "success": True,
            "status": "success",
            "provider": effective_provider,
            "mode": mode,
            "prepare_only": True,
            "acquisition_plan": acquisition_plan,
            "requires_verification": True,
            "warnings": ["Preparation only. No preview fetch was attempted."],
            "limitations": [
                "No satellite preview fetched in prepare_only mode.",
                "Not a formal satellite analysis.",
            ],
        }

    if mode == "cache_only":
        return find_cached_satellite_image(
            aoi=requested_aoi,
            case_id=case_id,
            workflow_id=workflow_id,
        )

    if mode != "preview":
        return {
            "success": False,
            "status": "degraded",
            "error": "unsupported_mode",
            "message": f"Unsupported satellite acquisition mode: {mode}",
            "acquisition_plan": acquisition_plan,
        }

    if not sat_cfg["allow_fetch"]:
        return {
            "success": False,
            "status": "degraded",
            "provider": effective_provider,
            "mode": mode,
            "error": "satellite_acquisition_disabled",
            "acquisition_plan": acquisition_plan,
            "next_action": "Set GEO_EXPERT_ALLOW_SATELLITE_FETCH=1 to allow preview fetch attempts.",
            "warnings": ["Preview fetch is disabled by policy."],
            "limitations": ["No fetch attempted because GEO_EXPERT_ALLOW_SATELLITE_FETCH is disabled."],
        }

    if effective_provider != "gee":
        return {
            "success": False,
            "status": "degraded",
            "provider": effective_provider,
            "mode": mode,
            "error": "unsupported_satellite_provider",
            "acquisition_plan": acquisition_plan,
            "warnings": [f"Unsupported provider '{effective_provider}' for preview fetch."],
            "limitations": ["Only GEE preview fetch is supported in this phase."],
        }

    if not sat_cfg["gee_enabled"]:
        return {
            "success": False,
            "status": "degraded",
            "provider": effective_provider,
            "mode": mode,
            "error": "gee_unavailable",
            "acquisition_plan": acquisition_plan,
            "warnings": ["Set GEO_EXPERT_GEE_ENABLED=1 before attempting GEE preview fetch."],
            "limitations": ["GEE preview path is disabled by default."],
        }

    if requested_aoi is None:
        return {
            "success": False,
            "status": "degraded",
            "provider": effective_provider,
            "mode": mode,
            "error": "aoi_missing",
            "acquisition_plan": acquisition_plan,
            "warnings": ["AOI is required for GEE preview fetch."],
            "limitations": ["Preview fetch requires a small valid AOI bbox."],
        }

    try:
        from ..geo_database.image_provider_contracts import ImageProviderRequest
        from ..geo_database.image_provider_gee import gee_fetch_thumbnail_preview
    except Exception:
        return {
            "success": False,
            "status": "degraded",
            "provider": effective_provider,
            "mode": mode,
            "error": "gee_unavailable",
            "acquisition_plan": acquisition_plan,
            "warnings": ["GEE preview dependency is unavailable in this environment."],
            "limitations": ["No preview fetch attempted because GEE modules could not be loaded."],
        }

    request = ImageProviderRequest(
        provider="gee",
        task="satellite_preview",
        aoi=requested_aoi,
        time_range=list(time_range or ["2025-01-01", "2025-12-31"]),
        output_mode="thumbnail",
    )
    gee_result = gee_fetch_thumbnail_preview(request)
    if not gee_result.get("success"):
        error = str(gee_result.get("error") or "gee_unavailable")
        if "authenticate" in error or "auth" in error:
            error = "gee_not_authenticated"
        return {
            "success": False,
            "status": "degraded",
            "provider": effective_provider,
            "mode": mode,
            "error": error,
            "acquisition_plan": acquisition_plan,
            "warnings": list(gee_result.get("warnings") or []),
            "limitations": list(gee_result.get("limitations") or []),
        }

    thumb_url = str(gee_result.get("thumbnail_url") or "").strip()
    if not thumb_url:
        return {
            "success": False,
            "status": "degraded",
            "provider": effective_provider,
            "mode": mode,
            "error": "gee_preview_missing_url",
            "acquisition_plan": acquisition_plan,
            "warnings": ["GEE preview succeeded but returned no thumbnail URL."],
            "limitations": list(gee_result.get("limitations") or []),
        }

    eo_cfg = eo_cache_config()
    cache_dir = Path(output_dir or sat_cfg.get("output_dir") or eo_cfg.get("path") or Path("outputs") / "geo_expert" / "eo_cache_preview")
    filename = f"gee_preview_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.png"
    target_path = cache_dir / filename
    try:
        _download_preview_image(thumb_url, target_path)
    except Exception as exc:
        return {
            "success": False,
            "status": "degraded",
            "provider": effective_provider,
            "mode": mode,
            "error": "gee_preview_download_failed",
            "acquisition_plan": acquisition_plan,
            "warnings": [f"Failed to download GEE thumbnail preview: {exc}"],
            "limitations": list(gee_result.get("limitations") or []),
        }

    sidecar_payload = {
        "provider": "gee",
        "source": "eo_cache",
        "workflow_hint": workflow_id,
        "case_id": case_id,
        "aoi": requested_aoi,
        "match_quality": "precise_aoi",
        "confidence": 0.9,
        "time_range": acquisition_plan["time_range"],
        "is_formal_analysis": False,
        "is_export": False,
        "geotiff_download": False,
        "requires_verification": True,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }
    sidecar_path = _write_preview_sidecar(target_path, sidecar_payload)
    return {
        "success": True,
        "status": "success",
        "provider": "gee",
        "service": "gee_preview",
        "mode": mode,
        "used_real_service": True,
        "used_real_input": True,
        "image_path": str(target_path),
        "aoi": requested_aoi,
        "sidecar_path": sidecar_path,
        "thumbnail_url": thumb_url,
        "match_strategy": "fetched_preview",
        "confidence": 0.9,
        "reason": "Fetched a GEE thumbnail preview for the requested AOI.",
        "requires_verification": True,
        "is_formal_analysis": False,
        "is_export": False,
        "geotiff_download": False,
        "warnings": list(gee_result.get("warnings") or []),
        "limitations": list(gee_result.get("limitations") or []) + ["Preview imagery only; not a formal satellite analysis."],
        "acquisition_plan": acquisition_plan,
    }


def satellite_status() -> dict[str, Any]:
    sat_cfg = satellite_config()
    cache_info = _load_or_build_index(sat_cfg["cache_index_path"])
    return {
        "provider": sat_cfg["provider"],
        "allow_fetch": sat_cfg["allow_fetch"],
        "gee_enabled": sat_cfg["gee_enabled"],
        "cache_available": bool(cache_info.get("success")),
        "cache_image_count": int(cache_info.get("image_count") or 0),
        "cache_index_path": cache_info.get("index_path") or sat_cfg["cache_index_path"],
    }


__all__ = [
    "acquire_satellite_preview",
    "build_eo_cache_index",
    "find_cached_satellite_image",
    "satellite_status",
]
