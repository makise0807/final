from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_SOURCE_ROOT = Path(os.getenv("GEO_EXPERT_SOURCE_ROOT", r"C:\Users\34620\OneDrive\Desktop\geo-orchestrator"))
ALIAS_REQUIREMENTS = {
    "building_layer": ["building", "footprint", "建物", "建築"],
    "river_zone": ["river", "flood", "watercourse", "河川", "行水區", "水"],
    "agricultural_zone": ["agricultural", "farmland", "agri", "zoning", "agriculture", "landuse", "農業區", "農地"],
    "hazard_zone": ["hazard", "landslide", "flood", "disaster", "山崩", "崩塌", "災害"],
    "slope_layer": ["slope", "hillside", "terrain", "坡地", "山坡"],
    "ecology_network_layer": ["ecology", "green", "network", "生態", "綠網"],
    "sensitive_habitat_layer": ["habitat", "sensitive", "ecology", "棲地", "敏感"],
    "landuse_layer": ["landuse", "land_use", "land-use", "使用分區", "土地使用", "分區"],
    "zoning_change_layer": ["zoning", "change", "urban", "變更", "都市計畫", "分區"],
}
ALIAS_REQUIRED_DATA = {
    "building_layer": {"required_data_type": "building footprints", "acceptable_formats": ["SHP", "GPKG", "GeoJSON"]},
    "river_zone": {"required_data_type": "river/floodplain polygon", "acceptable_formats": ["SHP", "GPKG", "GeoJSON"]},
    "agricultural_zone": {"required_data_type": "agricultural zoning / land-use zone", "acceptable_formats": ["SHP", "GPKG", "GeoJSON"]},
    "hazard_zone": {"required_data_type": "hazard potential polygon", "acceptable_formats": ["SHP", "GPKG", "GeoJSON"]},
    "slope_layer": {"required_data_type": "slope/hillside polygon or raster-derived vector", "acceptable_formats": ["SHP", "GPKG", "GeoJSON"]},
    "ecology_network_layer": {"required_data_type": "ecological corridor / green network polygon", "acceptable_formats": ["SHP", "GPKG", "GeoJSON"]},
    "sensitive_habitat_layer": {"required_data_type": "sensitive habitat polygon", "acceptable_formats": ["SHP", "GPKG", "GeoJSON"]},
    "landuse_layer": {"required_data_type": "land-use zoning", "acceptable_formats": ["SHP", "GPKG", "GeoJSON"]},
    "zoning_change_layer": {"required_data_type": "zoning change proposal boundaries", "acceptable_formats": ["SHP", "GPKG", "GeoJSON"]},
}
ALIAS_WHERE_TO_GET_HINT = {
    "building_layer": "Municipal open data building footprint layer or cadastral building survey export.",
    "river_zone": "Water resources / floodplain authority polygon layer.",
    "agricultural_zone": "Agricultural zoning or land-use classification dataset.",
    "hazard_zone": "Hazard potential map polygons from disaster-prevention or geology authority.",
    "slope_layer": "Hillside / slope management layer or raster-derived vector product.",
    "ecology_network_layer": "Ecological corridor or national green network polygon layer.",
    "sensitive_habitat_layer": "Sensitive habitat, conservation, or biodiversity protection polygons.",
    "landuse_layer": "Urban/rural land-use zoning dataset.",
    "zoning_change_layer": "Urban planning zoning change proposal boundaries.",
}


def _load_aliases() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "plugins" / "geo_expert" / "data" / "spatial" / "layer_aliases.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _public_relations() -> dict[str, list[str]]:
    try:
        from sqlalchemy import create_engine, text
    except Exception:
        return {"tables": [], "views": []}
    host = os.getenv("POSTGRES_HOST")
    db = os.getenv("POSTGRES_DB")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    port = os.getenv("POSTGRES_PORT", "5432")
    if not all([host, db, user, password]):
        return {"tables": [], "views": []}
    engine = create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}", future=True)
    with engine.connect() as conn:
        tables = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name")).scalars().all()
        views = conn.execute(text("SELECT table_name FROM information_schema.views WHERE table_schema='public' ORDER BY table_name")).scalars().all()
    return {"tables": [f"public.{name}" for name in tables], "views": [f"public.{name}" for name in views]}


def _find_files(source_root: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in ("*.dump", "*.sql", "*.gpkg", "*.geojson", "*.shp", "*.csv", "*.tif", "*.tiff"):
        files.extend(source_root.rglob(pattern))
    return sorted({path.resolve() for path in files})


def _command_preview(path: Path, target_table: str) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix == ".dump":
        return (
            "pg_restore",
            f'docker cp "{path}" geo_postgis:/tmp/{path.name} && docker exec geo_postgis pg_restore -U geouser -d geodb -n public /tmp/{path.name}',
        )
    if suffix == ".sql":
        return ("psql", f'psql -h localhost -U geouser -d geodb -f "{path}"')
    if suffix in {".geojson", ".gpkg", ".shp"}:
        return ("ogr2ogr", f'ogr2ogr -f PostgreSQL PG:"host=localhost dbname=geodb user=geouser" "{path}" -nln {target_table}')
    return ("metadata_only", f"# review {path}")


def build_import_plan(source_root: Path = DEFAULT_SOURCE_ROOT) -> dict[str, Any]:
    aliases = _load_aliases()
    relations = _public_relations()
    found_files = [str(path) for path in _find_files(source_root)]
    resolved_aliases: list[str] = []
    missing_aliases: list[dict[str, Any]] = []
    suggested_imports: list[dict[str, Any]] = []

    for alias, raw in aliases.items():
        meta = raw if isinstance(raw, dict) else {"table": str(raw), "status": "resolved"}
        status = str(meta.get("status") or "resolved")
        table = str(meta.get("table") or "")
        if status == "resolved":
            resolved_aliases.append(alias)
            continue
        keywords = ALIAS_REQUIREMENTS.get(alias, [])
        candidates = [path for path in found_files if any(keyword in Path(path).name.lower() for keyword in keywords)]
        if not candidates:
            missing_aliases.append(
                {
                    "alias": alias,
                    "target_table": table,
                    "status": "source_missing",
                    **ALIAS_REQUIRED_DATA.get(alias, {}),
                    "where_to_get_hint": ALIAS_WHERE_TO_GET_HINT.get(alias),
                    "blocked_reason": meta.get("description") or f"No source file found for {alias}.",
                }
            )
            continue
        for candidate in candidates:
            method, preview = _command_preview(Path(candidate), table or f"public.{alias}")
            suggested_imports.append(
                {
                    "alias": alias,
                    "source": candidate,
                    "target_table": table or f"public.{alias}",
                    "method": method,
                    **ALIAS_REQUIRED_DATA.get(alias, {}),
                    "where_to_get_hint": ALIAS_WHERE_TO_GET_HINT.get(alias),
                    "command_preview": preview,
                    "requires_user_approval": True,
                }
            )
        missing_aliases.append(
            {
                "alias": alias,
                "target_table": table,
                "status": "import_candidate_found",
                **ALIAS_REQUIRED_DATA.get(alias, {}),
                "where_to_get_hint": ALIAS_WHERE_TO_GET_HINT.get(alias),
                "blocked_reason": "Source file found but import requires explicit user approval.",
            }
        )

    if any(Path(path).suffix.lower() == ".dump" for path in found_files):
        suggested_imports.append(
            {
                "alias": "database_restore",
                "source": next(path for path in found_files if Path(path).suffix.lower() == ".dump"),
                "target_table": "public.*",
                "method": "pg_restore",
                "command_preview": _command_preview(Path(next(path for path in found_files if Path(path).suffix.lower() == ".dump")), "public.*")[1],
                "requires_user_approval": True,
            }
        )

    warnings = []
    if any(item.get("method") == "pg_restore" for item in suggested_imports):
        warnings.append("Dump restore may conflict with existing public tables; inspect before executing.")

    return {
        "source_root": str(source_root),
        "found_files": found_files,
        "found_existing_tables": relations["tables"],
        "found_existing_views": relations["views"],
        "resolved_aliases": sorted(resolved_aliases),
        "missing_aliases": missing_aliases,
        "suggested_imports": suggested_imports,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a read-only PostGIS import plan for Geo Expert assets.")
    parser.add_argument("--source-root", type=str, default=str(DEFAULT_SOURCE_ROOT))
    args = parser.parse_args()
    print(json.dumps(build_import_plan(Path(args.source_root)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
