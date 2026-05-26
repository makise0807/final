from __future__ import annotations

import json

from plugins.geo_expert.tools import workflow_eval_all_handler


def test_service_coverage_quality_notes_present() -> None:
    payload = json.loads(workflow_eval_all_handler({"mode": "safe_run"}))
    coverage = payload["service_coverage"]
    assert coverage["readiness_level"] in {"prototype", "real_service_partial", "real_service_operational"}
    assert "aoi_match_quality" in coverage["satellite"]
    assert "layer_coverage" in coverage["postgis"]
    assert coverage["chromadb"]["quality_note"]
    assert "embedding_backend" in coverage["chromadb"]
    assert coverage["detector"]["quality_note"]
