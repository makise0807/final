from __future__ import annotations

import json

from plugins.geo_expert.tools import case_plan_handler


def test_geo_expert_case_plan() -> None:
    cases = [
        ("我要找台中的違章建築", "WF-001"),
        ("山坡地疑似超限利用", "WF-002"),
        ("捷運站周邊容積獎勵", "WF-008"),
    ]
    for query, expected in cases:
        payload = json.loads(case_plan_handler({"user_request": query, "inputs": {"location": "台中"}}))
        assert payload["success"] is True
        assert payload["selected_workflow_id"] == expected
        assert "missing_inputs" in payload
        assert "execution_plan" in payload
        assert "approval_required_steps" in payload
        assert "recommended_next_actions" in payload
