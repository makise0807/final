from __future__ import annotations

import json
from pathlib import Path

from plugins.geo_expert.tools import run_preliminary_case_check_handler


def test_geo_expert_direct_handler(tmp_path: Path) -> None:
    raw = run_preliminary_case_check_handler(
        {
            "user_request": "我要找台中的違章建築",
            "image_case_id": "sample_taichung_case",
            "require_satellite": False,
            "use_llm": False,
            "output_dir": str(tmp_path / "geo_expert_test"),
        }
    )

    assert isinstance(raw, str)
    payload = json.loads(raw)
    assert payload["success"] is True
    assert payload["selected_sop"] == "WF-001"
    assert payload["selected_sop_title"] == "農業區違章工廠盤查"
    assert Path(payload["report_path"]).exists()
    assert Path(payload["geojson_path"]).exists()
    assert Path(payload["overlay_path"]).exists()
    assert payload["image_background"]["source"] == "local_fixture"
    assert payload["aoi_consistent"] is True
    assert any("formal legal conclusion" in item.lower() for item in payload["limitations"])
