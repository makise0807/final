from __future__ import annotations

import json

from plugins.geo_expert.adapters.satellite_tools import build_eo_cache_index, find_cached_satellite_image


def test_sidecar_with_aoi_enables_bbox_overlap(tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "scene.png").write_bytes(b"img")
    (cache_dir / "scene.json").write_text(
        json.dumps(
            {
                "source": "eo_cache",
                "provider": "gee_preview",
                "workflow_hint": "WF-002",
                "aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47},
                "match_quality": "precise_aoi",
            }
        ),
        encoding="utf-8",
    )
    index_path = tmp_path / "index.json"
    build_eo_cache_index(cache_dir=str(cache_dir), output_path=str(index_path))
    payload = find_cached_satellite_image(
        aoi={"west": 120.7001, "south": 23.4501, "east": 120.7199, "north": 23.4699},
        cache_index_path=str(index_path),
    )
    assert payload["match_strategy"] == "bbox_overlap"
    assert payload["metadata_found"] is True
    assert payload["match_quality"] == "precise_aoi"


def test_sidecar_without_aoi_cannot_use_bbox_overlap(tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "scene.png").write_bytes(b"img")
    (cache_dir / "scene.json").write_text(
        json.dumps({"source": "eo_cache", "workflow_hint": "WF-002", "aoi": None, "match_quality": "workflow_hint_only"}),
        encoding="utf-8",
    )
    index_path = tmp_path / "index.json"
    build_eo_cache_index(cache_dir=str(cache_dir), output_path=str(index_path))
    payload = find_cached_satellite_image(
        aoi={"west": 120.7001, "south": 23.4501, "east": 120.7199, "north": 23.4699},
        workflow_id="WF-002",
        cache_index_path=str(index_path),
    )
    assert payload["match_strategy"] == "workflow_hint"
    assert payload["match_quality"] == "workflow_hint_only"


def test_latest_fallback_still_warns(tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "scene.png").write_bytes(b"img")
    index_path = tmp_path / "index.json"
    build_eo_cache_index(cache_dir=str(cache_dir), output_path=str(index_path))
    payload = find_cached_satellite_image(cache_index_path=str(index_path))
    assert payload["match_strategy"] == "latest_without_metadata"
    assert payload["warnings"]
