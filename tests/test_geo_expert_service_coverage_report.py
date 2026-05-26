from __future__ import annotations

import json

from plugins.geo_expert.tools import workflow_eval_all_handler


def test_geo_expert_service_coverage_report() -> None:
    payload = json.loads(workflow_eval_all_handler({"mode": "safe_run"}))
    coverage = payload["service_coverage"]
    assert "chromadb" in coverage
    assert "postgis" in coverage
    assert "eo_cache" in coverage
    assert "satellite" in coverage
    assert "detector" in coverage
    assert "selected_collections" in coverage["chromadb"]
    assert "aliases_missing" in coverage["postgis"]
    assert "image_count" in coverage["eo_cache"]
    assert "cache_image_count" in coverage["satellite"]
    assert "blockers" in coverage["satellite"]
    assert "next_actions" in coverage["satellite"]
    assert "backend" in coverage["detector"]
    assert "blockers" in coverage
    assert "next_actions" in coverage
    assert "overall_real_service_score" in coverage
