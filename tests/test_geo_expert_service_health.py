from __future__ import annotations

from plugins.geo_expert.production import check_service_health


def test_service_health_returns_structured_payload() -> None:
    result = check_service_health()
    assert result["success"] is True
    for key in ("chromadb", "postgis", "detector", "satellite_cache", "gee", "openeo", "legal_grounding"):
        assert key in result
