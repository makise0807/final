from __future__ import annotations

import json

from plugins.geo_expert.tools import workflow_run_handler


def test_geo_expert_workflow_run_each() -> None:
    for index in range(1, 11):
        workflow_id = f"WF-{index:03d}"
        args = {"workflow_id": workflow_id, "user_request": workflow_id, "mode": "safe_run", "inputs": {}}
        if workflow_id == "WF-001":
            args["inputs"] = {"image_case_id": "sample_taichung_case", "require_satellite": False, "use_llm": False}
        payload = json.loads(workflow_run_handler(args))
        assert payload["workflow_id"] == workflow_id
        assert payload["success"] is True
        assert payload["failed_steps"] == []
