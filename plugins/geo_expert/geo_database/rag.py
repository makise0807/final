"""Grounded RAG answering for the geo expert database."""

from __future__ import annotations

from .search import search_database
from .store import connect, resolve_db_path


LOW_CONFIDENCE_SOURCE_TYPES = {"app", "test"}


def _load_chunk_context(db_path: str, chunk_ids: list[str]) -> dict[str, dict]:
    if not chunk_ids:
        return {}
    conn = connect(db_path)
    try:
        placeholders = ",".join("?" for _ in chunk_ids)
        rows = conn.execute(
            f"""
            SELECT
                c.id AS chunk_id,
                c.text AS text,
                d.title AS title,
                d.path AS path,
                d.source_type AS source_type,
                d.source_priority AS source_priority,
                d.source_domain AS source_domain,
                d.section_title AS section_title
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.id IN ({placeholders})
            """,
            chunk_ids,
        ).fetchall()
    finally:
        conn.close()
    return {
        str(row["chunk_id"]): {
            "text": row["text"],
            "title": row["section_title"] or row["title"],
            "path": row["path"],
            "source_type": row["source_type"],
            "source_priority": row["source_priority"],
            "source_domain": row["source_domain"],
        }
        for row in rows
    }


def _build_no_context_answer() -> str:
    return (
        "1. 問題摘要\n"
        "本地資料庫尚未找到足夠相關的依據。\n"
        "2. EO/GIS workflow\n"
        "建議先補齊 AOI、time_range 與任務目標，再進入 workflow_plan / dry_run。\n"
        "3. 缺少資料\n"
        "- database context\n"
        "- relevant citations\n"
        "4. 限制聲明\n"
        "- 目前答案只根據本地 SQLite chunks，未執行任何真實 OpenEO backend。\n"
        "5. 下一步\n"
        "- 請補充 AOI / time_range / 法規背景，或重新匯入更相關的專家資料。"
    )


def answer_question(
    question: str,
    db_path: str | None = None,
    top_k: int = 8,
    *,
    source_type_filter: str | None = None,
    source_domain_filter: str | None = None,
) -> dict:
    resolved_db_path = str(resolve_db_path(db_path))
    search_result = search_database(
        question,
        resolved_db_path,
        top_k=top_k,
        source_type_filter=source_type_filter,
        source_domain_filter=source_domain_filter,
    )
    hits = search_result["hits"]
    if not hits:
        return {
            "success": True,
            "answer": _build_no_context_answer(),
            "citations": [],
            "missing_information": ["database context", "relevant citations"],
            "limitations": ["no grounded local source matched the question"],
        }

    chunk_lookup = _load_chunk_context(resolved_db_path, [hit["chunk_id"] for hit in hits])
    citations = []
    for hit in hits[: min(4, len(hits))]:
        chunk = chunk_lookup.get(hit["chunk_id"])
        if not chunk:
            continue
        citations.append(
            {
                "title": chunk["title"],
                "path": chunk["path"],
                "chunk_id": hit["chunk_id"],
                "source_type": chunk["source_type"],
                "source_domain": chunk["source_domain"],
                "quote": chunk["text"][:240].strip(),
            }
        )

    dominant_source_types = [hit["source_type"] for hit in hits[: min(3, len(hits))]]
    app_layer_dominant = (
        bool(dominant_source_types)
        and all(source_type in LOW_CONFIDENCE_SOURCE_TYPES for source_type in dominant_source_types)
    )
    limitations = [
        "This answer is grounded only in local SQLite database chunks.",
        "No real OpenEO backend call or EO execution has been performed.",
    ]
    missing_information = ["AOI", "time_range", "landuse_layer"]
    if app_layer_dominant:
        limitations.append(
            "Current hits are dominated by app-layer or test-layer code, so method documentation confidence is limited."
        )
        missing_information.append("method-focused analysis/workflow documents")

    grounded_lines = [
        f"- [{citation['source_type']}] {citation['title']} ({citation['path']}#{citation['chunk_id']}): {citation['quote']}"
        for citation in citations
    ]
    workflow_hint = (
        "Grounded facts come from the cited local documents only. Use geo_database.workflow_plan "
        "and geo_database.workflow_dry_run for deterministic read-only planning; do not treat this as real execution."
    )
    if app_layer_dominant:
        workflow_hint += " Prefer analysis/, database/, or legal sources over app/test files."

    answer = (
        "1. 問題摘要\n"
        + "\n".join(grounded_lines)
        + "\n2. EO/GIS workflow\n"
        + workflow_hint
        + "\n3. 缺少資料\n"
        + "- " + "\n- ".join(dict.fromkeys(missing_information))
        + "\n4. 限制聲明\n"
        + "- " + "\n- ".join(limitations)
        + "\n5. 下一步\n"
        + "請先補 AOI / time_range / legal context，再視需要進入 workflow_plan 與 dry_run。"
    )
    return {
        "success": True,
        "answer": answer,
        "citations": citations,
        "missing_information": list(dict.fromkeys(missing_information)),
        "limitations": limitations,
    }
