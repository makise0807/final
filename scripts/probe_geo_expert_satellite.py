from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from plugins.geo_expert.adapters.satellite_tools import acquire_satellite_preview, satellite_status


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Geo Expert satellite acquisition probe.")
    parser.add_argument("--mode", default="cache_only", choices=["prepare_only", "cache_only", "preview"])
    parser.add_argument("--workflow-id", default="")
    parser.add_argument("--case-id", default="")
    parser.add_argument("--west", type=float, default=120.7)
    parser.add_argument("--south", type=float, default=23.45)
    parser.add_argument("--east", type=float, default=120.72)
    parser.add_argument("--north", type=float, default=23.47)
    args = parser.parse_args()
    aoi = {"west": args.west, "south": args.south, "east": args.east, "north": args.north}
    payload = {
        "status": satellite_status(),
        "probe": acquire_satellite_preview(
            aoi=aoi,
            case_id=args.case_id or None,
            workflow_id=args.workflow_id or None,
            mode=args.mode,
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
