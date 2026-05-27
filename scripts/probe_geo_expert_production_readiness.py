from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from plugins.geo_expert.production import calculate_readiness_score, check_service_health


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    health = check_service_health()
    readiness = calculate_readiness_score()
    print(json.dumps({"success": True, "service_health": health, "production_readiness": readiness}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
