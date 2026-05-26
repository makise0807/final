from __future__ import annotations

import json

from plugins.geo_expert.tools import workflow_list_handler


def test_geo_expert_workflow_from_word_data() -> None:
    raw = workflow_list_handler({})
    assert isinstance(raw, str)

    payload = json.loads(raw)
    assert payload["success"] is True

    workflow_ids = {item["workflow_id"] for item in payload["workflows"]}
    assert "WF-001" in workflow_ids
    assert len(workflow_ids) >= 10
