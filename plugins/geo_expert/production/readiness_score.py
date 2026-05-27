from __future__ import annotations

from typing import Any


def calculate_readiness_score(service_coverage: dict[str, Any] | None = None) -> dict[str, Any]:
    coverage = dict(service_coverage or {})
    blocking_gaps: list[str] = []
    non_blocking_gaps: list[str] = []
    required_for_production: list[str] = [
        "domain-specific detector or verified interpretation workflow",
        "semantic legal/RAG embedding backend",
        "full required spatial layer coverage",
        "approval-gated external acquisition pipeline",
        "reproducibility manifest and audit logging",
    ]
    score = 0.72
    if coverage.get("postgis", {}).get("aliases_missing", 0):
        blocking_gaps.append("Missing required PostGIS layers for full domain analysis.")
        score -= 0.15
    if "yolo11n_general_model" in (coverage.get("detector", {}).get("quality_note") or []):
        non_blocking_gaps.append("Detector remains a general YOLO model, not a domain-specific enforcement detector.")
        score -= 0.08
    if "production_embedding_recommended" in (coverage.get("chromadb", {}).get("quality_note") or []):
        non_blocking_gaps.append("RAG still uses deterministic hash embedding unless explicitly upgraded.")
        score -= 0.07
    if coverage.get("satellite", {}).get("fallback_latest_matches", 0):
        non_blocking_gaps.append("Satellite matching still falls back to latest_without_metadata for some runs.")
        score -= 0.05
    if coverage.get("production_readiness", {}).get("approval_gates_open") is False:
        score += 0.03
    score = max(0.0, min(1.0, round(score, 2)))
    readiness_level = "prototype"
    if blocking_gaps:
        readiness_level = "production_ready_blocked"
    elif score >= 0.75:
        readiness_level = "production_ready_partial"
    elif score >= 0.5:
        readiness_level = "mvp"
    return {
        "readiness_level": readiness_level,
        "score": score,
        "blocking_gaps": blocking_gaps,
        "non_blocking_gaps": non_blocking_gaps,
        "required_for_production": required_for_production,
    }
