from __future__ import annotations

from plugins.geo_expert.adapters.rag_tools import search_regulations
from plugins.geo_expert.adapters.spatial_tools import spatial_query


def test_geo_expert_real_services_optional() -> None:
    rag = search_regulations("農業區")
    assert "success" in rag
    spatial = spatial_query("layer_check", {"layer_names": ["public.test_layer"]})
    assert "success" in spatial
    if spatial.get("success"):
        assert spatial.get("used_real_service") is True
    else:
        assert spatial.get("error") in {"dependency_unavailable", "postgis_query_failed"}
