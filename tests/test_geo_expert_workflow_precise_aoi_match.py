from __future__ import annotations

import json

from plugins.geo_expert.tools import workflow_run_handler


def test_workflow_precise_aoi_match_with_sidecar(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "scene.png").write_bytes(b"img")
    (cache_dir / "scene.json").write_text(
        json.dumps(
                {
                    "source": "eo_cache",
                    "provider": "gee_preview",
                    "aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47},
                    "match_quality": "precise_aoi",
                }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GEO_EXPERT_EO_CACHE_DIR", str(cache_dir))
    payload = json.loads(
        workflow_run_handler(
            {
                "workflow_id": "WF-002",
                "user_request": "山坡地保育區超限利用監測",
                "mode": "safe_run",
                "inputs": {"aoi": {"west": 120.7001, "south": 23.4501, "east": 120.719, "north": 23.469}},
            }
        )
    )
    assert payload["satellite_evidence"]["match_strategy"] == "bbox_overlap"
    assert payload["satellite_evidence"]["confidence"] > 0.5
    assert not any("latest_without_metadata" in warning for warning in payload["satellite_evidence"]["warnings"])
    inherited = [step for step in payload["steps"] if step["evidence"].get("satellite_image_path")]
    assert inherited


def test_workflow_no_overlap_or_no_sidecar_falls_back(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "scene.png").write_bytes(b"img")
    monkeypatch.setenv("GEO_EXPERT_EO_CACHE_DIR", str(cache_dir))
    payload = json.loads(
        workflow_run_handler(
            {
                "workflow_id": "WF-002",
                "user_request": "山坡地保育區超限利用監測",
                "mode": "safe_run",
                "inputs": {"aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47}},
            }
        )
    )
    assert payload["satellite_evidence"]["match_strategy"] == "latest_without_metadata"
    assert payload["satellite_evidence"]["warnings"]
