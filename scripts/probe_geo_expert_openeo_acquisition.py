from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from plugins.geo_expert.openeo_acquisition import run_openeo_acquisition


def _parse_bbox(raw: str) -> dict[str, float]:
    west, south, east, north = [float(item) for item in raw.split(",")]
    return {"west": west, "south": south, "east": east, "north": north}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("--bbox", default="120.7,23.45,120.72,23.47")
    args = parser.parse_args()
    mode = "approved_run" if args.execute else "prepare_only"
    result = run_openeo_acquisition(
        {
            "aoi": _parse_bbox(args.bbox),
            "date_range": {"start": "2025-01-01", "end": "2025-01-31"},
            "bands": ["B04", "B03", "B02", "B08"],
            "mode": mode,
            "approved": bool(args.approved),
        }
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
