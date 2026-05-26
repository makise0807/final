from __future__ import annotations

import json

from plugins.geo_expert.tools import workflow_eval_all_handler


def test_geo_expert_workflow_dry_run_all() -> None:
    payload = json.loads(workflow_eval_all_handler({"mode": "dry_run"}))
    assert payload["success"] is True
    assert payload["count"] == 10
    for item in payload["results"]:
        assert item["workflow_id"].startswith("WF-")
        assert item["failed_steps"] == []
        assert item["steps"]
