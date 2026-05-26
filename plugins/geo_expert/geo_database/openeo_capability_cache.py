"""Capability cache helpers for OpenEO metadata discovery."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CAPABILITIES_CACHE_PATH = Path(".hermes/openeo/capabilities_cache.json")
DEFAULT_CAPABILITIES_TTL_SECONDS = 86400


def _resolve_cache_path(path: str | Path | None = None) -> Path:
    return Path(path) if path is not None else DEFAULT_CAPABILITIES_CACHE_PATH


def save_capabilities_cache(capabilities: dict[str, Any], path: str | Path | None = None) -> dict[str, Any]:
    cache_path = _resolve_cache_path(path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "backend_url": capabilities.get("backend_url"),
        "source": "real_cached",
        "retrieved_at": capabilities.get("retrieved_at"),
        "collections": capabilities.get("collections", []),
        "processes": capabilities.get("processes", []),
        "backend_extensions": capabilities.get("backend_extensions", []),
        "unknown_processes": capabilities.get("unknown_processes", []),
        "warnings": capabilities.get("warnings", []),
        "raw_summary": {
            "collections_count": len(capabilities.get("collections", [])),
            "processes_count": len(capabilities.get("processes", [])) + len(capabilities.get("backend_extensions", [])),
        },
    }
    cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_capabilities_cache(path: str | Path | None = None, backend_url: str | None = None) -> dict[str, Any]:
    cache_path = _resolve_cache_path(path)
    if not cache_path.exists():
        return {"success": False, "error": "cache_not_found", "path": str(cache_path)}
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    if backend_url and payload.get("backend_url") != backend_url:
        return {
            "success": False,
            "error": "backend_url_mismatch",
            "path": str(cache_path),
            "cached_backend_url": payload.get("backend_url"),
        }
    warnings = list(payload.get("warnings", []))
    if not is_capabilities_cache_fresh(payload):
        warnings.append("capabilities_cache_stale")
    payload["warnings"] = list(dict.fromkeys(warnings))
    payload["success"] = True
    payload["path"] = str(cache_path)
    return payload


def is_capabilities_cache_fresh(capabilities: dict[str, Any], ttl_seconds: int = DEFAULT_CAPABILITIES_TTL_SECONDS) -> bool:
    retrieved_at = capabilities.get("retrieved_at")
    if not retrieved_at:
        return False
    try:
        dt = datetime.fromisoformat(retrieved_at)
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds() <= ttl_seconds


def clear_capabilities_cache(path: str | Path | None = None) -> dict[str, Any]:
    cache_path = _resolve_cache_path(path)
    existed = cache_path.exists()
    if existed:
        cache_path.unlink()
    return {"success": True, "path": str(cache_path), "deleted": existed}
