"""Importer for geo expert source files into SQLite."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

from .store import connect, initialize_database, rebuild_database, resolve_db_path

SUPPORTED_SUFFIXES = {".md", ".txt", ".py", ".json", ".jsonl", ".csv"}
EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
}
MAX_FILE_SIZE_BYTES = 512_000
TARGET_CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

SOURCE_PRIORITY_RULES = {
    "readme": 100,
    "legal": 95,
    "legal_candidate": 78,
    "analysis": 90,
    "database": 85,
    "data": 80,
    "script": 60,
    "unknown": 40,
    "test": 30,
    "app": 20,
}

LEGAL_SOURCE_DOMAINS = ["law", "land_management", "urban_planning"]
LEGAL_PATH_MARKERS = (
    "GEO/",
    "/GEO/",
    "geo法律/",
    "legal/",
    "/legal/",
    "law/",
    "/law/",
    "法規/",
    "法律/",
)
LEGAL_CONTENT_MARKERS = (
    "法",
    "條例",
    "辦法",
    "施行細則",
    "裁罰",
    "罰鍰",
    "行政處分",
    "國土計畫",
    "區域計畫",
    "水土保持",
    "都市更新",
    "農業發展",
)


def _looks_binary(raw: bytes) -> bool:
    if b"\x00" in raw:
        return True
    try:
        raw.decode("utf-8")
        return False
    except UnicodeDecodeError:
        return True


def _read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    if _looks_binary(raw):
        raise ValueError("binary file")
    return raw.decode("utf-8", errors="ignore")


def _normalize_content(path: Path, text: str) -> str:
    if path.suffix == ".json":
        try:
            return json.dumps(json.loads(text), ensure_ascii=False, indent=2)
        except Exception:
            return text
    if path.suffix == ".jsonl":
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                lines.append(json.dumps(json.loads(line), ensure_ascii=False, sort_keys=True))
            except Exception:
                lines.append(line)
        return "\n".join(lines)
    if path.suffix == ".csv":
        rows = []
        try:
            reader = csv.reader(text.splitlines())
            for row in reader:
                rows.append(", ".join(cell.strip() for cell in row))
            return "\n".join(rows)
        except Exception:
            return text
    return text


def _chunk_text(text: str, target_size: int = TARGET_CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    length = len(normalized)
    while start < length:
        end = min(start + target_size, length)
        if end < length:
            boundary = normalized.rfind(" ", start, min(end + 200, length))
            if boundary > start + 400:
                end = boundary
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(0, end - overlap)
    return chunks


def _looks_like_legal_path(rel_path: str, source_root: Path | None = None) -> bool:
    normalized = rel_path.replace("\\", "/")
    lowered = normalized.lower()
    if any(marker.lower() in lowered for marker in LEGAL_PATH_MARKERS):
        return True
    if source_root is not None and source_root.name.lower() == "geo":
        if "data/regulations" in lowered or "samples/legal" in lowered or "legal" in lowered:
            return True
    return False


def _looks_like_legal_content(text: str) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in LEGAL_CONTENT_MARKERS)


def _detect_source_metadata(
    rel_path: str,
    *,
    source_root: Path | None = None,
    content: str = "",
) -> tuple[str, int, list[str]]:
    normalized = rel_path.replace("\\", "/")
    lowered = normalized.lower()
    name = Path(normalized).name.lower()

    if _looks_like_legal_path(rel_path, source_root) or _looks_like_legal_content(content):
        source_type = "legal"
        return source_type, SOURCE_PRIORITY_RULES[source_type], LEGAL_SOURCE_DOMAINS

    if name.startswith("readme"):
        source_type = "readme"
    elif lowered.startswith("analysis/"):
        source_type = "analysis"
    elif lowered.startswith("database/"):
        source_type = "database"
    elif lowered.startswith("data/"):
        source_type = "data"
    elif lowered.startswith("scripts/"):
        source_type = "script"
    elif lowered.startswith("streamlit/") or name in {"app.py", "agent_chat.py"}:
        source_type = "app"
    elif "/tests/" in lowered or lowered.startswith("tests/") or name.startswith("test_"):
        source_type = "test"
    else:
        source_type = "unknown"

    source_domain = LEGAL_SOURCE_DOMAINS if source_type in {"legal", "legal_candidate"} else []
    return source_type, SOURCE_PRIORITY_RULES[source_type], source_domain


def _extract_section_title(path: Path, text: str) -> str | None:
    if path.suffix.lower() == ".md":
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip() or None
    if path.suffix.lower() == ".py":
        match = re.search(r'("""|\'\'\')\s*(.+?)\s*\1', text, re.DOTALL)
        if match:
            first_line = match.group(2).strip().splitlines()[0].strip()
            return first_line or None
    if path.suffix.lower() in {".json", ".jsonl"}:
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
        return first_line[:120] or None
    return None


def _iter_source_files(source_dir: Path):
    for path in sorted(source_dir.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if path.stat().st_size > MAX_FILE_SIZE_BYTES:
            yield path, "file too large"
            continue
        yield path, None


def import_source_directory(
    source_dir: str | Path,
    db_path: str | Path | None = None,
    rebuild: bool = True,
) -> dict:
    source_path = Path(source_dir).expanduser()
    if source_path.is_absolute():
        source_root = source_path.resolve()
    else:
        candidates = [
            Path.cwd() / source_path,
            Path.cwd().parent / source_path,
        ]
        source_root = next((candidate.resolve() for candidate in candidates if candidate.exists()), source_path.resolve())
    if not source_root.exists():
        raise FileNotFoundError(f"source_dir not found: {source_root}")

    resolved_db_path = resolve_db_path(db_path)
    conn = connect(resolved_db_path)
    try:
        if rebuild:
            rebuild_database(conn)
        else:
            initialize_database(conn)

        skipped_files: list[str] = []
        documents_imported = 0
        chunks_imported = 0
        source_type_counts: dict[str, int] = {}

        for path, skip_reason in _iter_source_files(source_root):
            rel_path = path.relative_to(source_root).as_posix()
            if skip_reason:
                skipped_files.append(f"{rel_path}: {skip_reason}")
                continue
            try:
                content = _normalize_content(path, _read_text_file(path))
            except ValueError:
                skipped_files.append(f"{rel_path}: binary file")
                continue
            except Exception as exc:
                skipped_files.append(f"{rel_path}: {exc}")
                continue

            chunks = _chunk_text(content)
            if not chunks:
                skipped_files.append(f"{rel_path}: empty content")
                continue

            title = path.stem
            source_type, source_priority, source_domain = _detect_source_metadata(
                rel_path,
                source_root=source_root,
                content=content,
            )
            section_title = _extract_section_title(path, content)
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            cur = conn.execute(
                """
                INSERT INTO documents(path, title, section_title, file_type, source_type, source_priority, source_domain, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rel_path,
                    title,
                    section_title,
                    path.suffix.lower(),
                    source_type,
                    source_priority,
                    json.dumps(source_domain, ensure_ascii=False),
                    content_hash,
                ),
            )
            document_id = cur.lastrowid
            documents_imported += 1
            source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1

            for chunk_index, chunk in enumerate(chunks):
                cur = conn.execute(
                    """
                    INSERT INTO chunks(document_id, chunk_index, text)
                    VALUES (?, ?, ?)
                    """,
                    (document_id, chunk_index, chunk),
                )
                chunk_id = cur.lastrowid
                conn.execute(
                    """
                    INSERT INTO chunks_fts(text, path, title, source_type, source_priority, chunk_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (chunk, rel_path, title, source_type, source_priority, str(chunk_id)),
                )
                chunks_imported += 1

        conn.commit()
    finally:
        conn.close()

    return {
        "success": True,
        "db_path": str(resolved_db_path),
        "documents_imported": documents_imported,
        "chunks_imported": chunks_imported,
        "skipped_files": skipped_files,
        "source_type_counts": source_type_counts,
    }
