from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from plugins.geo_expert.adapters.detector_tools import detector_status, run_detection
from plugins.geo_expert.adapters.eo_tools import select_eo_cache_image


def probe_detector(sample_image: str | None = None) -> dict[str, Any]:
    status = detector_status()
    if not sample_image:
        selected = select_eo_cache_image()
        if selected.get("success"):
            sample_image = str((selected.get("selected_image") or {}).get("image_path") or "")
    payload: dict[str, Any] = {"status": status}
    if not sample_image:
        payload["success"] = True
        payload["message"] = "Detector config checked. No sample image provided."
        return payload
    result = run_detection(
        {
            "task": "preliminary_image_recognition",
            "sop_id": "WF-001",
            "image_source": "local_image",
            "local_image_path": sample_image,
            "aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47},
        }
    )
    payload["success"] = True
    payload["sample_image"] = sample_image
    payload["result"] = {
        "success": result.get("success"),
        "detector_used": result.get("detector_used"),
        "used_real_model": result.get("used_real_model", False),
        "warning_count": len(result.get("warnings") or []),
        "detection_count": len(result.get("detections") or []),
        "error": result.get("error"),
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Geo Expert detector probe.")
    parser.add_argument("--image", type=str, default=None, help="Optional sample image path.")
    args = parser.parse_args()
    print(json.dumps(probe_detector(args.image), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
