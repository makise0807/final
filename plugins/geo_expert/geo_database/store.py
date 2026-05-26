"""SQLite storage primitives for the local geo expert database."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(".hermes/geo_database/geo_expert.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL,
    title TEXT,
    section_title TEXT,
    file_type TEXT,
    source_type TEXT,
    source_priority INTEGER,
    source_domain TEXT,
    content_hash TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    FOREIGN KEY(document_id) REFERENCES documents(id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text,
    path UNINDEXED,
    title UNINDEXED,
    source_type UNINDEXED,
    source_priority UNINDEXED,
    chunk_id UNINDEXED
);
"""


def resolve_db_path(db_path: str | Path | None = None) -> Path:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    return path.expanduser().resolve()


def ensure_parent_dir(db_path: str | Path | None = None) -> Path:
    path = resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = ensure_parent_dir(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialize_database(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    _ensure_documents_source_domain_column(conn)
    conn.commit()


def rebuild_database(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS chunks_fts;
        DROP TABLE IF EXISTS chunks;
        DROP TABLE IF EXISTS documents;
        """
    )
    initialize_database(conn)


def _ensure_documents_source_domain_column(conn: sqlite3.Connection) -> None:
    """Add ``documents.source_domain`` when opening an older database."""
    try:
        rows = conn.execute("PRAGMA table_info(documents)").fetchall()
    except sqlite3.Error:
        return
    columns = {row[1] for row in rows}
    if "source_domain" in columns:
        return
    try:
        conn.execute("ALTER TABLE documents ADD COLUMN source_domain TEXT")
    except sqlite3.Error:
        pass
