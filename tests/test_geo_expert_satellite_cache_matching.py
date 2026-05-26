from __future__ import annotations

import json

from plugins.geo_expert.adapters.satellite_tools import build_eo_cache_index, find_cached_satellite_image


def _write_image(path) -> None:
    path.write_bytes(b"fake-image")


def test_geo_expert_satellite_cache_matching_bbox_case_and_workflow(tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    bbox_image = cache_dir / "wf-002_scene.png"
    case_image = cache_dir / "case-special.png"
    latest_image = cache_dir / "latest.png"
    _write_image(bbox_image)
    _write_image(case_image)
    _write_image(latest_image)
    (bbox_image.with_suffix(".json")).write_text(
        json.dumps({"aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47}, "workflow_hint": "WF-002"}),
        encoding="utf-8",
    )
    (case_image.with_suffix(".json")).write_text(
        json.dumps({"case_id": "sample_case", "workflow_hint": "WF-009"}),
        encoding="utf-8",
    )
    index_path = tmp_path / "index.json"
    build_eo_cache_index(cache_dir=str(cache_dir), output_path=str(index_path))

    by_case = find_cached_satellite_image(case_id="sample_case", workflow_id="WF-002", cache_index_path=str(index_path))
    assert by_case["success"] is True
    assert by_case["match_strategy"] == "case_id_exact"
    assert by_case["image_path"].endswith("case-special.png")

    by_workflow = find_cached_satellite_image(workflow_id="WF-002", cache_index_path=str(index_path))
    assert by_workflow["success"] is True
    assert by_workflow["match_strategy"] == "workflow_hint"
    assert by_workflow["image_path"].endswith("wf-002_scene.png")

    by_aoi = find_cached_satellite_image(
        aoi={"west": 120.7005, "south": 23.4505, "east": 120.719, "north": 23.469},
        cache_index_path=str(index_path),
    )
    assert by_aoi["success"] is True
    assert by_aoi["match_strategy"] == "bbox_overlap"
    assert by_aoi["confidence"] > 0.5


def test_geo_expert_satellite_cache_matching_latest_without_metadata_warning(tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    image_path = cache_dir / "latest.png"
    _write_image(image_path)
    index_path = tmp_path / "index.json"
    build_eo_cache_index(cache_dir=str(cache_dir), output_path=str(index_path))

    payload = find_cached_satellite_image(
        aoi={"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47},
        cache_index_path=str(index_path),
    )
    assert payload["success"] is True
    assert payload["match_strategy"] == "latest_without_metadata"
    assert payload["warnings"]
    assert "not a precise AOI match" in payload["warnings"][0]
