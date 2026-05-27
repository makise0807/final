from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.ingest_geo_expert_local_chroma import deterministic_embedding

from .schemas import USER_DATA_IMPORT_INPUT_TYPES
from .user_data_store import get_runtime_user_data_dir, upsert_dataset


def _read_text(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
    except Exception:
        return []
    return [text] if text else []


def _read_json(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(payload, dict):
        return [json.dumps(payload, ensure_ascii=False)]
    if isinstance(payload, list):
        return [json.dumps(item, ensure_ascii=False) for item in payload if item]
    return []


def _read_jsonl(path: Path) -> list[str]:
    try:
        return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except Exception:
        return []


def _read_csv(path: Path) -> list[str]:
    rows: list[str] = []
    try:
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if row:
                    rows.append(json.dumps(row, ensure_ascii=False))
    except Exception:
        return []
    return rows


def _read_docx(path: Path) -> tuple[list[str], str | None]:
    try:
        from docx import Document  # type: ignore
    except Exception:
        return [], "docx_dependency_missing"
    try:
        doc = Document(str(path))
    except Exception as exc:
        return [], f"docx_read_failed:{exc}"
    text = "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()).strip()
    return ([text] if text else []), None


def _read_pdf(path: Path) -> tuple[list[str], str | None]:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return [], "pdf_dependency_missing"
    try:
        reader = PdfReader(str(path))
        text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    except Exception as exc:
        return [], f"pdf_read_failed:{exc}"
    return ([text] if text else []), None


def _chunks_from_file(path: Path) -> tuple[list[str], str | None]:
    kind = path.suffix.lower().lstrip(".")
    if kind in {"txt", "md"}:
        return _read_text(path), None
    if kind == "json":
        return _read_json(path), None
    if kind == "jsonl":
        return _read_jsonl(path), None
    if kind == "csv":
        return _read_csv(path), None
    if kind == "docx":
        return _read_docx(path)
    if kind == "pdf":
        return _read_pdf(path)
    return [], "unsupported_file_type"


def import_user_data(*, pack: dict[str, Any], source_files: list[str], embedding_backend: str = "hash") -> dict[str, Any]:
    runtime_dir = get_runtime_user_data_dir()
    if not source_files:
        return {"success": False, "status": "degraded", "error": "no_source_files", "runtime_dir": str(runtime_dir)}
    chunks: list[dict[str, Any]] = []
    warnings: list[str] = []
    stored_files: list[str] = []
    pack_dir = runtime_dir / str(pack.get("pack_id") or "unknown_pack")
    pack_dir.mkdir(parents=True, exist_ok=True)
    for raw in source_files:
        path = Path(raw).expanduser()
        if not path.exists():
            warnings.append(f"missing_source:{path}")
            continue
        if path.suffix.lower().lstrip(".") not in USER_DATA_IMPORT_INPUT_TYPES:
            warnings.append(f"unsupported_source:{path.name}")
            continue
        texts, error = _chunks_from_file(path)
        if error:
            warnings.append(error)
            continue
        stored = pack_dir / path.name
        try:
            stored.write_bytes(path.read_bytes())
            stored_files.append(str(stored))
        except Exception as exc:
            warnings.append(f"copy_failed:{path.name}:{exc}")
        for index, text in enumerate(texts):
            text = str(text).strip()
            if not text:
                continue
            chunks.append(
                {
                    "id": hashlib.sha1(f"{path.resolve()}:{index}:{text}".encode("utf-8")).hexdigest()[:24],
                    "document": text,
                    "metadata": {
                        "source_path": str(path),
                        "stored_copy_path": str(stored),
                        "filename": path.name,
                        "chunk_index": index,
                        "pack_id": pack.get("pack_id"),
                        "collection": pack.get("user_data_collection"),
                    },
                    "embedding": deterministic_embedding(text),
                }
            )
    if not chunks:
        return {
            "success": False,
            "status": "degraded",
            "error": "no_user_data_available",
            "warnings": warnings,
            "runtime_dir": str(runtime_dir),
        }
    dataset_id = hashlib.sha1(f"{pack.get('pack_id')}|{'|'.join(source_files)}".encode("utf-8")).hexdigest()[:16]
    dataset_dir = pack_dir / dataset_id
    dataset_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = dataset_dir / "chunks.json"
    chunks_path.write_text(json.dumps({"chunks": chunks}, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_entry = {
        "dataset_id": dataset_id,
        "pack_id": pack.get("pack_id"),
        "collection": pack.get("user_data_collection"),
        "source_files": source_files,
        "stored_files": stored_files,
        "chunk_count": len(chunks),
        "chunks_path": str(chunks_path),
        "embedding_backend": embedding_backend,
    }
    upsert_dataset(manifest_entry)
    return {
        "success": True,
        "status": "success",
        "dataset_id": dataset_id,
        "pack_id": pack.get("pack_id"),
        "collection": pack.get("user_data_collection"),
        "source_files": source_files,
        "stored_files": stored_files,
        "chunk_count": len(chunks),
        "chunks_path": str(chunks_path),
        "runtime_dir": str(runtime_dir),
        "warnings": warnings,
    }
