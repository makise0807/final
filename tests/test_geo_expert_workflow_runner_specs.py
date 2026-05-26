from __future__ import annotations

import json
from pathlib import Path


def test_geo_expert_workflow_runner_specs() -> None:
    path = Path("C:/Users/34620/OneDrive/Desktop/final/plugins/geo_expert/data/workflow_db/expert_workflows.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    workflow_ids = {item["workflow_id"] for item in payload}
    assert workflow_ids == {f"WF-{index:03d}" for index in range(1, 11)}
    for item in payload:
        assert item["steps"]
        assert len(item["steps"]) >= 3
        assert "safety" in item
