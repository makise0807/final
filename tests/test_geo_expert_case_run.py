from __future__ import annotations

import json
from pathlib import Path

from plugins.geo_expert.tools import case_run_handler


def test_geo_expert_case_run() -> None:
    payload = json.loads(
        case_run_handler(
            {
                "user_request": "我要找台中的違章建築",
                "mode": "safe_run",
                "inputs": {"image_case_id": "sample_taichung_case", "require_satellite": False, "use_llm": False},
            }
        )
    )
    assert payload["success"] is True
    assert payload["workflow_id"] == "WF-001"
    assert Path(payload["report_path"]).exists()
    assert Path(payload["result_json_path"]).exists()
    assert "recommended_next_actions" in payload
