from __future__ import annotations

from typing import Any


def build_legal_report_sections(grounding: dict[str, Any]) -> dict[str, Any]:
    checklist = list(grounding.get("applicability_checklist") or [])
    citations = list(grounding.get("citations") or [])
    facts_missing = sorted({fact for item in checklist for fact in item.get("facts_missing") or []})
    facts_available = sorted({fact for item in checklist for fact in item.get("facts_available") or []})
    return {
        "Legal Basis": citations,
        "Applicability Checklist": checklist,
        "Evidence Sufficiency": {
            "facts_available": facts_available,
            "facts_missing": facts_missing,
            "human_review_required": True,
        },
        "Human Review Required": True,
        "Formality Level": [
            "preliminary_screening",
            "expert_review_draft",
            "not_official_decision",
        ],
        "Disclaimer": "本段為法規依據與適用要件檢核草稿，僅供專家複核，不構成正式法律意見。",
    }
