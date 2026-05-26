from __future__ import annotations

import json

from plugins.geo_expert.tools import eo_local_analysis_handler


def test_geo_expert_eo_local_analysis_bbox_and_missing_image() -> None:
    raw_bbox = eo_local_analysis_handler(
        {
            "operation": "bbox",
            "parameters": {"lon": 120.54, "lat": 23.99, "size_meters": 500},
        }
    )
    bbox_payload = json.loads(raw_bbox)
    assert bbox_payload["success"] is True
    assert "bbox" in bbox_payload

    raw_missing = eo_local_analysis_handler(
        {
            "operation": "vari",
            "parameters": {"image_path": "C:/definitely/missing/image.tif"},
        }
    )
    missing_payload = json.loads(raw_missing)
    assert missing_payload["success"] is False
    assert missing_payload["error"] == "local_input_missing"
