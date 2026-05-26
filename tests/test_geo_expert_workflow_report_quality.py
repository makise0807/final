from __future__ import annotations

from pathlib import Path

from plugins.geo_expert.workflow_runner import run_workflow


def test_geo_expert_workflow_report_quality() -> None:
    cases = {
        "WF-001": {"image_case_id": "sample_taichung_case", "require_satellite": False, "use_llm": False},
        "WF-005": {},
        "WF-009": {},
    }
    for workflow_id, inputs in cases.items():
        result = run_workflow(workflow_id=workflow_id, user_request=workflow_id, inputs=inputs, mode="safe_run")
        report_text = Path(result["report_path"]).read_text(encoding="utf-8")
        assert "Evidence Summary" in report_text
        assert "Warnings" in report_text
        assert "Next Recommended Actions" in report_text
        if workflow_id == "WF-001":
            assert Path(result["outputs"]["geojson_path"]).exists()
            assert Path(result["outputs"]["overlay_path"]).exists()
