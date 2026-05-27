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


def search_user_data(
    pack_id: str,
    query: str,
    dataset_ids: list[str] | None = None,
    top_k: int = 5,
    collection_name: str | None = None,
) -> dict[str, Any]:
    requested_ids = [item for item in (dataset_ids or []) if item]
    datasets = list_datasets(pack_id)
    if requested_ids:
        allowed = set(requested_ids)
        datasets = [item for item in datasets if item.get("dataset_id") in allowed]
    collection = collection_name or str((datasets[0].get("collection") if datasets else "") or "")

    if not datasets:
        return {
            "success": True,
            "status": "no_user_data_available",
            "pack_id": pack_id,
            "collection": collection,
            "dataset_ids": requested_ids,
            "query": query,
            "hits": [],
            "citations": [],
            "reason": "No imported user datasets are available for this pack.",
            "warnings": ["No imported user datasets are available for this pack."],
            "limitations": ["User-data RAG requires imported runtime data in outputs/geo_expert/user_data/."],
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

    hits = [
        {
            "dataset_id": item["dataset_id"],
            "collection": item["collection"],
            "score": item["score"],
            "content": item["content"],
            "citation": str(
                item["metadata"].get("source_path")
                or item["metadata"].get("filename")
                or item["dataset_id"]
            ),
            "metadata": item["metadata"],
        }
        for item in rows
    ]
    citations = [
        {
            "dataset_id": item["dataset_id"],
            "citation": item["citation"],
            "metadata": item["metadata"],
        }
        for item in hits
    ]
    if not hits:
        return {
            "success": True,
            "status": "degraded",
            "pack_id": pack_id,
            "collection": collection,
            "dataset_ids": [str(item.get("dataset_id") or "") for item in datasets],
            "query": query,
            "hits": [],
            "citations": [],
            "reason": "Imported user datasets exist, but no matching chunks were found for this query.",
            "warnings": ["No matching user data chunks were found."],
            "limitations": ["Deterministic local RAG only; citations still require human review."],
        }
    return {
        "success": True,
        "status": "ok",
        "pack_id": pack_id,
        "collection": collection or str(hits[0].get("collection") or ""),
        "dataset_ids": sorted({str(item["dataset_id"]) for item in hits}),
        "query": query,
        "hits": hits,
        "citations": citations,
        "reason": f"Retrieved {len(hits)} user-data hits for grounded pack analysis.",
        "warnings": [],
        "limitations": ["Deterministic local RAG only; citations still require human review."],
    }


def answer_user_data_question(
    pack_id: str,
    query: str,
    dataset_ids: list[str] | None = None,
    top_k: int = 3,
    collection_name: str | None = None,
) -> dict[str, Any]:
    search = search_user_data(
        pack_id,
        query,
        dataset_ids=dataset_ids,
        top_k=top_k,
        collection_name=collection_name,
    )
    if not search.get("hits"):
        return {
            "success": True,
            "status": "no_user_data_available",
            "pack_id": pack_id,
            "collection": search.get("collection"),
            "dataset_ids": search.get("dataset_ids") or [],
            "query": query,
            "answer": None,
            "citations": [],
            "reason": "No user data is available for a grounded answer.",
            "warnings": ["No user data is available for a grounded answer."],
            "limitations": ["The system will not hallucinate an answer when user data is missing."],
        }

    hits = list(search.get("hits") or [])
    answer_parts = [str(item.get("content") or "")[:180] for item in hits if str(item.get("content") or "").strip()]
    return {
        "success": True,
        "status": "ok",
        "pack_id": pack_id,
        "collection": search.get("collection"),
        "dataset_ids": search.get("dataset_ids") or [],
        "query": query,
        "answer": " | ".join(answer_parts),
        "citations": search.get("citations") or [],
        "reason": f"Grounded answer built from {len(hits)} imported user-data hits.",
        "warnings": [],
        "limitations": ["Grounded only in imported user data chunks.", "Requires human verification before external use."],
    }
