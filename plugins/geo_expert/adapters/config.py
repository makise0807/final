from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PLUGIN_ROOT / "data"
WORKFLOW_DB_PATH = DATA_ROOT / "workflow_db" / "expert_workflows.json"
REGULATIONS_ROOT = DATA_ROOT / "regulations"
GEO_FIXTURES_ROOT = DATA_ROOT / "geo_fixtures"
SPATIAL_ROOT = DATA_ROOT / "spatial"

_DEFAULT_CHROMA_REGULATIONS_ALIASES = ["geo_regulations", "urban_regulations"]
_DEFAULT_CHROMA_WORKFLOW_ALIASES = ["geo_workflows", "urban_regulations"]
_DEFAULT_CHROMA_MAP_ALIASES = ["geo_map_data", "urban_regulations"]


def get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def dependency_error(
    dependency: str,
    message: str,
    *,
    required_config: list[str] | None = None,
    error: str = "dependency_unavailable",
    **extra: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "success": False,
        "error": error,
        "dependency": dependency,
        "message": message,
        "required_config": list(required_config or []),
    }
    payload.update(extra)
    return payload


def plugin_paths() -> dict[str, str]:
    return {
        "plugin_root": str(PLUGIN_ROOT),
        "data_root": str(DATA_ROOT),
        "workflow_db_path": str(WORKFLOW_DB_PATH),
        "regulations_root": str(REGULATIONS_ROOT),
        "geo_fixtures_root": str(GEO_FIXTURES_ROOT),
        "spatial_root": str(SPATIAL_ROOT),
    }


def _parse_alias_list(raw: str | None, defaults: list[str]) -> list[str]:
    if not raw:
        return list(defaults)
    parts = [item.strip() for item in str(raw).replace(";", ",").split(",")]
    cleaned = [item for item in parts if item]
    return cleaned or list(defaults)


def postgis_config() -> dict[str, Any]:
    database_url = get_env("DATABASE_URL")
    if database_url:
        return {
            "configured": True,
            "database_url": database_url,
            "required_config": ["DATABASE_URL"],
        }
    host = get_env("POSTGRES_HOST")
    user = get_env("POSTGRES_USER")
    password = get_env("POSTGRES_PASSWORD")
    db = get_env("POSTGRES_DB")
    port = get_env("POSTGRES_PORT", "5432")
    configured = all([host, user, password, db])
    return {
        "configured": configured,
        "database_url": None,
        "host": host,
        "user": user,
        "password_present": bool(password),
        "db": db,
        "port": port,
        "required_config": ["POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "POSTGRES_PORT"],
    }


def chroma_config() -> dict[str, Any]:
    url = get_env("CHROMA_URL")
    host = get_env("CHROMA_HOST", "localhost")
    port = get_env("CHROMA_PORT", "8000")
    regulations_aliases = _parse_alias_list(
        get_env("CHROMA_COLLECTION_REGULATIONS"),
        _DEFAULT_CHROMA_REGULATIONS_ALIASES,
    )
    workflows_aliases = _parse_alias_list(
        get_env("CHROMA_COLLECTION_WORKFLOWS"),
        _DEFAULT_CHROMA_WORKFLOW_ALIASES,
    )
    map_metadata_aliases = _parse_alias_list(
        get_env("CHROMA_COLLECTION_MAP_METADATA"),
        _DEFAULT_CHROMA_MAP_ALIASES,
    )
    if url and "://" in url:
        parsed = urlparse(url)
        host = parsed.hostname or host
        port = str(parsed.port or port)
    return {
        "configured": bool(host and port),
        "host": host,
        "port": port,
        "url": url,
        "regulations_collection": regulations_aliases[0],
        "workflows_collection": workflows_aliases[0],
        "map_metadata_collection": map_metadata_aliases[0],
        "regulations_collection_aliases": regulations_aliases,
        "workflows_collection_aliases": workflows_aliases,
        "map_metadata_collection_aliases": map_metadata_aliases,
        "required_config": ["CHROMA_HOST|CHROMA_URL", "CHROMA_PORT", "CHROMA_COLLECTION_REGULATIONS", "CHROMA_COLLECTION_WORKFLOWS", "CHROMA_COLLECTION_MAP_METADATA"],
    }


def openeo_config() -> dict[str, Any]:
    url = get_env("OPENEO_URL")
    user = get_env("OPENEO_USER")
    password = get_env("OPENEO_PASSWORD")
    return {
        "configured": bool(url and user and password),
        "url": url,
        "user_present": bool(user),
        "password_present": bool(password),
        "required_config": ["OPENEO_URL", "OPENEO_USER", "OPENEO_PASSWORD"],
    }


def eo_cache_config() -> dict[str, Any]:
    raw = get_env("GEO_EXPERT_EO_CACHE_DIR")
    path = Path(raw).expanduser() if raw else None
    exists = bool(path and path.exists() and path.is_dir())
    return {
        "configured": bool(raw),
        "path": str(path) if path else None,
        "exists": exists,
        "required_config": ["GEO_EXPERT_EO_CACHE_DIR"],
    }


def satellite_config() -> dict[str, Any]:
    provider = str(get_env("GEO_EXPERT_SATELLITE_PROVIDER", "cache_only") or "cache_only").strip().lower()
    allow_fetch = str(get_env("GEO_EXPERT_ALLOW_SATELLITE_FETCH", "0") or "0").strip().lower() in {"1", "true", "yes", "on"}
    gee_enabled = str(get_env("GEO_EXPERT_GEE_ENABLED", "0") or "0").strip().lower() in {"1", "true", "yes", "on"}
    index_path_raw = get_env("GEO_EXPERT_EO_CACHE_INDEX", str(Path("outputs") / "geo_expert" / "eo_cache_index.json"))
    index_path = Path(index_path_raw).expanduser() if index_path_raw else Path("outputs") / "geo_expert" / "eo_cache_index.json"
    output_dir_raw = get_env("GEO_EXPERT_SATELLITE_OUTPUT_DIR")
    output_dir = Path(output_dir_raw).expanduser() if output_dir_raw else None
    return {
        "provider": provider,
        "allow_fetch": allow_fetch,
        "gee_enabled": gee_enabled,
        "gee_project": get_env("GEO_EXPERT_GEE_PROJECT"),
        "cache_index_path": str(index_path),
        "output_dir": str(output_dir) if output_dir else None,
        "required_config": [
            "GEO_EXPERT_SATELLITE_PROVIDER",
            "GEO_EXPERT_ALLOW_SATELLITE_FETCH",
            "GEO_EXPERT_GEE_ENABLED",
            "GEO_EXPERT_EO_CACHE_DIR",
            "GEO_EXPERT_EO_CACHE_INDEX",
            "GEO_EXPERT_GEE_PROJECT",
            "GEO_EXPERT_SATELLITE_OUTPUT_DIR",
        ],
    }


def detector_config() -> dict[str, Any]:
    backend = str(get_env("GEO_EXPERT_DETECTOR_BACKEND", "mock") or "mock").strip().lower()
    model_path = get_env("GEO_EXPERT_DETECTOR_MODEL_PATH")
    device = str(get_env("GEO_EXPERT_DETECTOR_DEVICE", "cpu") or "cpu").strip()
    confidence_raw = get_env("GEO_EXPERT_DETECTOR_CONFIDENCE", "0.25")
    try:
        confidence = float(str(confidence_raw))
    except Exception:
        confidence = 0.25
    resolved = None
    if model_path:
        with_path = Path(model_path).expanduser()
        resolved = str(with_path)
    return {
        "backend": backend,
        "model_path": resolved,
        "model_basename": Path(resolved).name if resolved else None,
        "model_exists": bool(resolved and Path(resolved).exists()),
        "device": device,
        "confidence": confidence,
        "required_config": [
            "GEO_EXPERT_DETECTOR_BACKEND",
            "GEO_EXPERT_DETECTOR_MODEL_PATH",
            "GEO_EXPERT_DETECTOR_DEVICE",
            "GEO_EXPERT_DETECTOR_CONFIDENCE",
        ],
    }
