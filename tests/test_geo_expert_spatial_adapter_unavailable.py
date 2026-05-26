from __future__ import annotations

import json

from plugins.geo_expert.tools import spatial_query_handler


def test_geo_expert_spatial_adapter_unavailable(monkeypatch) -> None:
    for key in ("DATABASE_URL", "POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "POSTGRES_PORT"):
        monkeypatch.delenv(key, raising=False)
    raw = spatial_query_handler({"operation": "buffer", "parameters": {"distance_m": 50, "geojson_polygon": {}}})
    payload = json.loads(raw)
    assert payload["success"] is False
    assert payload["dependency"] == "postgis"

