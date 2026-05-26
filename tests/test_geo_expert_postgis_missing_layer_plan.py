from __future__ import annotations

from scripts.plan_geo_expert_postgis_import import build_import_plan


def test_postgis_missing_layer_plan_reports_required_data_types(tmp_path) -> None:
    plan = build_import_plan(tmp_path)
    missing = {item["alias"]: item for item in plan["missing_aliases"]}
    assert "building_layer" in missing
    assert missing["building_layer"]["required_data_type"] == "building footprints"
    assert missing["building_layer"]["status"] == "source_missing"
    assert "acceptable_formats" in missing["building_layer"]
    assert missing["building_layer"]["where_to_get_hint"]
