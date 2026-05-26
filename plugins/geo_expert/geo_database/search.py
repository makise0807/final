"""Keyword and FTS search over the geo expert database."""

from __future__ import annotations

import math
import re

from .store import connect, initialize_database, resolve_db_path


def _build_snippet(text: str, query: str, size: int = 220) -> str:
    lowered_text = text.lower()
    lowered_query = query.lower()
    idx = lowered_text.find(lowered_query)
    if idx == -1:
        return text[:size].strip()
    start = max(0, idx - 80)
    end = min(len(text), idx + len(query) + 120)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet += "..."
    return snippet


def _query_tokens(query: str) -> list[str]:
    tokens = [token for token in re.split(r"\W+", query.lower()) if len(token) >= 3]
    return tokens or [query.lower()]


def _query_category_boost(query: str, path: str, source_type: str) -> float:
    lowered_query = query.lower()
    lowered_path = path.lower()
    boost = 0.0
    workflow_query = any(token in lowered_query for token in ("workflow", "plan"))
    eo_query = any(token in lowered_query for token in ("sentinel", "ndvi", "ndbi", "cloud mask", "landcover", "openeo"))
    enforcement_query = any(token in lowered_query for token in ("違章工廠", "違法", "農地", "山坡地", "國土計畫"))
    legal_query = any(token in lowered_query for token in ("法", "法規", "條例", "辦法", "裁罰", "國土計畫", "都市更新", "農業發展", "區域計畫"))
    test_query = any(token in lowered_query for token in ("test", "pytest"))

    if workflow_query and (source_type in {"analysis", "readme"} or "workflow_db" in lowered_path):
        boost += 20.0
    if eo_query and source_type in {"analysis", "database", "readme"}:
        boost += 18.0
    if enforcement_query and (source_type in {"analysis", "data"} or "workflow" in lowered_path):
        boost += 16.0
    if legal_query and source_type in {"legal", "legal_candidate", "readme", "database", "data"}:
        boost += 22.0
    if source_type == "test" and not test_query:
        boost -= 18.0
    return boost


def _path_penalty(path: str, source_type: str) -> float:
    lowered_path = path.lower()
    penalty = 0.0
    if source_type == "app":
        penalty -= 35.0
    if "agent_chat.py" in lowered_path:
        penalty -= 25.0
    if "app.py" in lowered_path and source_type == "app":
        penalty -= 15.0
    if "streamlit/" in lowered_path:
        penalty -= 12.0
    if source_type == "test":
        penalty -= 12.0
    if source_type == "analysis":
        penalty += 12.0
    if source_type == "database":
        penalty += 10.0
    if source_type == "readme":
        penalty += 10.0
    if source_type == "legal":
        penalty += 26.0
    if source_type == "legal_candidate":
        penalty += 12.0
    if "workflow_db" in lowered_path:
        penalty += 14.0
    if source_type == "data":
        penalty += 6.0
    return penalty


def _token_match_score(text: str, tokens: list[str]) -> float:
    lowered_text = text.lower()
    matched = sum(1 for token in tokens if token in lowered_text)
    density = matched / max(len(tokens), 1)
    return density * 40.0 + matched * 5.0


def _fts_score(raw_score: float) -> float:
    normalized = max(raw_score, 0.0)
    return 100.0 / (1.0 + math.log1p(normalized))


def _combined_score(*, raw_score: float, is_fts: bool, row, query: str, tokens: list[str]) -> float:
    lexical = _fts_score(raw_score) if is_fts else _token_match_score(row["text"], tokens)
    source_priority = float(row["source_priority"] or 0)
    path_boost = _path_penalty(row["path"], row["source_type"])
    query_boost = _query_category_boost(query, row["path"], row["source_type"])
    return lexical + source_priority + path_boost + query_boost


def _apply_filters(sql: str, source_type_filter: str | None, source_domain_filter: str | None) -> tuple[str, list[str]]:
    filter_sql = ""
    params: list[str] = []
    if source_type_filter:
        filter_sql += " AND d.source_type = ?"
        params.append(source_type_filter)
    if source_domain_filter:
        filter_sql += " AND COALESCE(d.source_domain, '') LIKE ?"
        params.append(f"%{source_domain_filter}%")
    return sql + filter_sql, params


def search_database(
    query: str,
    db_path: str | None = None,
    top_k: int = 5,
    *,
    source_type_filter: str | None = None,
    source_domain_filter: str | None = None,
) -> dict:
    if not query or not query.strip():
        return {"success": True, "query": query, "hits": []}

    resolved_db_path = resolve_db_path(db_path)
    tokens = _query_tokens(query)
    conn = connect(resolved_db_path)
    try:
        initialize_database(conn)
        try:
            sql, extra_params = _apply_filters(
                """
                SELECT
                    bm25(chunks_fts) AS score,
                    d.path AS path,
                    COALESCE(d.section_title, d.title) AS title,
                    d.source_type AS source_type,
                    d.source_priority AS source_priority,
                    d.source_domain AS source_domain,
                    c.id AS chunk_id,
                    c.text AS text
                FROM chunks_fts
                JOIN chunks c ON c.id = CAST(chunks_fts.chunk_id AS INTEGER)
                JOIN documents d ON d.id = c.document_id
                WHERE chunks_fts MATCH ?
                """,
                source_type_filter,
                source_domain_filter,
            )
            rows = conn.execute(
                sql + " LIMIT ?",
                (query, *extra_params, max(top_k * 10, 20)),
            ).fetchall()
            is_fts = True
        except Exception:
            rows = []
            is_fts = False
        if not rows:
            where_clause = " OR ".join("lower(c.text) LIKE ?" for _ in tokens)
            params = [f"%{token}%" for token in tokens]
            sql, extra_params = _apply_filters(
                f"""
                SELECT
                    0.0 AS score,
                    d.path AS path,
                    COALESCE(d.section_title, d.title) AS title,
                    d.source_type AS source_type,
                    d.source_priority AS source_priority,
                    d.source_domain AS source_domain,
                    c.id AS chunk_id,
                    c.text AS text
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE {where_clause}
                """,
                source_type_filter,
                source_domain_filter,
            )
            rows = conn.execute(
                sql + " LIMIT ?",
                (*params, *extra_params, max(top_k * 10, 20)),
            ).fetchall()
            is_fts = False
    finally:
        conn.close()

    scored_rows = sorted(
        (
            (
                _combined_score(
                    raw_score=float(row["score"]),
                    is_fts=is_fts,
                    row=row,
                    query=query,
                    tokens=tokens,
                ),
                row,
            )
            for row in rows
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    hits = [
        {
            "title": row["title"],
            "path": row["path"],
            "chunk_id": str(row["chunk_id"]),
            "score": round(score, 3),
            "source_type": row["source_type"],
            "source_priority": int(row["source_priority"] or 0),
            "source_domain": row["source_domain"],
            "snippet": _build_snippet(row["text"], query),
        }
        for score, row in scored_rows[:top_k]
    ]
    return {"success": True, "query": query, "hits": hits}
