from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.ingest_geo_expert_local_chroma import deterministic_embedding

from .user_data_store import list_datasets


def _similarity(query: str, text: str) -> float:
    q = deterministic_embedding(query)
    t = deterministic_embedding(text)
    return round(sum(a * b for a, b in zip(q, t)), 4)


def _load_chunks(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    path = Path(str(dataset.get("chunks_path") or ""))
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    chunks = payload.get("chunks")
    return [item for item in chunks if isinstance(item, dict)] if isinstance(chunks, list) else []


def search_user_data(pack_id: str, query: str, dataset_ids: list[str] | None = None, top_k: int = 5) -> dict[str, Any]:
    datasets = list_datasets(pack_id)
    if dataset_ids:
        allowed = set(dataset_ids)
        datasets = [item for item in datasets if item.get("dataset_id") in allowed]
    if not datasets:
        return {
            "success": True,
            "status": "degraded",
            "pack_id": pack_id,
            "error": "no_user_data_available",
            "results": [],
            "warnings": ["No imported user datasets are available for this pack."],
            "limitations": ["User-data RAG requires imported runtime data."],
        }
    rows: list[dict[str, Any]] = []
    for dataset in datasets:
        for chunk in _load_chunks(dataset):
            document = str(chunk.get("document") or "").strip()
            if not document:
                continue
            rows.append(
                {
                    "dataset_id": dataset.get("dataset_id"),
                    "collection": dataset.get("collection"),
                    "score": _similarity(query, document),
                    "content": document,
                    "metadata": chunk.get("metadata") or {},
                }
            )
    rows.sort(key=lambda item: item["score"], reverse=True)
    rows = rows[: max(1, int(top_k))]
    return {
        "success": True,
        "status": "success" if rows else "degraded",
        "pack_id": pack_id,
        "service": "runtime_user_data_rag",
        "results": [
            {
                "dataset_id": item["dataset_id"],
                "collection": item["collection"],
                "score": item["score"],
                "content": item["content"],
                "citation": str(item["metadata"].get("source_path") or item["metadata"].get("filename") or item["dataset_id"]),
                "metadata": item["metadata"],
            }
            for item in rows
        ],
        "warnings": [] if rows else ["No matching user data chunks were found."],
        "limitations": ["Deterministic local RAG only; citations still require human review."],
    }


def answer_user_data_question(pack_id: str, query: str, dataset_ids: list[str] | None = None, top_k: int = 3) -> dict[str, Any]:
    search = search_user_data(pack_id, query, dataset_ids=dataset_ids, top_k=top_k)
    if not search.get("results"):
        return {
            "success": True,
            "status": "degraded",
            "pack_id": pack_id,
            "query": query,
            "error": "no_user_data_available",
            "answer": None,
            "citations": [],
            "warnings": ["No user data is available for a grounded answer."],
            "limitations": ["The system will not hallucinate an answer when user data is missing."],
        }
    results = search["results"]
    return {
        "success": True,
        "status": "success",
        "pack_id": pack_id,
        "query": query,
        "answer": " | ".join(str(item["content"])[:180] for item in results),
        "citations": [
            {"dataset_id": item["dataset_id"], "citation": item["citation"], "metadata": item["metadata"]}
            for item in results
        ],
        "warnings": [],
        "limitations": ["Grounded only in imported user data chunks.", "Requires human verification before external use."],
    }
