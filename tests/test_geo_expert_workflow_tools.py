from __future__ import annotations

import json

from plugins.geo_expert.tools import workflow_list_handler, workflow_show_handler


def test_geo_expert_workflow_list_and_show() -> None:
    raw_list = workflow_list_handler({})
    assert isinstance(raw_list, str)
    list_payload = json.loads(raw_list)
    assert list_payload["success"] is True
    assert any(item["workflow_id"] == "WF-001" for item in list_payload["workflows"])

    raw_show = workflow_show_handler({"workflow_id": "WF-001"})
    assert isinstance(raw_show, str)
    show_payload = json.loads(raw_show)
    assert show_payload["success"] is True
    assert show_payload["workflow_id"] == "WF-001"
    assert show_payload["title"] == "農業區違章工廠盤查"
