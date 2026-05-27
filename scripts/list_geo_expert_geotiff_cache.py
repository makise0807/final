from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from plugins.geo_expert.openeo_acquisition import list_geotiff_cache


def main() -> int:
    print(json.dumps(list_geotiff_cache(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
