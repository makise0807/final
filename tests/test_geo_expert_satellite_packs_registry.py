from __future__ import annotations

from plugins.geo_expert.satellite_workflows.pack_registry import load_packs


def test_satellite_packs_registry_loads_ten_packs() -> None:
    packs = load_packs()
    assert len(packs) == 10
    ids = [pack["pack_id"] for pack in packs]
    assert len(ids) == len(set(ids))
    for pack in packs:
        for key in (
            "pack_id",
            "title",
            "title_zh",
            "target_users",
            "input_types",
            "default_report_type",
            "satellite_required",
            "rag_enabled",
            "user_data_collection",
            "system_collection",
            "workflow_steps",
            "report_sections",
            "safety_notes",
        ):
            assert key in pack
