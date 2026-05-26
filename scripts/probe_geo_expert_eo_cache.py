from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from plugins.geo_expert.adapters.eo_tools import list_eo_cache_images


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Geo Expert EO cache probe.")
    parser.parse_args()
    print(json.dumps(list_eo_cache_images(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
