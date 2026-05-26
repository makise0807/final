from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence

DEFAULT_SOURCE_ROOT = Path(os.getenv("GEO_EXPERT_SOURCE_ROOT", r"C:\Users\34620\OneDrive\Desktop\geo-orchestrator"))
DEFAULT_PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "plugins" / "geo_expert" / "data"
DEFAULT_COLLECTION = os.getenv("CHROMA_COLLECTION_REGULATIONS", "urban_regulations")
EMBED_DIM = 128
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
EMBEDDING_NAME = "deterministic_hash_v1"
DEFAULT_ST_MODEL = os.getenv("GEO_EXPERT_RAG_EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]{1,}", re.UNICODE)


class DeterministicHashEmbeddingFunction:
    def name(self) -> str:
        return EMBEDDING_NAME

    def __call__(self, input: Sequence[str] | str) -> list[list[float]]:
        if isinstance(input, str):
            return [deterministic_embedding(input)]
        return [deterministic_embedding(text) for text in input]


class SentenceTransformersEmbeddingFunction:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        from sentence_transformers import SentenceTransformer  # type: ignore

        self._model = SentenceTransformer(model_name, local_files_only=True)

    def name(self) -> str:
        return f"sentence_transformers:{self.model_name}"

    def __call__(self, input: Sequence[str] | str) -> list[list[float]]:
        texts = [input] if isinstance(input, str) else list(input)
        vectors = self._model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return [[float(value) for value in row] for row in vectors]


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(str(text or "")) if token.strip()]


def deterministic_embedding(text: str, dim: int = EMBED_DIM) -> list[float]:
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


def _stable_doc_id(source_path: Path, chunk_index: int, chunk: str, source_type: str) -> str:
    payload = f"{source_type}:{source_path.resolve()}:{chunk_index}:{hashlib.sha1(chunk.encode('utf-8')).hexdigest()}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:24]


def _chunk_text(text: str, *, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    cleaned = str(text or "").strip()
    if not cleaned:
        return []
    chunks: list[str] = []
    start = 0
    step = max(1, chunk_size - overlap)
    while start < len(cleaned):
        chunk = cleaned[start : start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks


def _infer_source_type(path: Path) -> str:
    lowered = str(path).lower()
    if "regulation" in lowered or "法" in path.stem:
        return "regulation"
    if "workflow" in lowered:
        return "workflow"
    if "expert_knowledge" in lowered:
        return "expert_knowledge"
    return "unknown"


def _law_name(path: Path) -> str | None:
    stem = path.stem.strip()
    return stem or None


def _workflow_docs(path: Path) -> list[tuple[str, str, dict[str, Any]]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    docs: list[tuple[str, str, dict[str, Any]]] = []
    if isinstance(payload, dict):
        items = payload.get("workflows") or payload.get("items") or []
    elif isinstance(payload, list):
        items = payload
    else:
        items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        workflow_id = str(item.get("workflow_id") or "")
        title = str(item.get("title") or workflow_id or path.stem)
        text = json.dumps(item, ensure_ascii=False, sort_keys=True)
        for idx, chunk in enumerate(_chunk_text(text)):
            docs.append(
                (
                    _stable_doc_id(path, idx, chunk, "workflow"),
                    chunk,
                    {
                        "source_path": str(path),
                        "source_type": "workflow",
                        "title": title,
                        "workflow_id": workflow_id,
                        "law_name": None,
                        "chunk_index": idx,
                        "filename": path.name,
                    },
                )
            )
    return docs


def collect_corpus_documents(
    *,
    source_roots: Sequence[Path] | None = None,
    plugin_root: Path = DEFAULT_PLUGIN_ROOT,
) -> tuple[list[tuple[str, str, dict[str, Any]]], dict[str, Any]]:
    roots = list(source_roots or [DEFAULT_SOURCE_ROOT])
    candidates = [root / "data" / "regulations" for root in roots]
    candidates.extend([root / "data" / "workflow_db" / "expert_workflows.json" for root in roots])
    candidates.extend(
        [
            plugin_root / "expert_knowledge",
            plugin_root / "workflow_db" / "expert_workflows.json",
        ]
    )
    docs: list[tuple[str, str, dict[str, Any]]] = []
    scanned_sources: list[str] = []
    skipped_empty_files: list[str] = []
    source_type_counter: Counter[str] = Counter()
    chunks_generated = 0

    for candidate in candidates:
        scanned_sources.append(str(candidate))
        if not candidate.exists():
            continue
        if candidate.is_file() and candidate.suffix.lower() == ".json":
            items = _workflow_docs(candidate)
            docs.extend(items)
            source_type_counter["workflow"] += len(items)
            chunks_generated += len(items)
            continue
        if not candidate.is_dir():
            continue
        for path in sorted(candidate.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".txt", ".md", ".json"}:
                continue
            if path.suffix.lower() == ".json" and "workflow" in path.name.lower():
                items = _workflow_docs(path)
                docs.extend(items)
                source_type_counter["workflow"] += len(items)
                chunks_generated += len(items)
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            chunks = _chunk_text(text)
            if not chunks:
                skipped_empty_files.append(str(path))
                continue
            source_type = _infer_source_type(path)
            for idx, chunk in enumerate(chunks):
                docs.append(
                    (
                        _stable_doc_id(path, idx, chunk, source_type),
                        chunk,
                        {
                            "source_path": str(path),
                            "source_type": source_type,
                            "title": path.stem,
                            "workflow_id": None,
                            "law_name": _law_name(path),
                            "chunk_index": idx,
                            "filename": path.name,
                        },
                    )
                )
            source_type_counter[source_type] += len(chunks)
            chunks_generated += len(chunks)

    deduped: list[tuple[str, str, dict[str, Any]]] = []
    seen_ids: set[str] = set()
    seen_payloads: set[tuple[str, str]] = set()
    for doc_id, document, metadata in docs:
        if not document.strip():
            continue
        payload_key = (str(metadata.get("source_path") or ""), document)
        if payload_key in seen_payloads:
            continue
        seen_payloads.add(payload_key)
        unique_id = doc_id
        counter = 1
        while unique_id in seen_ids:
            unique_id = f"{doc_id}-{counter}"
            counter += 1
        seen_ids.add(unique_id)
        deduped.append((unique_id, document, metadata))

    summary = {
        "sources_scanned": scanned_sources,
        "chunks_generated": chunks_generated,
        "documents_collected": len(deduped),
        "skipped_empty_files": skipped_empty_files,
        "source_type_breakdown": dict(source_type_counter),
    }
    return deduped, summary


def _create_client() -> tuple[Any | None, dict[str, Any] | None]:
    try:
        import chromadb
        import requests
    except Exception as exc:
        return None, {"success": False, "status": "degraded", "error": "dependency_unavailable", "message": str(exc)}
    host = os.getenv("CHROMA_HOST", "localhost")
    port = int(os.getenv("CHROMA_PORT", "8000"))
    url = os.getenv("CHROMA_URL", f"http://{host}:{port}")
    for endpoint in ("/api/v2/heartbeat", "/api/v1/heartbeat"):
        try:
            response = requests.get(f"{url}{endpoint}", timeout=2)
            if response.ok:
                return chromadb.HttpClient(host=host, port=port), None
        except Exception:
            continue
    return None, {
        "success": False,
        "status": "degraded",
        "error": "heartbeat_failed",
        "message": "ChromaDB heartbeat failed.",
        "url": url,
    }


def _resolve_embedding_backend(
    backend: str,
    model_name: str | None = None,
) -> tuple[Any | None, str, str | None]:
    normalized = str(backend or "hash").strip().lower()
    if normalized == "hash":
        return DeterministicHashEmbeddingFunction(), EMBEDDING_NAME, None
    if normalized == "sentence_transformers":
        try:
            embedding_fn = SentenceTransformersEmbeddingFunction(model_name or DEFAULT_ST_MODEL)
            return embedding_fn, embedding_fn.name(), None
        except ImportError:
            return None, normalized, "sentence_transformers_missing"
        except Exception as exc:
            return None, normalized, f"sentence_transformers_unavailable:{exc}"
    if normalized == "chroma_default":
        return None, "chroma_default", None
    return None, normalized, "unsupported_embedding_backend"


def _batched(items: Sequence[tuple[str, str, dict[str, Any]]], batch_size: int = 50) -> Iterable[Sequence[tuple[str, str, dict[str, Any]]]]:
    for index in range(0, len(items), batch_size):
        yield items[index : index + batch_size]


def ingest(
    collection_name: str,
    *,
    reset: bool = False,
    limit: int | None = None,
    verbose: bool = False,
    dry_run: bool = False,
    source_roots: Sequence[Path] | None = None,
    embedding_backend: str = "hash",
    embedding_model: str | None = None,
) -> dict[str, Any]:
    docs, summary = collect_corpus_documents(source_roots=source_roots)
    if limit is not None:
        docs = docs[: max(0, int(limit))]
    if not docs:
        return {
            "success": False,
            "status": "degraded",
            "error": "no_documents_found",
            "message": "No local corpus documents found.",
            "collection": collection_name,
            "corpus_summary": summary,
        }
    if dry_run:
        _embedding_fn, embedding_name, embedding_error = _resolve_embedding_backend(embedding_backend, embedding_model)
        return {
            "success": embedding_error is None,
            "status": "success" if embedding_error is None else "degraded",
            "collection": collection_name,
            "documents_added": 0,
            "doc_count": len(docs),
            "embedding": embedding_name,
            "embedding_backend": embedding_backend,
            "error": embedding_error,
            "dry_run": True,
            "corpus_summary": summary,
        }
    client, error = _create_client()
    if error:
        error["collection"] = collection_name
        error["corpus_summary"] = summary
        return error
    embedding_fn, embedding_name, embedding_error = _resolve_embedding_backend(embedding_backend, embedding_model)
    if embedding_error:
        return {
            "success": False,
            "status": "degraded",
            "error": embedding_error,
            "collection": collection_name,
            "embedding_backend": embedding_backend,
            "embedding": embedding_name,
            "corpus_summary": summary,
            "message": "Selected embedding backend is unavailable in this environment.",
        }
    try:
        if reset:
            try:
                client.delete_collection(collection_name)
            except Exception:
                pass
        get_or_create_kwargs: dict[str, Any] = {
            "name": collection_name,
            "metadata": {
                "embedding_mode": embedding_name,
                "embedding_backend": embedding_backend,
            },
        }
        if embedding_backend != "chroma_default":
            get_or_create_kwargs["embedding_function"] = embedding_fn
        collection = client.get_or_create_collection(**get_or_create_kwargs)
        processed = 0
        for batch in _batched(docs):
            ids = [item[0] for item in batch]
            documents = [item[1] for item in batch]
            metadatas = [item[2] for item in batch]
            upsert_kwargs: dict[str, Any] = {
                "ids": ids,
                "documents": documents,
                "metadatas": metadatas,
            }
            if embedding_backend != "chroma_default":
                upsert_kwargs["embeddings"] = embedding_fn(documents)
            collection.upsert(**upsert_kwargs)
            processed += len(batch)
            if verbose and processed % 10 == 0:
                print(json.dumps({"progress": processed, "collection": collection_name, "embedding_backend": embedding_backend}, ensure_ascii=False))
        doc_count = int(collection.count())
        return {
            "success": True,
            "status": "success",
            "collection": collection_name,
            "documents_added": processed,
            "doc_count": doc_count,
            "embedding": embedding_name,
            "embedding_backend": embedding_backend,
            "corpus_summary": summary,
        }
    except Exception as exc:
        return {
            "success": False,
            "status": "degraded",
            "error": "chroma_upsert_failed",
            "message": str(exc),
            "collection": collection_name,
            "documents_attempted": len(docs),
            "embedding": embedding_name,
            "embedding_backend": embedding_backend,
            "corpus_summary": summary,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline deterministic Geo Expert Chroma ingest helper.")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--reset", action="store_true", help="Delete and recreate only the target collection before ingest.")
    parser.add_argument("--limit", type=int, default=None, help="Optionally cap corpus documents for smoke testing.")
    parser.add_argument("--verbose", action="store_true", help="Print progress every 10 ingested documents.")
    parser.add_argument("--dry-run", action="store_true", help="Scan and summarize corpus without writing to Chroma.")
    parser.add_argument("--source-root", action="append", default=None, help="Add an extra source root. Can be provided multiple times.")
    parser.add_argument("--embedding-backend", choices=["hash", "sentence_transformers", "chroma_default"], default="hash")
    parser.add_argument("--embedding-model", default=os.getenv("GEO_EXPERT_RAG_EMBEDDING_MODEL"))
    args = parser.parse_args()
    roots = [Path(item) for item in args.source_root] if args.source_root else [DEFAULT_SOURCE_ROOT]
    print(
        json.dumps(
            ingest(
                args.collection,
                reset=args.reset,
                limit=args.limit,
                verbose=args.verbose,
                dry_run=args.dry_run,
                source_roots=roots,
                embedding_backend=args.embedding_backend,
                embedding_model=args.embedding_model,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
