from __future__ import annotations

import json
from pathlib import Path

from plugins.geo_expert.tools import workflow_eval_all_handler


def test_geo_expert_workflow_safe_run_all() -> None:
    payload = json.loads(workflow_eval_all_handler({"mode": "safe_run"}))
    assert payload["success"] is True
    assert payload["count"] == 10
    for item in payload["results"]:
        assert item["workflow_id"].startswith("WF-")
        assert item["steps"]
        assert item["failed_steps"] == []
    wf001 = next(item for item in payload["results"] if item["workflow_id"] == "WF-001")
    assert Path(wf001["outputs"]["report_path"]).exists()
    assert Path(wf001["outputs"]["geojson_path"]).exists()
    assert Path(wf001["outputs"]["overlay_path"]).exists()
