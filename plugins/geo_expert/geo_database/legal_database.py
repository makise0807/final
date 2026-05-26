"""Legal knowledge-base wrappers built on top of the geo database store."""

from __future__ import annotations

from pathlib import Path

from .importer import import_source_directory
from .rag import answer_question
from .search import search_database

DEFAULT_LEGAL_DB_PATH = Path(".hermes/legal_database/legal_expert.db")


def import_legal_source_directory(
    source_dir: str | Path,
    db_path: str | Path | None = None,
    rebuild: bool = True,
) -> dict:
    """Import legal source files into the dedicated legal DB."""
    target_db = db_path or DEFAULT_LEGAL_DB_PATH
    return import_source_directory(source_dir, target_db, rebuild=rebuild)


def search_legal_database(
    query: str,
    db_path: str | Path | None = None,
    top_k: int = 5,
) -> dict:
    target_db = db_path or DEFAULT_LEGAL_DB_PATH
    return search_database(
        query,
        target_db,
        top_k=top_k,
        source_type_filter="legal",
    )


def answer_legal_question(
    question: str,
    db_path: str | Path | None = None,
    top_k: int = 8,
) -> dict:
    target_db = db_path or DEFAULT_LEGAL_DB_PATH
    return answer_question(
        question,
        target_db,
        top_k=top_k,
        source_type_filter="legal",
    )


__all__ = [
    "DEFAULT_LEGAL_DB_PATH",
    "answer_legal_question",
    "import_legal_source_directory",
    "search_legal_database",
]
