from __future__ import annotations

import json

from plugins.geo_expert import workflow_runner


def test_wf001_default_path_stays_mock() -> None:
    payload = workflow_runner.run_workflow(
        workflow_id="WF-001",
        user_request="台中農地違章工廠",
        inputs={"image_case_id": "sample_taichung_case", "require_satellite": False, "use_llm": False},
        mode="safe_run",
    )
    detector_steps = [step for step in payload["steps"] if step["adapter"] == "detector"]
    assert detector_steps
    assert detector_steps[0]["evidence"].get("detector_used") == "mock"


def test_wf001_real_detector_degrades_when_model_unavailable(monkeypatch) -> None:
    monkeypatch.setenv("GEO_EXPERT_WF001_REAL_DETECTOR", "1")
    monkeypatch.setattr(
        workflow_runner,
        "run_detection",
        lambda request: {"success": False, "error": "yolo_dependency_missing", "warnings": ["dependency missing"]},
    )
    payload = workflow_runner.run_workflow(
        workflow_id="WF-001",
        user_request="台中農地違章工廠",
        inputs={"image_case_id": "sample_taichung_case", "real_detector": True},
        mode="safe_run",
    )
    detector_steps = [step for step in payload["steps"] if step["adapter"] == "detector"]
    assert detector_steps
    assert detector_steps[0]["status"] == "degraded"


def test_wf001_real_detector_can_use_real_result(monkeypatch) -> None:
    monkeypatch.setattr(
        workflow_runner,
        "run_detection",
        lambda request: {
            "success": True,
            "detector_used": "yolo",
            "used_real_model": True,
            "used_real_service": False,
            "warnings": [],
            "limitations": [],
            "geojson": {"type": "FeatureCollection", "features": []},
            "overlay_summary": {"detection_count": 0},
        },
    )
    payload = workflow_runner.run_workflow(
        workflow_id="WF-001",
        user_request="台中農地違章工廠",
        inputs={"image_case_id": "sample_taichung_case", "real_detector": True},
        mode="safe_run",
    )
    detector_steps = [step for step in payload["steps"] if step["adapter"] == "detector"]
    assert detector_steps
    assert detector_steps[0]["used_real_service"] is True
    assert detector_steps[0]["evidence"]["used_real_model"] is True
