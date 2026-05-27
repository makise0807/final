from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .config import dependency_error, postgis_config

_LAYER_ALIASES_PATH = Path(__file__).resolve().parents[1] / "data" / "spatial" / "layer_aliases.json"
WORKFLOW_LAYER_REQUIREMENTS = {
    "WF-001": ["cadastral_layer", "agricultural_zone", "building_layer"],
    "WF-002": ["slope_layer", "hazard_zone"],
    "WF-003": ["cadastral_layer", "landuse_layer"],
    "WF-004": ["river_zone"],
    "WF-005": ["agricultural_zone", "cadastral_layer"],
    "WF-006": ["landuse_layer"],
    "WF-007": ["agricultural_zone", "landuse_layer"],
    "WF-008": ["cadastral_layer", "landuse_layer"],
    "WF-009": ["hazard_zone", "slope_layer"],
    "WF-010": ["ecology_network_layer", "sensitive_habitat_layer"],
}


def _load_layer_aliases() -> dict[str, Any]:
    if not _LAYER_ALIASES_PATH.exists():
        return {}
    try:
        payload = json.loads(_LAYER_ALIASES_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _alias_entry(alias_name: str) -> dict[str, Any]:
    raw = (_load_layer_aliases() or {}).get(alias_name)
    if isinstance(raw, str):
        return {
            "alias": alias_name,
            "table": raw,
            "geometry_column": None,
            "status": "resolved",
            "description": "",
        }
    if isinstance(raw, dict):
        return {
            "alias": alias_name,
            "table": str(raw.get("table") or ""),
            "geometry_column": raw.get("geometry_column"),
            "status": str(raw.get("status") or "resolved"),
            "description": str(raw.get("description") or ""),
        }
    return {
        "alias": alias_name,
        "table": alias_name,
        "geometry_column": None,
        "status": "missing_data_required",
        "description": "Alias not defined.",
    }


def _resolve_layer_name(name: str) -> dict[str, Any]:
    alias_map = _load_layer_aliases() or {}
    if name in alias_map:
        return _alias_entry(name)
    return {
        "alias": name,
        "table": name,
        "geometry_column": None,
        "status": "direct",
        "description": "Direct table reference.",
    }


def spatial_capability_profile() -> dict[str, Any]:
    alias_map = _load_layer_aliases() or {}
    grouped = {
        "cadastral": "missing_data_required",
        "building": "missing_data_required",
        "river": "missing_data_required",
        "hazard": "missing_data_required",
        "landuse": "missing_data_required",
        "ecology": "missing_data_required",
        "zoning_change": "missing_data_required",
    }
    alias_checks = []
    for alias in alias_map.keys():
        entry = _alias_entry(alias)
        alias_checks.append(entry)
        status = str(entry.get("status") or "")
        if alias in {"cadastral_layer", "land_parcel_layer", "parcels_wgs84", "parcels_twd97"} and status == "resolved":
            grouped["cadastral"] = "available"
        if alias == "building_layer" and status == "resolved":
            grouped["building"] = "available"
        if alias == "river_zone" and status == "resolved":
            grouped["river"] = "available"
        if alias in {"hazard_zone", "slope_layer"} and status == "resolved":
            grouped["hazard"] = "available"
        if alias in {"agricultural_zone", "landuse_layer"} and status == "resolved":
            grouped["landuse"] = "available"
        if alias in {"ecology_network_layer", "sensitive_habitat_layer"} and status == "resolved":
            grouped["ecology"] = "available"
        if alias == "zoning_change_layer" and status == "resolved":
            grouped["zoning_change"] = "available"
    return {
        "success": True,
        "capability_profile": grouped,
        "workflow_layer_requirements": WORKFLOW_LAYER_REQUIREMENTS,
        "alias_entries": alias_checks,
    }


def _connect_engine():
    cfg = postgis_config()
    if not cfg["configured"]:
        return None, _postgis_unavailable("connect")
    try:
        from sqlalchemy import create_engine
    except Exception:
        return None, dependency_error(
            "postgis",
            "SQLAlchemy is unavailable for PostGIS adapter.",
            required_config=cfg["required_config"],
        )
    try:
        if cfg.get("database_url"):
            engine = create_engine(cfg["database_url"], future=True)
        else:
            engine = create_engine(
                f"postgresql+psycopg2://{cfg['user']}:{cfg.get('password') or os.getenv('POSTGRES_PASSWORD','')}@{cfg['host']}:{cfg['port']}/{cfg['db']}",
                future=True,
            )
        return engine, None
    except Exception as exc:
        return None, dependency_error(
            "postgis",
            f"PostGIS engine creation failed: {exc}",
            required_config=cfg["required_config"],
        )


def _postgis_unavailable(operation: str) -> dict[str, Any]:
    cfg = postgis_config()
    return dependency_error(
        "postgis",
        "PostGIS is not configured or unavailable.",
        required_config=cfg["required_config"],
        operation=operation,
    )


def _relation_exists(conn: Any, table_name: str) -> bool:
    from sqlalchemy import text

    return bool(conn.execute(text("SELECT to_regclass(:table_name) IS NOT NULL"), {"table_name": table_name}).scalar())


def _row_count(conn: Any, table_name: str) -> int | None:
    from sqlalchemy import text

    try:
        return int(conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar() or 0)
    except Exception:
        return None


def spatial_status() -> dict[str, Any]:
    cfg = postgis_config()
    if not cfg["configured"]:
        return dependency_error(
            "postgis",
            "PostGIS is not configured or unavailable.",
            required_config=cfg["required_config"],
            configured=False,
            disabled_by_default=True,
            connects_on_import=False,
        )
    alias_checks = []
    public_tables: list[dict[str, Any]] = []
    public_views: list[dict[str, Any]] = []
    geometry_columns: list[dict[str, Any]] = []
    engine, error = _connect_engine()
    if error:
        return error
    try:
        from sqlalchemy import text

        with engine.connect() as conn:
            public_tables = [dict(row) for row in conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name")).mappings().all()]
            public_views = [dict(row) for row in conn.execute(text("SELECT table_name FROM information_schema.views WHERE table_schema='public' ORDER BY table_name")).mappings().all()]
            geometry_columns = [dict(row) for row in conn.execute(text("SELECT f_table_schema, f_table_name, f_geometry_column, type FROM geometry_columns WHERE f_table_schema='public' ORDER BY f_table_name, f_geometry_column")).mappings().all()]
            for alias in (_load_layer_aliases() or {}).keys():
                entry = _alias_entry(alias)
                exists = _relation_exists(conn, entry["table"]) if entry["table"] else False
                alias_checks.append(
                    {
                        "alias": alias,
                        "table_name": entry["table"],
                        "geometry_column": entry.get("geometry_column"),
                        "status": entry.get("status"),
                        "description": entry.get("description"),
                        "exists": bool(exists and entry.get("status") == "resolved"),
                        "row_count": _row_count(conn, entry["table"]) if exists else None,
                    }
                )
    except Exception:
        alias_checks = []
    return {
        "success": True,
        "dependency": "postgis",
        "configured": True,
        "disabled_by_default": True,
        "connects_on_import": False,
        "alias_checks": alias_checks,
        "public_tables": public_tables,
        "public_views": public_views,
        "geometry_columns": geometry_columns,
        "capability_profile": spatial_capability_profile().get("capability_profile"),
        "workflow_layer_requirements": WORKFLOW_LAYER_REQUIREMENTS,
    }


def analyze_buffer(geojson_polygon: dict[str, Any], distance_m: float) -> dict[str, Any]:
    if not postgis_config()["configured"]:
        return _postgis_unavailable("buffer")
    engine, error = _connect_engine()
    if error:
        return error
    try:
        from sqlalchemy import text

        geometry = json.dumps(geojson_polygon or {})
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT ST_Area(ST_Buffer(ST_SetSRID(ST_GeomFromGeoJSON(:geom),4326)::geography, :distance)) AS area_m2"
                ),
                {"geom": geometry, "distance": float(distance_m)},
            ).mappings().first()
        return {
            "success": True,
            "operation": "buffer",
            "used_real_service": True,
            "service": "postgis",
            "buffer_area_m2": float(row["area_m2"]) if row and row.get("area_m2") is not None else 0.0,
            "parameters": {"distance_m": float(distance_m)},
        }
    except Exception as exc:
        return {
            "success": False,
            "error": "postgis_query_failed",
            "message": str(exc),
            "operation": "buffer",
            "used_real_service": True,
            "service": "postgis",
        }


def analyze_proximity(geojson_polygon: dict[str, Any], target_table: str, max_distance_m: float, limit_n: int = 10) -> dict[str, Any]:
    if not postgis_config()["configured"]:
        return _postgis_unavailable("proximity")
    engine, error = _connect_engine()
    if error:
        return error
    resolved = _resolve_layer_name(target_table)
    if resolved.get("status") == "missing_data_required":
        return {
            "success": False,
            "error": "missing_required_layer",
            "message": resolved.get("description") or f"Missing spatial data for alias: {target_table}",
            "operation": "proximity",
            "used_real_service": False,
            "service": "postgis",
            "alias": target_table,
            "target_table": resolved.get("table"),
            "required_layer": target_table,
            "next_action": "import_layer",
        }
    try:
        with engine.connect() as conn:
            exists = _relation_exists(conn, resolved["table"])
            count = _row_count(conn, resolved["table"]) if exists else None
        if not exists:
            return {
                "success": False,
                "error": "layer_unavailable",
                "message": f"Target table not found: {resolved['table']}",
                "operation": "proximity",
                "used_real_service": True,
                "service": "postgis",
                "alias": target_table,
                "target_table": resolved["table"],
            }
        return {
            "success": True,
            "operation": "proximity",
            "used_real_service": True,
            "service": "postgis",
            "message": "Layer is available for proximity analysis; query remains bounded and read-only.",
            "parameters": {
                "target_table": resolved["table"],
                "max_distance_m": float(max_distance_m),
                "limit_n": int(limit_n),
            },
            "evidence": {"row_count": count, "alias": target_table},
        }
    except Exception as exc:
        return {
            "success": False,
            "error": "postgis_query_failed",
            "message": str(exc),
            "operation": "proximity",
            "used_real_service": True,
            "service": "postgis",
        }


def calculate_overlay_intersection(target_table: str, geojson_polygon: dict[str, Any] | None = None, geojson_file: str | None = None) -> dict[str, Any]:
    if not postgis_config()["configured"]:
        return _postgis_unavailable("intersection")
    engine, error = _connect_engine()
    if error:
        return error
    resolved = _resolve_layer_name(target_table)
    if resolved.get("status") == "missing_data_required":
        return {
            "success": False,
            "error": "missing_required_layer",
            "message": resolved.get("description") or f"Missing spatial data for alias: {target_table}",
            "operation": "intersection",
            "used_real_service": False,
            "service": "postgis",
            "alias": target_table,
            "target_table": resolved.get("table"),
            "required_layer": target_table,
            "next_action": "import_layer",
        }
    try:
        with engine.connect() as conn:
            exists = _relation_exists(conn, resolved["table"])
            count = _row_count(conn, resolved["table"]) if exists else None
        if not exists:
            return {
                "success": False,
                "error": "layer_unavailable",
                "message": f"Target table not found: {resolved['table']}",
                "operation": "intersection",
                "used_real_service": True,
                "service": "postgis",
                "alias": target_table,
                "target_table": resolved["table"],
            }
        return {
            "success": True,
            "operation": "intersection",
            "used_real_service": True,
            "service": "postgis",
            "message": "Layer is available for read-only intersection analysis.",
            "parameters": {"target_table": resolved["table"], "geojson_file": geojson_file},
            "evidence": {
                "row_count": count,
                "alias": target_table,
                "geometry_column": resolved.get("geometry_column"),
            },
        }
    except Exception as exc:
        return {
            "success": False,
            "error": "postgis_query_failed",
            "message": str(exc),
            "operation": "intersection",
            "used_real_service": True,
            "service": "postgis",
        }


def analyze_dissolve_union(parcel_ids_list: list[str]) -> dict[str, Any]:
    if not postgis_config()["configured"]:
        return _postgis_unavailable("dissolve")
    engine, error = _connect_engine()
    if error:
        return error
    try:
        with engine.connect() as conn:
            count = _row_count(conn, "public.cadastral_parcels")
        return {
            "success": True,
            "operation": "dissolve",
            "used_real_service": True,
            "service": "postgis",
            "message": "PostGIS connection available for dissolve/union analysis.",
            "parameters": {"parcel_ids_list": list(parcel_ids_list or [])},
            "evidence": {"row_count": count, "table": "public.cadastral_parcels"},
        }
    except Exception as exc:
        return {
            "success": False,
            "error": "postgis_query_failed",
            "message": str(exc),
            "operation": "dissolve",
            "used_real_service": True,
            "service": "postgis",
        }


def check_layer_availability(layer_names: list[str] | None = None) -> dict[str, Any]:
    if not postgis_config()["configured"]:
        return _postgis_unavailable("layer_check")
    engine, error = _connect_engine()
    if error:
        return error
    names = [str(name).strip() for name in (layer_names or []) if str(name).strip()]
    try:
        availability: dict[str, Any] = {}
        with engine.connect() as conn:
            for name in names:
                resolved = _resolve_layer_name(name)
                exists = _relation_exists(conn, resolved["table"]) if resolved.get("table") else False
                availability[name] = {
                    "table": resolved.get("table"),
                    "status": resolved.get("status"),
                    "exists": bool(exists and resolved.get("status") in {"resolved", "direct"}),
                    "description": resolved.get("description"),
                    "geometry_column": resolved.get("geometry_column"),
                    "row_count": _row_count(conn, resolved["table"]) if exists else None,
                }
        return {
            "success": True,
            "operation": "layer_check",
            "used_real_service": True,
            "service": "postgis",
            "available_layers": availability,
            "capability_profile": spatial_capability_profile().get("capability_profile"),
        }
    except Exception as exc:
        return {
            "success": False,
            "error": "postgis_query_failed",
            "message": str(exc),
            "operation": "layer_check",
            "used_real_service": True,
            "service": "postgis",
        }


def spatial_query(operation: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    params = dict(parameters or {})
    op = str(operation or "").strip().lower()
    if op == "buffer":
        return analyze_buffer(dict(params.get("geojson_polygon") or {}), float(params.get("distance_m", 0.0)))
    if op == "proximity":
        return analyze_proximity(
            dict(params.get("geojson_polygon") or {}),
            str(params.get("target_table") or ""),
            float(params.get("max_distance_m", 0.0)),
            int(params.get("limit_n", 10)),
        )
    if op == "intersection":
        return calculate_overlay_intersection(
            str(params.get("target_table") or ""),
            geojson_polygon=params.get("geojson_polygon"),
            geojson_file=params.get("geojson_file"),
        )
    if op == "dissolve":
        return analyze_dissolve_union(list(params.get("parcel_ids_list") or []))
    if op == "layer_check":
        return check_layer_availability(list(params.get("layer_names") or []))
    if op == "capability_show":
        return spatial_capability_profile()
    return {
        "success": False,
        "error": "unsupported_operation",
        "message": f"Unsupported spatial_query operation: {operation}",
        "supported_operations": ["buffer", "proximity", "intersection", "dissolve", "layer_check", "capability_show"],
    }


__all__ = [
    "analyze_buffer",
    "analyze_dissolve_union",
    "analyze_proximity",
    "calculate_overlay_intersection",
    "check_layer_availability",
    "spatial_capability_profile",
    "spatial_query",
    "spatial_status",
]
