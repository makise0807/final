from __future__ import annotations

from plugins.geo_expert.openeo_acquisition import create_openeo_acquisition_plan


def test_openeo_plan_defaults_to_prepare_only() -> None:
    plan = create_openeo_acquisition_plan(
        {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47},
        {"start": "2025-01-01", "end": "2025-01-31"},
        ["B04", "B03", "B02", "B08"],
        10,
    )
    assert plan["success"] is True
    assert plan["mode"] == "prepare_only"
    assert plan["submit_allowed"] is False
    assert plan["download_allowed"] is False
