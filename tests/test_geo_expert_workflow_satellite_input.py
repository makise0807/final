from __future__ import annotations

from plugins.geo_expert.workflow_runner import run_workflow


def test_geo_expert_workflow_satellite_input_propagates_to_step_evidence(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "wf-002_scene.png").write_bytes(b"img")
    (cache_dir / "wf-002_scene.json").write_text(
        '{"workflow_hint":"WF-002","aoi":{"west":120.7,"south":23.45,"east":120.72,"north":23.47}}',
        encoding="utf-8",
    )
    monkeypatch.setenv("GEO_EXPERT_EO_CACHE_DIR", str(cache_dir))
    result = run_workflow(
        workflow_id="WF-002",
        user_request="山坡地保育區超限利用監測",
        mode="safe_run",
        inputs={"aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47}},
    )
    relevant = [
        step for step in result["steps"]
        if step["adapter"] in {"eo", "detector"} and step["evidence"].get("satellite_match_strategy")
    ]
    assert relevant
    assert all(step["evidence"]["satellite_match_strategy"] in {"workflow_hint", "bbox_overlap"} for step in relevant)
