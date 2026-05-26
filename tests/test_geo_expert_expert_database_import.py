from __future__ import annotations

import json
from pathlib import Path


def test_geo_expert_expert_database_import() -> None:
    path = Path(__file__).resolve().parents[1] / "plugins" / "geo_expert" / "data" / "workflow_db" / "expert_workflows.json"
    assert path.exists()

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert len(payload) >= 1

    for workflow in payload:
        assert "workflow_id" in workflow
        assert "title" in workflow
        assert "safety" in workflow

    wf_001 = next((item for item in payload if item.get("workflow_id") == "WF-001"), None)
    assert wf_001 is not None
    assert wf_001["title"] == "農業區違章工廠盤查"
