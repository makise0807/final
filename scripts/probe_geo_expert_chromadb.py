from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from collections import Counter
from typing import Any
from urllib.parse import urlparse

EMBED_DIM = 128
TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]{1,}", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(str(text or "")) if token.strip()]


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


def _alias_list(raw: str | None, defaults: list[str]) -> list[str]:
    if not raw:
        return list(defaults)
    values = [item.strip() for item in str(raw).replace(";", ",").split(",")]
    return [item for item in values if item] or list(defaults)


def _config() -> dict[str, Any]:
    url = os.getenv("CHROMA_URL")
    host = os.getenv("CHROMA_HOST", "localhost")
    port = os.getenv("CHROMA_PORT", "8000")
    if url and "://" in url:
        parsed = urlparse(url)
        host = parsed.hostname or host
        port = str(parsed.port or port)
    return {
        "url": url or f"http://{host}:{port}",
        "host": host,
        "port": port,
        "collections": {
            "regulations": _alias_list(os.getenv("CHROMA_COLLECTION_REGULATIONS"), ["geo_regulations", "urban_regulations"]),
            "workflows": _alias_list(os.getenv("CHROMA_COLLECTION_WORKFLOWS"), ["geo_workflows", "urban_regulations"]),
            "map_metadata": _alias_list(os.getenv("CHROMA_COLLECTION_MAP_METADATA"), ["geo_map_data", "urban_regulations"]),
        },
    }


def _heartbeat(base_url: str) -> dict[str, Any]:
    try:
        import requests

        for endpoint in ("/api/v2/heartbeat", "/api/v1/heartbeat"):
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=2)
                if response.ok:
                    return {"success": True, "endpoint": endpoint, "status_code": response.status_code}
            except Exception:
                continue
        return {"success": False, "error": "heartbeat_failed", "message": "No ChromaDB heartbeat endpoint responded."}
    except Exception as exc:
        return {"success": False, "error": "requests_unavailable", "message": str(exc)}


def _normalize_collection_names(raw_collections: Any) -> list[str]:
    names: list[str] = []
    for item in raw_collections or []:
        if isinstance(item, str):
            names.append(item)
        elif hasattr(item, "name"):
            names.append(str(getattr(item, "name")))
        elif isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]))
    return [name for name in names if name]


def _collection_metadata_summary(collection: Any) -> dict[str, Any]:
    metadata = dict(getattr(collection, "metadata", {}) or {})
    return {
        "metadata": metadata,
        "embedding_backend": metadata.get("embedding_backend") or metadata.get("embedding_mode"),
    }


def _summarize_legal_metadata(metadatas: list[dict[str, Any]]) -> dict[str, Any]:
    law_names = sorted({str(item.get("law_name")) for item in metadatas if item.get("law_name")})
    legal_text_count = sum(1 for item in metadatas if item.get("source_type") == "legal_text")
    article_chunks_count = sum(1 for item in metadatas if item.get("chunk_kind") == "article")
    issue_tags = Counter()
    for item in metadatas:
        for tag in item.get("issue_tags") or []:
            issue_tags[str(tag)] += 1
    sample_citations = [
        str(item.get("citation_key") or item.get("law_name") or "")
        for item in metadatas
        if item.get("citation_key") or item.get("law_name")
    ][:5]
    return {
        "legal_text_count": legal_text_count,
        "law_names": law_names,
        "sample_citations": sample_citations,
        "article_chunks_count": article_chunks_count,
        "issue_tags_count": dict(issue_tags),
    }


def probe_chromadb() -> dict[str, Any]:
    cfg = _config()
    heartbeat = _heartbeat(cfg["url"])
    try:
        import chromadb
    except Exception as exc:
        return {
            "success": False,
            "status": "degraded",
            "service": "chromadb",
            "config": cfg,
            "heartbeat": heartbeat,
            "error": "chromadb_unavailable",
            "message": str(exc),
            "collections": [],
            "collection_checks": [],
        }
    try:
        client = chromadb.HttpClient(host=cfg["host"], port=int(cfg["port"]))
        raw_collections = client.list_collections()
        names = _normalize_collection_names(raw_collections)
        checks = []
        for logical_name, aliases in cfg["collections"].items():
            selected = next((candidate for candidate in aliases if candidate in names), None)
            check = {
                "logical_name": logical_name,
                "expected_collection": aliases[0] if aliases else None,
                "fallback_candidates": aliases[1:] if len(aliases) > 1 else [],
                "selected_collection": selected,
                "collection_exists": bool(selected),
                "query_ok": False,
                "result_count": 0,
                "doc_count": 0,
            }
            if not selected:
                check["status"] = "collection_missing"
                checks.append(check)
                continue
            collection = client.get_collection(selected)
            summary = _collection_metadata_summary(collection)
            check["collection_metadata"] = summary["metadata"]
            check["embedding_backend"] = summary["embedding_backend"]
            try:
                check["doc_count"] = int(collection.count())
                if check["doc_count"] <= 0:
                    check["status"] = "collection_empty"
                    checks.append(check)
                    continue
                query_result = collection.query(
                    query_embeddings=[_deterministic_embedding("農業區 違章工廠 非都市土地使用管制")],
                    n_results=3,
                    include=["documents", "metadatas", "distances"],
                )
                documents = ((query_result.get("documents") or [[]])[0]) or []
                metadatas = [dict(item or {}) for item in (((query_result.get("metadatas") or [[]])[0]) or [])]
                check["status"] = "success" if documents else "collection_empty"
                check["query_ok"] = True
                check["result_count"] = len(documents)
                check["used_real_service"] = bool(documents)
                check["sample_metadata"] = metadatas[0] if metadatas else None
                check.update(_summarize_legal_metadata(metadatas))
            except Exception as exc:
                check["status"] = "degraded"
                check["query_ok"] = False
                check["used_real_service"] = False
                check["error"] = "query_failed"
                check["message"] = str(exc)
            checks.append(check)
        return {
            "success": True,
            "status": "success" if heartbeat.get("success") else "degraded",
            "service": "chromadb",
            "config": cfg,
            "heartbeat": heartbeat,
            "collections": sorted(names),
            "collection_checks": checks,
        }
    except Exception as exc:
        return {
            "success": False,
            "status": "degraded",
            "service": "chromadb",
            "config": cfg,
            "heartbeat": heartbeat,
            "error": "chromadb_probe_failed",
            "message": str(exc),
            "collections": [],
            "collection_checks": [],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Geo Expert ChromaDB probe.")
    parser.parse_args()
    print(json.dumps(probe_chromadb(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
