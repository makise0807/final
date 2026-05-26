from __future__ import annotations

from plugins.geo_expert.adapters.detector_tools import _to_detection_payload, run_detection


def test_detector_defaults_to_mock_without_env(monkeypatch) -> None:
    monkeypatch.delenv("GEO_EXPERT_DETECTOR_BACKEND", raising=False)
    monkeypatch.delenv("GEO_EXPERT_DETECTOR_MODEL_PATH", raising=False)
    payload = run_detection(
        {
            "task": "preliminary_image_recognition",
            "sop_id": "WF-001",
            "aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47},
        }
    )
    assert payload["success"] is True
    assert payload["detector_used"] == "mock"
    assert payload["used_real_model"] is False


def test_detector_yolo_path_missing_degrades_then_falls_back(monkeypatch) -> None:
    monkeypatch.setenv("GEO_EXPERT_DETECTOR_BACKEND", "yolo")
    monkeypatch.setenv("GEO_EXPERT_DETECTOR_MODEL_PATH", "C:/missing/yolo11n.pt")
    payload = run_detection(
        {
            "task": "preliminary_image_recognition",
            "sop_id": "WF-001",
            "aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47},
        }
    )
    assert payload["success"] is True
    assert payload["used_real_model"] is False
    assert payload["detector_used"] == "mock"
    assert payload["degraded_reason"] == "model_path_missing"


def test_detection_payload_exposes_yolo_limitations() -> None:
    payload = _to_detection_payload(
        {"image_source": "local_image", "target_classes": ["building"]},
        {
            "features": [
                {
                    "feature_id": "det-001",
                    "geometry": {"type": "Polygon", "coordinates": [[[120.7, 23.45], [120.71, 23.45], [120.71, 23.46], [120.7, 23.46], [120.7, 23.45]]]},
                    "bbox": [120.7, 23.45, 120.71, 23.46],
                    "pixel_bbox": [10, 20, 30, 40],
                    "raw_class_id": 0,
                    "raw_class_name": "person",
                    "mapped_class_label": "unknown_object",
                    "confidence": 0.88,
                    "evidence": ["generic_object_detection"],
                }
            ]
        },
        detector_name="yolo",
        model_basename="yolo11n.pt",
    )
    assert payload["used_real_model"] is True
    detection = payload["detections"][0]
    assert detection["raw_class_id"] == 0
    assert detection["raw_class_name"] == "person"
    assert detection["pixel_bbox"] == [10, 20, 30, 40]
    assert detection["model_scope"] == "general_object_detector"
    assert any("pixel-space" in item for item in payload["warnings"])
