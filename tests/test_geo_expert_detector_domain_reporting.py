from __future__ import annotations

from pathlib import Path

from PIL import Image

from plugins.geo_expert.adapters.detector_tools import run_detection


def test_detector_domain_reporting_uses_general_model_language(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (32, 32), color=(255, 255, 255)).save(image_path)
    result = run_detection(
        {
            "task": "run_preliminary_case_check",
            "sop_id": "WF-001",
            "local_image_path": str(image_path),
            "aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47},
            "image_source": "local_image",
        }
    )
    assert result["success"] is True
    assert result.get("model_scope") in {None, "general_object_detector"} or result.get("detections") is not None
    if result.get("detections"):
        detection = result["detections"][0]
        assert detection["model_scope"] == "general_object_detector"
        assert detection["domain_specific"] is False
        assert detection["interpretation_allowed"] is False
