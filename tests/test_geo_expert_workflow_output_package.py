from __future__ import annotations

import json
from pathlib import Path

from plugins.geo_expert.workflow_runner import run_workflow


def test_geo_expert_workflow_output_package() -> None:
    for index in range(1, 11):
        workflow_id = f"WF-{index:03d}"
        inputs = {}
        if workflow_id == "WF-001":
            inputs = {"image_case_id": "sample_taichung_case", "require_satellite": False, "use_llm": False}
        result = run_workflow(workflow_id=workflow_id, user_request=workflow_id, inputs=inputs, mode="safe_run")
        report_path = Path(result["report_path"])
        result_json_path = Path(result["result_json_path"])
        assert report_path.exists()
        assert result_json_path.exists()
        report_text = report_path.read_text(encoding="utf-8")
        assert workflow_id in report_text
        assert "Steps" in report_text or "## Steps" in report_text
        assert "Limitations" in report_text
        assert "Not a formal legal conclusion" in report_text
        payload = json.loads(result_json_path.read_text(encoding="utf-8"))
        assert payload["workflow_id"] == workflow_id
        assert all("status" in step for step in payload["steps"])
