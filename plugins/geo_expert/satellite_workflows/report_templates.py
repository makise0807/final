from __future__ import annotations

from typing import Any


def _user_data_summary(user_rag: dict[str, Any]) -> dict[str, Any]:
    if user_rag.get("status") == "ok":
        return {
            "status": "ok",
            "collection": user_rag.get("collection"),
            "dataset_ids": user_rag.get("dataset_ids") or [],
            "citations": user_rag.get("citations") or [],
            "summary": f"Retrieved {len(user_rag.get('hits') or [])} user-data evidence hits.",
        }
    return {
        "status": user_rag.get("status") or "no_user_data_available",
        "collection": user_rag.get("collection"),
        "dataset_ids": user_rag.get("dataset_ids") or [],
        "citations": [],
        "summary": "目前未提供使用者資料，因此本段僅使用衛星/系統資料。",
    }


def build_pack_report(
    pack: dict[str, Any],
    user_request: str,
    inputs: dict[str, Any],
    satellite_evidence: dict[str, Any],
    user_rag: dict[str, Any],
    analysis: dict[str, Any],
) -> dict[str, Any]:
    sections = [
        {"heading": "Purpose / 用途", "content": pack.get("title_zh") or pack.get("title")},
        {"heading": "Input Summary / 輸入摘要", "content": {"user_request": user_request, "inputs": inputs}},
        {"heading": "Satellite Evidence / 衛星影像證據", "content": satellite_evidence},
        {"heading": "User Data Evidence / 使用者資料佐證", "content": _user_data_summary(user_rag)},
        {"heading": "Domain Observations / 領域觀察", "content": analysis.get("observations") or []},
        {"heading": "Risks or Caveats / 風險與限制", "content": analysis.get("risks") or []},
        {"heading": "Next Actions / 下一步", "content": analysis.get("next_actions") or []},
    ]
    return {
        "title": pack.get("title"),
        "title_zh": pack.get("title_zh"),
        "pack_id": pack.get("pack_id"),
        "sections": sections,
        "report_sections": list(pack.get("report_sections") or []),
        "sections_map": {section["heading"]: section["content"] for section in sections},
        "user_request": user_request,
    }
