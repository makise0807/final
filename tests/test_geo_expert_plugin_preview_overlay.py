from __future__ import annotations

import json
from pathlib import Path

from plugins.geo_expert.tools import preview_satellite_overlay_handler


def test_geo_expert_preview_overlay(tmp_path: Path) -> None:
    raw = preview_satellite_overlay_handler(
        {
            "image_case_id": "sample_taichung_case",
            "require_satellite": False,
            "output_dir": str(tmp_path / "geo_expert_preview"),
        }
    )

    assert isinstance(raw, str)
    payload = json.loads(raw)
    assert payload["success"] is True
    assert Path(payload["overlay_path"]).exists()
    assert Path(payload["overlay_path"]).name == "overlay_preview.png"
