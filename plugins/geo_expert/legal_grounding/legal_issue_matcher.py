from __future__ import annotations

from typing import Any


ISSUE_KEYWORDS = {
    "illegal_factory_agriculture": ["違章工廠", "農業區", "農地工廠", "WF-001", "real_estate_insight"],
    "non_urban_land_use_control": ["非都市土地", "使用管制", "農業區", "一般農業區"],
    "solar_on_farmland": ["農地種電", "光電", "太陽能", "WF-005"],
    "river_management_zone": ["河川", "行水區", "廢棄物", "WF-004"],
    "hillside_conservation": ["山坡地", "保育", "超限利用", "崩塌", "WF-002", "WF-009"],
    "urban_planning_redevelopment_tod": ["都市計畫", "都更", "TOD", "都市更新", "WF-003", "WF-006", "WF-008"],
    "ecology_sensitive_development": ["生態敏感區", "綠網", "國土綠網", "WF-010"],
}


def match_legal_issues(*, user_request: str = "", workflow_id: str = "", pack_id: str = "", facts: dict[str, Any] | None = None) -> dict[str, Any]:
    haystack = " ".join(
        [
            str(user_request or ""),
            str(workflow_id or ""),
            str(pack_id or ""),
            str(facts or ""),
        ]
    )
    issue_tags: list[str] = []
    matched_terms: dict[str, list[str]] = {}
    for issue, keywords in ISSUE_KEYWORDS.items():
        hits = [keyword for keyword in keywords if keyword and keyword in haystack]
        if hits:
            issue_tags.append(issue)
            matched_terms[issue] = hits
    if not issue_tags:
        issue_tags = ["general_land_use_review"]
        matched_terms["general_land_use_review"] = []
    return {
        "issue_tags": issue_tags,
        "matched_terms": matched_terms,
    }
