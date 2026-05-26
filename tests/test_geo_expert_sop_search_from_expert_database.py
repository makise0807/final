from __future__ import annotations

import json

from plugins.geo_expert.tools import search_sop_database_handler


def test_geo_expert_sop_search_from_expert_database() -> None:
    raw = search_sop_database_handler({"query": "我要找台中的違章建築", "limit": 5})
    assert isinstance(raw, str)

    payload = json.loads(raw)
    assert payload["success"] is True

    serialized = json.dumps(payload["results"], ensure_ascii=False)
    assert "WF-001" in serialized or "農業區違章工廠盤查" in serialized
