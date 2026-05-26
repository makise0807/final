from __future__ import annotations

from pathlib import Path

import scripts.ingest_geo_expert_local_chroma as ingest_mod


def test_deterministic_embedding_is_stable() -> None:
    emb_a = ingest_mod.deterministic_embedding("都市計畫 農業區")
    emb_b = ingest_mod.deterministic_embedding("都市計畫 農業區")
    assert len(emb_a) == ingest_mod.EMBED_DIM
    assert emb_a == emb_b
    assert any(value != 0.0 for value in emb_a)


def test_collect_corpus_documents_chunks_non_empty(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    plugin_root = tmp_path / "plugin"
    regulations_dir = source_root / "data" / "regulations"
    workflows_path = source_root / "data" / "workflow_db" / "expert_workflows.json"
    knowledge_dir = plugin_root / "expert_knowledge"
    plugin_workflows = plugin_root / "workflow_db" / "expert_workflows.json"
    regulations_dir.mkdir(parents=True)
    workflows_path.parent.mkdir(parents=True)
    knowledge_dir.mkdir(parents=True)
    plugin_workflows.parent.mkdir(parents=True)
    (regulations_dir / "a.txt").write_text("都市計畫農業區相關規定\n第二段內容", encoding="utf-8")
    workflows_path.write_text('[{"workflow_id":"WF-X","title":"測試流程"}]', encoding="utf-8")
    (knowledge_dir / "b.md").write_text("農地與容積獎勵摘要", encoding="utf-8")
    plugin_workflows.write_text('{"workflows":[{"workflow_id":"WF-Y","title":"另一個流程"}]}', encoding="utf-8")

    docs, summary = ingest_mod.collect_corpus_documents(source_roots=[source_root], plugin_root=plugin_root)
    assert docs
    assert summary["documents_collected"] == len(docs)
    assert all(doc_id for doc_id, _, _ in docs)
    assert all(document.strip() for _, document, _ in docs)
    assert all(metadata.get("source_path") for _, _, metadata in docs)
    assert all("source_type" in metadata for _, _, metadata in docs)


def test_dry_run_does_not_require_chroma(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    regulations_dir = source_root / "data" / "regulations"
    regulations_dir.mkdir(parents=True)
    (regulations_dir / "a.txt").write_text("都市計畫農業區相關規定", encoding="utf-8")
    payload = ingest_mod.ingest("urban_regulations", dry_run=True, source_roots=[source_root], limit=10)
    assert payload["success"] is True
    assert payload["dry_run"] is True
    assert payload["doc_count"] > 0
    assert "corpus_summary" in payload


def test_collect_corpus_documents_metadata_fields(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    regulations_dir = source_root / "data" / "regulations"
    regulations_dir.mkdir(parents=True)
    (regulations_dir / "law.txt").write_text("第一條 測試法規。第二條 測試內容。", encoding="utf-8")
    docs, _summary = ingest_mod.collect_corpus_documents(source_roots=[source_root], plugin_root=tmp_path / "plugin")
    assert docs
    _doc_id, _document, metadata = docs[0]
    assert metadata["source_path"]
    assert metadata["source_type"]
    assert "chunk_index" in metadata
    assert "title" in metadata


def test_script_import_does_not_require_chromadb() -> None:
    assert ingest_mod.DEFAULT_COLLECTION
    assert callable(ingest_mod.deterministic_embedding)


def test_dry_run_reports_sentence_transformers_missing_when_requested(tmp_path: Path, monkeypatch) -> None:
    source_root = tmp_path / "source"
    regulations_dir = source_root / "data" / "regulations"
    regulations_dir.mkdir(parents=True)
    (regulations_dir / "a.txt").write_text("土地使用分區測試內容", encoding="utf-8")
    monkeypatch.setitem(__import__("sys").modules, "sentence_transformers", None)
    payload = ingest_mod.ingest(
        "urban_regulations",
        dry_run=True,
        source_roots=[source_root],
        embedding_backend="sentence_transformers",
        embedding_model="local-model",
    )
    assert payload["success"] is False
    assert str(payload["error"]).startswith("sentence_transformers_")
