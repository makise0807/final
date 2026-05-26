from __future__ import annotations

from pathlib import Path

from scripts.plan_geo_expert_postgis_import import build_import_plan


def test_postgis_import_plan_detects_dump_and_geojson(tmp_path: Path) -> None:
    (tmp_path / "database").mkdir()
    dump_path = tmp_path / "database" / "geodb_export.dump"
    dump_path.write_bytes(b"dump")
    geojson_path = tmp_path / "river_zone.geojson"
    geojson_path.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")

    plan = build_import_plan(tmp_path)
    assert str(dump_path) in plan["found_files"]
    assert str(geojson_path) in plan["found_files"]
    methods = {item["method"] for item in plan["suggested_imports"]}
    assert "pg_restore" in methods
    assert "ogr2ogr" in methods
    assert all(item["requires_user_approval"] is True for item in plan["suggested_imports"])
    assert "resolved_aliases" in plan
    assert "missing_aliases" in plan
