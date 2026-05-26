from __future__ import annotations

from plugins.geo_expert.workflow_runner import run_workflow


def test_geo_expert_workflow_satellite_aoi_precise_match(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "wf-002_bbox.png").write_bytes(b"img")
    (cache_dir / "wf-002_bbox.json").write_text(
        '{"workflow_hint":"WF-002","aoi":{"west":120.7,"south":23.45,"east":120.72,"north":23.47}}',
        encoding="utf-8",
    )
    monkeypatch.setenv("GEO_EXPERT_EO_CACHE_DIR", str(cache_dir))
    monkeypatch.setenv("GEO_EXPERT_ALLOW_SATELLITE_FETCH", "0")
    result = run_workflow(
        workflow_id="WF-002",
        user_request="山坡地保育區超限利用監測",
        mode="safe_run",
        inputs={"aoi": {"west": 120.7001, "south": 23.4501, "east": 120.7199, "north": 23.4699}},
    )
    assert result["satellite_evidence"]["match_strategy"] in {"workflow_hint", "bbox_overlap"}


def test_geo_expert_workflow_satellite_aoi_latest_without_metadata_warning(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "latest.png").write_bytes(b"img")
    monkeypatch.setenv("GEO_EXPERT_EO_CACHE_DIR", str(cache_dir))
    monkeypatch.setenv("GEO_EXPERT_ALLOW_SATELLITE_FETCH", "0")
    result = run_workflow(
        workflow_id="WF-002",
        user_request="山坡地保育區超限利用監測",
        mode="safe_run",
        inputs={"aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47}},
    )
    assert result["satellite_evidence"]["match_strategy"] == "latest_without_metadata"
    assert any("not a precise AOI match" in warning for warning in result["satellite_evidence"]["warnings"])


def test_geo_expert_workflow_satellite_acquisition_disabled_when_no_cache(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / "empty"
    cache_dir.mkdir()
    monkeypatch.setenv("GEO_EXPERT_EO_CACHE_DIR", str(cache_dir))
    monkeypatch.setenv("GEO_EXPERT_ALLOW_SATELLITE_FETCH", "0")
    result = run_workflow(
        workflow_id="WF-002",
        user_request="山坡地保育區超限利用監測",
        mode="safe_run",
        inputs={"aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47}},
    )
    assert result["satellite_evidence"]["error"] == "satellite_acquisition_disabled"
