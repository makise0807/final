from __future__ import annotations

from typing import Any

from ..adapters.rag_tools import search_regulations
from .legal_citation_parser import parse_legal_citation
from .legal_issue_matcher import match_legal_issues


ISSUE_REQUIREMENTS = {
    "illegal_factory_agriculture": {
        "required_facts": ["land_use_zone", "current_use", "structure_presence", "parcel_location"],
        "possible_laws": ["區域計畫法", "非都市土地使用管制規則", "農業發展條例"],
    },
    "non_urban_land_use_control": {
        "required_facts": ["land_category", "approved_use", "current_use"],
        "possible_laws": ["區域計畫法", "非都市土地使用管制規則"],
    },
    "solar_on_farmland": {
        "required_facts": ["parcel_location", "facility_type", "approval_status", "current_land_use"],
        "possible_laws": ["農業發展條例", "非都市土地使用管制規則"],
    },
    "river_management_zone": {
        "required_facts": ["river_zone_overlap", "activity_type", "site_photos"],
        "possible_laws": ["水利法", "河川管理辦法"],
    },
    "hillside_conservation": {
        "required_facts": ["slope_location", "land_disturbance", "permit_status"],
        "possible_laws": ["山坡地保育利用條例", "水土保持法"],
    },
    "urban_planning_redevelopment_tod": {
        "required_facts": ["planning_area", "site_condition", "transport_context", "zoning_status"],
        "possible_laws": ["都市計畫法", "都市更新條例"],
    },
    "ecology_sensitive_development": {
        "required_facts": ["ecology_overlap", "development_type", "impact_scope"],
        "possible_laws": ["國土計畫法", "野生動物保育法", "環境影響評估法"],
    },
    "general_land_use_review": {
        "required_facts": ["site_location", "current_use"],
        "possible_laws": ["區域計畫法", "都市計畫法"],
    },
}


def _facts_available(required_facts: list[str], facts: dict[str, Any]) -> tuple[list[str], list[str]]:
    available = [item for item in required_facts if facts.get(item) not in (None, "", [], {})]
    missing = [item for item in required_facts if item not in available]
    return available, missing


def build_applicability_check(*, user_request: str, workflow_id: str = "", pack_id: str = "", facts: dict[str, Any] | None = None) -> dict[str, Any]:
    facts = dict(facts or {})
    match = match_legal_issues(user_request=user_request, workflow_id=workflow_id, pack_id=pack_id, facts=facts)
    issue_tags = list(match.get("issue_tags") or [])
    rag = search_regulations(user_request or workflow_id or pack_id, top_k=5)
    results = list(rag.get("results") or [])

    checklists: list[dict[str, Any]] = []
    for issue in issue_tags:
        requirements = ISSUE_REQUIREMENTS.get(issue, ISSUE_REQUIREMENTS["general_land_use_review"])
        required_facts = list(requirements["required_facts"])
        available, missing = _facts_available(required_facts, facts)
        citation_hits = []
        parsed_hits = []
        for item in results:
            parsed = parse_legal_citation(str(item.get("content") or ""), item.get("metadata") or {})
            if parsed.get("law_name") or parsed.get("article_no") or parsed.get("key_terms"):
                parsed_hits.append(parsed)
                citation_hits.append(
                    {
                        "title": item.get("title"),
                        "citation": parsed.get("citation_key") or item.get("citation"),
                        "law_name": parsed.get("law_name"),
                        "article_no": parsed.get("article_no"),
                        "penalty_text": parsed.get("penalty_text"),
                        "actions": parsed.get("actions") or [],
                    }
                )
        if citation_hits and not missing:
            applicability = "likely_relevant"
            confidence = 0.78
        elif citation_hits:
            applicability = "needs_more_facts"
            confidence = 0.56
        else:
            applicability = "not_enough_evidence"
            confidence = 0.28
        checklists.append(
            {
                "issue": issue,
                "possible_laws": list(requirements["possible_laws"]),
                "required_facts": required_facts,
                "facts_available": available,
                "facts_missing": missing,
                "citation_hits": citation_hits,
                "parsed_citations": parsed_hits,
                "applicability": applicability,
                "confidence": confidence,
                "human_review_required": True,
            }
        )

    return {
        "success": True,
        "user_request": user_request,
        "workflow_id": workflow_id,
        "pack_id": pack_id,
        "issue_tags": issue_tags,
        "citations": [hit for item in checklists for hit in item.get("citation_hits") or []],
        "applicability_checklist": checklists,
        "human_review_required": True,
        "rag_status": rag.get("status"),
        "rag_used_real_service": bool(rag.get("used_real_service")),
        "warnings": list(rag.get("warnings") or []),
        "limitations": [
            "This is a grounded legal relevance screen, not a formal legal opinion.",
            "Human legal and field review remain required.",
        ],
    }
