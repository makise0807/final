from __future__ import annotations

from plugins.geo_expert.production import calculate_readiness_score


def test_readiness_score_does_not_claim_complete() -> None:
    coverage = {
        "postgis": {"aliases_missing": 9},
        "detector": {"quality_note": ["yolo11n_general_model"]},
        "chromadb": {"quality_note": ["production_embedding_recommended"]},
        "satellite": {"fallback_latest_matches": 2},
        "production_readiness": {"approval_gates_open": False},
    }
    result = calculate_readiness_score(coverage)
    assert result["readiness_level"] in {"production_ready_blocked", "mvp", "production_ready_partial"}
    assert result["score"] < 1.0
    assert result["blocking_gaps"]
