from __future__ import annotations

import json
from pathlib import Path

from plugins.geo_expert.adapters.workflow_tools import route_workflow


def test_geo_expert_workflow_routing_eval() -> None:
    path = Path("C:/Users/34620/OneDrive/Desktop/final/plugins/geo_expert/data/eval/workflow_routing_cases.jsonl")
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) >= 30
    passed = 0
    for item in lines:
        routed = route_workflow(item["query"], limit=5)
        assert routed["success"] is True
        assert routed["selected_workflow_id"] == item["expected_workflow_id"], item["query"]
        passed += 1
    assert passed >= 30
