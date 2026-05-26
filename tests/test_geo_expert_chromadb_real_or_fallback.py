from __future__ import annotations

from types import SimpleNamespace

from plugins.geo_expert.adapters import rag_tools
from plugins.geo_expert.adapters.rag_tools import search_regulations


def test_geo_expert_chromadb_real_or_fallback() -> None:
    payload = search_regulations("都市計畫 農業區", top_k=3)
    assert payload["success"] is True
    if payload.get("used_real_service"):
        assert payload["service"] == "chromadb"
        assert payload["status"] == "success"
        assert payload.get("collection")
    else:
        assert payload["status"] == "degraded"
        assert payload["service"] in {"local_text_fallback", "chromadb", "local_text"}
        assert payload.get("warnings") is not None or payload.get("error")


def test_chromadb_collection_alias_selection(monkeypatch) -> None:
    class FakeCollection:
        def count(self):
            return 1

        def query(self, **kwargs):
            return {
                "documents": [["都市計畫農業區法規"]],
                "metadatas": [[{"title": "urban", "source": "urban_regulations"}]],
                "distances": [[0.1]],
            }

    class FakeClient:
        def list_collections(self):
            return [SimpleNamespace(name="urban_regulations")]

        def get_collection(self, name):
            assert name == "urban_regulations"
            return FakeCollection()

    monkeypatch.setattr(rag_tools, "_get_chroma_client", lambda: (FakeClient(), None))
    monkeypatch.setattr(
        rag_tools,
        "chroma_config",
        lambda: {
            "configured": True,
            "regulations_collection_aliases": ["geo_regulations", "urban_regulations"],
            "workflows_collection_aliases": ["geo_workflows", "urban_regulations"],
            "map_metadata_collection_aliases": ["geo_map_data", "urban_regulations"],
            "required_config": [],
        },
    )
    payload = search_regulations("都市計畫", top_k=1)
    assert payload["success"] is True
    assert payload["used_real_service"] is True
    assert payload["collection"] == "urban_regulations"
