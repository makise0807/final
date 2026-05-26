from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from plugins.geo_expert.adapters.satellite_tools import acquire_satellite_preview


def _parse_bbox(raw: str | None) -> dict[str, float] | None:
    if not raw:
        return None
    parts = [part.strip() for part in str(raw).split(",")]
    if len(parts) != 4:
        return None
    try:
        west, south, east, north = [float(part) for part in parts]
    except Exception:
        return None
    if west >= east or south >= north:
        return None
    return {"west": west, "south": south, "east": east, "north": north}


def _parse_date_range(raw: str | None) -> list[str]:
    if not raw:
        return ["2025-01-01", "2025-12-31"]
    parts = [part.strip() for part in str(raw).split(",")]
    if len(parts) != 2 or not all(parts):
        return ["2025-01-01", "2025-12-31"]
    return [parts[0], parts[1]]


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe Geo Expert GEE preview path without triggering exports or GeoTIFF downloads.")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--bbox", default=None, help="west,south,east,north")
    parser.add_argument("--date-range", default=None, help="start,end")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    payload = {
        "allow_fetch": str(os.getenv("GEO_EXPERT_ALLOW_SATELLITE_FETCH", "0")),
        "gee_enabled": str(os.getenv("GEO_EXPERT_GEE_ENABLED", "0")),
        "gee_project": os.getenv("GEO_EXPERT_GEE_PROJECT"),
        "output_dir": args.output_dir or os.getenv("GEO_EXPERT_SATELLITE_OUTPUT_DIR"),
    }
    if payload["gee_project"] and not os.getenv("GEE_PROJECT"):
        os.environ["GEE_PROJECT"] = str(payload["gee_project"])
    aoi = _parse_bbox(args.bbox) or {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47}
    payload["probe"] = acquire_satellite_preview(
        aoi=aoi,
        mode="preview" if args.execute else "prepare_only",
        provider="gee",
        time_range=_parse_date_range(args.date_range),
        output_dir=payload["output_dir"],
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
