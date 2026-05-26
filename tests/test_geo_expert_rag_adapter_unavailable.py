from __future__ import annotations

import json
import os

from plugins.geo_expert.tools import rag_search_regulations_handler


def test_geo_expert_rag_adapter_unavailable(monkeypatch) -> None:
    monkeypatch.delenv("CHROMA_HOST", raising=False)
    monkeypatch.delenv("CHROMA_PORT", raising=False)
    raw = rag_search_regulations_handler({"query": "建築法", "top_k": 3})
    payload = json.loads(raw)
    assert isinstance(raw, str)
    assert "success" in payload
    assert payload["success"] is True or payload.get("error")

