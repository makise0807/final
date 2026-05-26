from __future__ import annotations

import json
import math
from typing import Any

from .config import WORKFLOW_DB_PATH, dependency_error


def load_workflows() -> dict[str, Any]:
    if not WORKFLOW_DB_PATH.exists():
        return dependency_error(
            "workflow_db",
            f"Workflow database file not found: {WORKFLOW_DB_PATH}",
            required_config=[],
            error="data_unavailable",
        )
    try:
        payload = json.loads(WORKFLOW_DB_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return dependency_error(
            "workflow_db",
            f"Workflow database could not be read: {exc}",
            required_config=[],
            error="data_unavailable",
        )
    if not isinstance(payload, list):
        return dependency_error(
            "workflow_db",
            "Workflow database payload is not a list.",
            required_config=[],
            error="data_unavailable",
        )
    return {
        "success": True,
        "workflows": payload,
        "count": len(payload),
        "path": str(WORKFLOW_DB_PATH),
    }


def list_workflows() -> dict[str, Any]:
    loaded = load_workflows()
    if not loaded.get("success"):
        return loaded
    workflows = loaded["workflows"]
    items = [
        {
            "workflow_id": item.get("scenario_id") or item.get("workflow_id") or item.get("id"),
            "title": item.get("scenario_name") or item.get("title"),
            "category": item.get("category"),
            "domain": item.get("domain"),
            "keywords": item.get("keywords") or [],
            "steps": item.get("steps") or [],
            "safety": item.get("safety") or {},
        }
        for item in workflows
        if isinstance(item, dict)
    ]
    return {
        "success": True,
        "workflows": items,
        "count": len(items),
    }


def show_workflow(workflow_id: str) -> dict[str, Any]:
    loaded = load_workflows()
    if not loaded.get("success"):
        return loaded
    target = str(workflow_id or "").strip()
    for item in loaded["workflows"]:
        if not isinstance(item, dict):
            continue
        current_id = str(item.get("scenario_id") or item.get("workflow_id") or item.get("id") or "").strip()
        if current_id == target:
            return {
                "success": True,
                "workflow": item,
                "workflow_id": current_id,
                "title": item.get("scenario_name") or item.get("title"),
            }
    return {
        "success": False,
        "error": "workflow_not_found",
        "message": f"Workflow '{target}' was not found.",
        "workflow_id": target,
    }


def search_workflows(query: str, limit: int = 5) -> dict[str, Any]:
    loaded = load_workflows()
    if not loaded.get("success"):
        return loaded
    lowered = str(query or "").strip().lower()
    terms = [term for term in lowered.replace("（", " ").replace("）", " ").replace("、", " ").replace("，", " ").split() if term]
    scored: list[tuple[float, dict[str, Any], list[str], str]] = []
    for item in loaded["workflows"]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("scenario_name") or "")
        domain = str(item.get("domain") or "")
        category = str(item.get("category") or "")
        keywords = [str(x) for x in (item.get("keywords") or [])]
        triggers = [str(x) for x in (item.get("triggers") or [])]
        score = 0.0
        matched_terms: list[str] = []
        reason_parts: list[str] = []
        haystacks = {
            "title": title.lower(),
            "domain": domain.lower(),
            "category": category.lower(),
            "keywords": " ".join(keywords).lower(),
            "triggers": " ".join(triggers).lower(),
        }
        if lowered and lowered in haystacks["title"]:
            score += 8.0
            matched_terms.append(lowered)
            reason_parts.append("title_match")
        if lowered and lowered in haystacks["triggers"]:
            score += 6.0
            matched_terms.append(lowered)
            reason_parts.append("trigger_match")
        if lowered and lowered in haystacks["keywords"]:
            score += 5.0
            matched_terms.append(lowered)
            reason_parts.append("keyword_match")
        if lowered and lowered in haystacks["category"]:
            score += 4.0
            matched_terms.append(lowered)
            reason_parts.append("category_match")
        if lowered and lowered in haystacks["domain"]:
            score += 3.0
            matched_terms.append(lowered)
            reason_parts.append("domain_match")
        for phrase in keywords + triggers + [title, category, domain]:
            phrase_lower = str(phrase).lower()
            if phrase_lower and phrase_lower in lowered:
                score += 3.2
                matched_terms.append(phrase)
                reason_parts.append("query_contains_phrase")
            elif lowered and lowered in phrase_lower:
                score += 2.4
                matched_terms.append(phrase)
                reason_parts.append("phrase_contains_query")
        for term in terms:
            for bucket, weight in (("triggers", 2.2), ("keywords", 1.8), ("title", 2.6), ("category", 1.4), ("domain", 1.0)):
                if term and term in haystacks[bucket]:
                    score += weight
                    matched_terms.append(term)
        if not terms:
            for bucket_text in (haystacks["triggers"], haystacks["keywords"], haystacks["title"]):
                for fragment in [lowered[i:j] for i in range(len(lowered)) for j in range(i + 2, min(len(lowered), i + 6) + 1)]:
                    if fragment in bucket_text:
                        score += 0.4
                        matched_terms.append(fragment)
        if score <= 0:
            continue
        normalized_score = min(0.99, round(1 - math.exp(-score / 10.0), 4))
        scored.append((normalized_score, item, sorted(set(matched_terms)), ",".join(sorted(set(reason_parts)))))
    scored.sort(key=lambda pair: (-pair[0], str(pair[1].get("workflow_id") or "")))
    results = [
        {
            "workflow_id": item.get("workflow_id") or item.get("scenario_id") or item.get("id"),
            "title": item.get("title") or item.get("scenario_name"),
            "domain": item.get("domain"),
            "category": item.get("category"),
            "score": score,
            "matched_terms": matched_terms,
            "reason": reason or "weighted_match",
        }
        for score, item, matched_terms, reason in scored[: max(int(limit), 1)]
    ]
    return {"success": True, "query": query, "results": results, "count": len(results)}


def route_workflow(query: str, limit: int = 5, confidence_threshold: float = 0.45) -> dict[str, Any]:
    found = search_workflows(query, limit=limit)
    if not found.get("success"):
        return found
    results = found.get("results") or []
    if not results:
        return {
            "success": True,
            "query": query,
            "needs_clarification": True,
            "candidates": [],
            "message": "No workflow candidates matched the query.",
        }
    top = results[0]
    matched_terms = top.get("matched_terms") or []
    needs_clarification = float(top.get("score") or 0.0) < float(confidence_threshold) and len(matched_terms) < 2
    return {
        "success": True,
        "query": query,
        "selected_workflow_id": None if needs_clarification else top.get("workflow_id"),
        "selected_workflow_title": None if needs_clarification else top.get("title"),
        "confidence": float(top.get("score") or 0.0),
        "needs_clarification": needs_clarification,
        "candidates": results,
        "reason": top.get("reason"),
    }


def get_execution_spec(workflow_id: str) -> dict[str, Any]:
    return show_workflow(workflow_id)
