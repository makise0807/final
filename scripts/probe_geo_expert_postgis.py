from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
LAYER_ALIASES_PATH = REPO_ROOT / "plugins" / "geo_expert" / "data" / "spatial" / "layer_aliases.json"


def _load_layer_aliases() -> dict[str, Any]:
    if not LAYER_ALIASES_PATH.exists():
        return {}
    return json.loads(LAYER_ALIASES_PATH.read_text(encoding="utf-8"))


def _db_config() -> dict[str, Any]:
    return {
        "database_url": os.getenv("DATABASE_URL"),
        "host": os.getenv("POSTGRES_HOST"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
        "db": os.getenv("POSTGRES_DB"),
        "user": os.getenv("POSTGRES_USER"),
        "password_present": bool(os.getenv("POSTGRES_PASSWORD")),
    }


def _connect_engine():
    cfg = _db_config()
    try:
        from sqlalchemy import create_engine
    except Exception as exc:
        return None, {"success": False, "error": "sqlalchemy_unavailable", "message": str(exc), "config": cfg}
    try:
        if cfg["database_url"]:
            return create_engine(cfg["database_url"], future=True), None
        if all([cfg["host"], cfg["db"], cfg["user"], os.getenv("POSTGRES_PASSWORD")]):
            password = os.getenv("POSTGRES_PASSWORD", "")
            url = f"postgresql+psycopg2://{cfg['user']}:{password}@{cfg['host']}:{cfg['port']}/{cfg['db']}"
            return create_engine(url, future=True), None
        return None, {"success": False, "error": "postgis_not_configured", "message": "PostGIS environment variables are incomplete.", "config": cfg}
    except Exception as exc:
        return None, {"success": False, "error": "postgis_connect_failed", "message": str(exc), "config": cfg}


def _alias_meta(raw: Any) -> dict[str, Any]:
    if isinstance(raw, str):
        return {"table": raw, "status": "resolved", "geometry_column": None, "description": ""}
    if isinstance(raw, dict):
        return {
            "table": str(raw.get("table") or ""),
            "status": str(raw.get("status") or "resolved"),
            "geometry_column": raw.get("geometry_column"),
            "description": str(raw.get("description") or ""),
        }
    return {"table": "", "status": "missing_data_required", "geometry_column": None, "description": ""}


def probe_postgis() -> dict[str, Any]:
    aliases = _load_layer_aliases()
    engine, error = _connect_engine()
    if error:
        return {
            "success": False,
            "status": "degraded",
            "service": "postgis",
            "config": _db_config(),
            "layer_aliases": aliases,
            "error": error.get("error"),
            "message": error.get("message"),
            "tables": [],
            "views": [],
            "geometry_columns": [],
            "alias_checks": [],
        }
    try:
        from sqlalchemy import text

        with engine.connect() as conn:
            version = conn.execute(text("SELECT PostGIS_Version()")).scalar()
            tables = [dict(row) for row in conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name")).mappings().all()]
            views = [dict(row) for row in conn.execute(text("SELECT table_name FROM information_schema.views WHERE table_schema='public' ORDER BY table_name")).mappings().all()]
            geometry_columns = [dict(row) for row in conn.execute(text("SELECT f_table_schema, f_table_name, f_geometry_column, type FROM geometry_columns WHERE f_table_schema='public' ORDER BY f_table_name, f_geometry_column")).mappings().all()]
            alias_checks = []
            for alias, raw in aliases.items():
                meta = _alias_meta(raw)
                exists = bool(conn.execute(text("SELECT to_regclass(:table_name) IS NOT NULL"), {"table_name": meta["table"]}).scalar()) if meta["table"] else False
                row_count = None
                if exists:
                    try:
                        row_count = int(conn.execute(text(f"SELECT COUNT(*) FROM {meta['table']}")).scalar() or 0)
                    except Exception:
                        row_count = None
                alias_checks.append(
                    {
                        "alias": alias,
                        "table_name": meta["table"],
                        "status": meta["status"],
                        "description": meta["description"],
                        "geometry_column": meta["geometry_column"],
                        "exists": bool(exists and meta["status"] == "resolved"),
                        "row_count": row_count,
                    }
                )
        return {
            "success": True,
            "status": "success",
            "service": "postgis",
            "config": _db_config(),
            "postgis_version": version,
            "tables": tables,
            "views": views,
            "geometry_columns": geometry_columns,
            "alias_checks": alias_checks,
            "aliases_resolved": sum(1 for item in alias_checks if item.get("exists")),
            "aliases_missing": sum(1 for item in alias_checks if not item.get("exists")),
        }
    except Exception as exc:
        return {
            "success": False,
            "status": "degraded",
            "service": "postgis",
            "config": _db_config(),
            "layer_aliases": aliases,
            "error": "postgis_probe_failed",
            "message": str(exc),
            "tables": [],
            "views": [],
            "geometry_columns": [],
            "alias_checks": [],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Geo Expert PostGIS probe.")
    parser.parse_args()
    print(json.dumps(probe_postgis(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
