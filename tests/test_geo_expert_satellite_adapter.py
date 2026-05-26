from __future__ import annotations

import json

from plugins.geo_expert.tools import satellite_acquire_preview_handler


def test_geo_expert_satellite_acquire_preview_prepare_only() -> None:
    payload = json.loads(
        satellite_acquire_preview_handler(
            {
                "aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47},
                "mode": "prepare_only",
            }
        )
    )
    assert payload["success"] is True
    assert payload["prepare_only"] is True
    assert "acquisition_plan" in payload


def test_geo_expert_satellite_acquire_preview_cache_only(monkeypatch, tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "wf-002_scene.png").write_bytes(b"img")
    (cache_dir / "wf-002_scene.json").write_text(
        json.dumps({"workflow_hint": "WF-002", "aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("GEO_EXPERT_EO_CACHE_DIR", str(cache_dir))
    payload = json.loads(
        satellite_acquire_preview_handler(
            {
                "workflow_id": "WF-002",
                "aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47},
                "mode": "cache_only",
            }
        )
    )
    assert payload["success"] is True
    assert payload["image_path"].endswith("wf-002_scene.png")
    assert payload["match_strategy"] in {"workflow_hint", "bbox_overlap"}


def test_geo_expert_satellite_acquire_preview_preview_disabled(monkeypatch) -> None:
    monkeypatch.setenv("GEO_EXPERT_ALLOW_SATELLITE_FETCH", "0")
    payload = json.loads(
        satellite_acquire_preview_handler(
            {
                "aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47},
                "provider": "gee",
                "mode": "preview",
            }
        )
    )
    assert payload["success"] is False
    assert payload["error"] == "satellite_acquisition_disabled"
    assert "next_action" in payload
