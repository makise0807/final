from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from plugins.geo_expert.adapters.satellite_tools import build_eo_cache_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a read-only EO cache metadata index for Geo Expert.")
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    payload = build_eo_cache_index(cache_dir=args.cache_dir, output_path=args.output, write_output=not args.no_write)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
