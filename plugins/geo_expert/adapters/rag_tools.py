from __future__ import annotations

from contextlib import suppress
import hashlib
import math
from pathlib import Path
import re
from typing import Any

from .config import REGULATIONS_ROOT, WORKFLOW_DB_PATH, chroma_config, dependency_error

EMBED_DIM = 128
TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]{1,}", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    tokens = [token.lower() for token in TOKEN_RE.findall(str(text or ""))]
    return [token for token in tokens if token.strip()]


def _deterministic_embedding(text: str, dim: int = EMBED_DIM) -> list[float]:
    vector = [0.0] * dim
    tokens = _tokenize(text)
    if not tokens:
        return vector
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for index in range(0, len(digest), 2):
            bucket = int.from_bytes(digest[index : index + 2], "big") % dim
            sign = -1.0 if digest[index] % 2 else 1.0
            weight = 1.0 + (digest[index + 1] / 255.0 if index + 1 < len(digest) else 0.0)
            vector[bucket] += sign * weight
    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 0.0:
        return vector
    return [value / norm for value in vector]


def _normalize_collection_names(raw_collections: Any) -> list[str]:
    names: list[str] = []
    for item in raw_collections or []:
        if isinstance(item, str):
            names.append(item)
            continue
        if hasattr(item, "name"):
            with suppress(Exception):
                names.append(str(item.name))
                continue
        if isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]))
    return [name for name in names if name]


def rag_status() -> dict[str, Any]:
    cfg = chroma_config()
    heartbeat = chroma_heartbeat()
    return {
        "success": True,
        "dependency": "chromadb",
        "configured": cfg["configured"],
        "disabled_by_default": True,
        "connects_on_import": False,
        "heartbeat_ok": heartbeat.get("success", False),
        "local_regulations_available": REGULATIONS_ROOT.exists(),
        "local_workflow_db_available": WORKFLOW_DB_PATH.exists(),
        "configured_aliases": {
            "regulations": cfg["regulations_collection_aliases"],
            "workflows": cfg["workflows_collection_aliases"],
            "map_metadata": cfg["map_metadata_collection_aliases"],
        },
    }


def chroma_heartbeat() -> dict[str, Any]:
    cfg = chroma_config()
    if not cfg["configured"]:
        return dependency_error(
            "chromadb",
            "ChromaDB is not configured or unavailable.",
            required_config=cfg["required_config"],
            error="chromadb_unavailable",
            status="degraded",
        )
    try:
        import requests

        base = cfg["url"] or f"http://{cfg['host']}:{cfg['port']}"
        for endpoint in ("/api/v2/heartbeat", "/api/v1/heartbeat"):
            with suppress(Exception):
                response = requests.get(f"{base}{endpoint}", timeout=2)
                if response.ok:
                    return {"success": True, "status": "success", "service": "chromadb", "endpoint": endpoint}
        return dependency_error(
            "chromadb",
            "ChromaDB heartbeat failed.",
            required_config=cfg["required_config"],
            error="chromadb_unavailable",
            status="degraded",
        )
    except Exception as exc:
        return dependency_error(
            "chromadb",
            f"ChromaDB heartbeat failed: {exc}",
            required_config=cfg["required_config"],
            error="chromadb_unavailable",
            status="degraded",
        )


def _get_chroma_client() -> tuple[Any | None, dict[str, Any] | None]:
    cfg = chroma_config()
    if not cfg["configured"]:
        return None, dependency_error(
            "chromadb",
            "ChromaDB is not configured or unavailable.",
            required_config=cfg["required_config"],
            error="chromadb_unavailable",
            status="degraded",
        )
    try:
        import chromadb

        client = chromadb.HttpClient(host=cfg["host"], port=int(cfg["port"]))
        return client, None
    except Exception as exc:
        return None, dependency_error(
            "chromadb",
            f"ChromaDB connection failed: {exc}",
            required_config=cfg["required_config"],
            error="chromadb_unavailable",
            status="degraded",
        )


def _choose_collection(logical_name: str, aliases: list[str]) -> tuple[Any | None, dict[str, Any]]:
    client, error = _get_chroma_client()
    info = {
        "logical_name": logical_name,
        "expected_collection": aliases[0] if aliases else None,
        "fallback_candidates": aliases[1:] if len(aliases) > 1 else [],
        "selected_collection": None,
        "collection_exists": False,
    }
    if error:
        return None, info | error
    raw_collections = client.list_collections()
    names = _normalize_collection_names(raw_collections)
    for candidate in aliases:
        if candidate in names:
            info["selected_collection"] = candidate
            info["collection_exists"] = True
            warnings = ["using_fallback_collection_alias"] if candidate != aliases[0] else []
            return client.get_collection(candidate), info | {"success": True, "warnings": warnings}
    return None, info | {
        "success": True,
        "status": "degraded",
        "used_real_service": False,
        "service": "local_text_fallback",
        "error": "chromadb_collection_missing",
        "message": f"No matching ChromaDB collection found for {logical_name}.",
        "warnings": [f"Missing collections: {', '.join(aliases)}"],
        "limitations": ["Falling back to local text search."],
    }


def _local_text_search(root: Path, query: str, top_k: int = 5) -> dict[str, Any]:
    if not root.exists():
        return dependency_error(
            "local_text_fallback",
            f"Local search root not found: {root}",
            required_config=[],
            error="data_unavailable",
        )
    lowered = str(query or "").lower().strip()
    matches: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".txt", ".md", ".json"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if lowered and lowered not in text.lower() and lowered not in path.name.lower():
            continue
        matches.append(
            {
                "title": path.stem,
                "content": text[:500],
                "path": str(path),
                "filename": path.name,
                "snippet": text[:240].replace("\r", " ").replace("\n", " "),
                "source": "local_text_fallback",
                "score": 0.2,
                "citation": str(path),
            }
        )
        if len(matches) >= top_k:
            break
    return {
        "success": True,
        "status": "degraded",
        "query": query,
        "used_real_service": False,
        "service": "local_text_fallback",
        "results": matches,
        "fallback_used": True,
        "warnings": [],
        "limitations": ["Local text fallback only."],
    }


def _query_collection(
    *,
    logical_name: str,
    aliases: list[str],
    query: str,
    top_k: int,
    where: dict[str, Any] | None = None,
) -> dict[str, Any]:
    collection, selected = _choose_collection(logical_name, aliases)
    if collection is None:
        return selected
    try:
        collection_metadata = dict(getattr(collection, "metadata", {}) or {})
        embedding_backend = str(collection_metadata.get("embedding_backend") or collection_metadata.get("embedding_mode") or "unknown")
        if embedding_backend.startswith("sentence_transformers"):
            quality_note = "local_semantic_embedding"
        elif embedding_backend.startswith("google") or embedding_backend.startswith("external"):
            quality_note = "external_embedding"
        else:
            quality_note = "dev_offline_validation"
        with suppress(Exception):
            if hasattr(collection, "count") and int(collection.count()) == 0:
                return {
                    "success": True,
                    "status": "degraded",
                    "used_real_service": False,
                    "service": "chromadb",
                    "collection": selected["selected_collection"],
                    "selected_collection": selected["selected_collection"],
                    "expected_collection": selected["expected_collection"],
                    "fallback_candidates": selected["fallback_candidates"],
                    "collection_metadata": collection_metadata,
                    "embedding_backend": embedding_backend,
                    "quality_note": quality_note,
                    "error": "collection_empty",
                    "results": [],
                    "warnings": ["ChromaDB collection exists but contains no documents."],
                    "limitations": ["Collection ingest may be required before semantic retrieval works."],
                }
        results = collection.query(
            query_embeddings=[_deterministic_embedding(query)],
            n_results=int(top_k),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        docs = ((results.get("documents") or [[]])[0]) or []
        metas = ((results.get("metadatas") or [[]])[0]) or []
        distances = ((results.get("distances") or [[]])[0]) or []
        token_candidates = [part.strip() for part in _tokenize(query) if len(part.strip()) >= 2]
        payload = []
        for index, doc in enumerate(docs):
            meta = metas[index] if index < len(metas) else {}
            token_hits = sum(1 for token in token_candidates if token and token in str(doc).lower())
            distance = float(distances[index]) if index < len(distances) else 1.0
            score = max(0.0, min(1.0, 1.0 - distance))
            if token_hits:
                score = max(score, min(1.0, 0.55 + token_hits * 0.1))
            payload.append(
                {
                    "title": str(meta.get("title") or meta.get("filename") or f"result-{index + 1}"),
                    "content": str(doc),
                    "source": str(meta.get("source") or meta.get("path") or selected["selected_collection"]),
                    "score": score,
                    "citation": str(meta.get("source") or meta.get("path") or selected["selected_collection"]),
                    "metadata": meta,
                    "snippet": str(doc)[:240].replace("\r", " ").replace("\n", " "),
                }
            )
        return {
            "success": True,
            "status": "success",
            "used_real_service": True,
            "service": "chromadb",
            "collection": selected["selected_collection"],
            "selected_collection": selected["selected_collection"],
            "expected_collection": selected["expected_collection"],
            "fallback_candidates": selected["fallback_candidates"],
            "collection_metadata": collection_metadata,
            "embedding_backend": embedding_backend,
            "quality_note": quality_note,
            "warnings": list(selected.get("warnings") or []),
            "results": payload,
            "query_ok": True,
            "result_count": len(payload),
            "limitations": [],
        }
    except Exception as exc:
        return {
            "success": True,
            "status": "degraded",
            "used_real_service": False,
            "service": "chromadb",
            "collection": selected["selected_collection"],
            "selected_collection": selected["selected_collection"],
            "expected_collection": selected["expected_collection"],
            "fallback_candidates": selected["fallback_candidates"],
            "collection_metadata": collection_metadata,
            "embedding_backend": embedding_backend,
            "quality_note": quality_note,
            "error": "chromadb_query_failed",
            "message": str(exc),
            "results": [],
            "warnings": [f"ChromaDB query failed: {exc}"],
            "limitations": ["Collection was reachable but query failed."],
        }


def search_regulations(query: str, source_filter: str | None = None, top_k: int = 5) -> dict[str, Any]:
    cfg = chroma_config()
    if not cfg["configured"]:
        fallback = _local_text_search(REGULATIONS_ROOT, query, top_k=top_k)
        fallback.update({"dependency": "chromadb", "source_filter": source_filter, "error": "chromadb_unavailable"})
        return fallback
    result = _query_collection(
        logical_name="regulations",
        aliases=list(cfg["regulations_collection_aliases"]),
        query=query,
        top_k=top_k,
        where={"source": source_filter} if source_filter else None,
    )
    if result.get("success") and result.get("used_real_service"):
        result["query"] = query
        result["source_filter"] = source_filter
        return result
    fallback = _local_text_search(REGULATIONS_ROOT, query, top_k=top_k)
    fallback.update(
        {
            "dependency": "chromadb",
            "source_filter": source_filter,
            "error": result.get("error", "chromadb_unavailable"),
            "warnings": list(dict.fromkeys([*(fallback.get("warnings") or []), *(result.get("warnings") or [])])),
            "selected_collection": result.get("selected_collection"),
            "expected_collection": result.get("expected_collection"),
            "fallback_candidates": result.get("fallback_candidates"),
        }
    )
    return fallback


def search_workflows(query: str, top_k: int = 5) -> dict[str, Any]:
    cfg = chroma_config()
    if not cfg["configured"]:
        fallback = _local_text_search(WORKFLOW_DB_PATH.parent, query, top_k=top_k)
        fallback["dependency"] = "chromadb"
        fallback["error"] = "chromadb_unavailable"
        return fallback
    result = _query_collection(
        logical_name="workflows",
        aliases=list(cfg["workflows_collection_aliases"]),
        query=query,
        top_k=top_k,
    )
    if result.get("success") and result.get("used_real_service"):
        result["query"] = query
        return result
    fallback = _local_text_search(WORKFLOW_DB_PATH.parent, query, top_k=top_k)
    fallback.update(
        {
            "dependency": "chromadb",
            "error": result.get("error", "chromadb_unavailable"),
            "warnings": list(dict.fromkeys([*(fallback.get("warnings") or []), *(result.get("warnings") or [])])),
            "selected_collection": result.get("selected_collection"),
            "expected_collection": result.get("expected_collection"),
            "fallback_candidates": result.get("fallback_candidates"),
        }
    )
    return fallback


def search_map_metadata(query: str, top_k: int = 3) -> dict[str, Any]:
    cfg = chroma_config()
    if not cfg["configured"]:
        return dependency_error(
            "chromadb",
            "Map metadata search requires ChromaDB configuration.",
            required_config=["CHROMA_HOST", "CHROMA_PORT"],
            query=query,
            top_k=top_k,
        )
    result = _query_collection(
        logical_name="map_metadata",
        aliases=list(cfg["map_metadata_collection_aliases"]),
        query=query,
        top_k=top_k,
    )
    if result.get("success") and result.get("used_real_service"):
        result["query"] = query
        return result
    return {
        "success": True,
        "status": "degraded",
        "error": result.get("error", "chromadb_unavailable"),
        "dependency": "chromadb",
        "service": "local_text_fallback",
        "message": result.get("message") or "Map metadata search degraded.",
        "required_config": cfg["required_config"],
        "used_real_service": False,
        "selected_collection": result.get("selected_collection"),
        "expected_collection": result.get("expected_collection"),
        "fallback_candidates": result.get("fallback_candidates"),
        "results": [],
        "warnings": list(result.get("warnings") or []),
        "limitations": ["No map metadata collection available."],
    }


__all__ = ["chroma_heartbeat", "rag_status", "search_map_metadata", "search_regulations", "search_workflows"]
