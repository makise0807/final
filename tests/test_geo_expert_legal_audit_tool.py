from __future__ import annotations

import json

from plugins.geo_expert.tools import legal_audit_handler


def test_legal_audit_tool_runs() -> None:
    payload = json.loads(legal_audit_handler({}))
    assert payload["success"] is True
    assert "coverage" in payload
    assert "missing_topics" in payload
