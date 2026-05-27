from __future__ import annotations

from typing import Any


def build_pack_report(pack: dict[str, Any], user_request: str, inputs: dict[str, Any], satellite_evidence: dict[str, Any], user_rag: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": pack.get("title"),
        "title_zh": pack.get("title_zh"),
        "sections": {
            "Purpose": pack.get("title_zh") or pack.get("title"),
            "Target user": ", ".join(str(item) for item in (pack.get("target_users") or [])),
            "Input summary": inputs,
            "Satellite evidence": satellite_evidence,
            "User data evidence": user_rag,
            "Domain observations": analysis.get("domain_observations"),
            "Risks / opportunities": analysis.get("risks_opportunities"),
            "Limitations": analysis.get("limitations"),
            "Next actions": analysis.get("next_actions"),
        },
        "report_sections": list(pack.get("report_sections") or []),
        "user_request": user_request,
    }
