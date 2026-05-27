from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_LOG_DIR = Path("outputs") / "geo_expert" / "audit_log"


def append_audit_log(entry: dict[str, Any]) -> dict[str, Any]:
    AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = str(entry.get("run_id") or "unknown")
    path = AUDIT_LOG_DIR / f"{timestamp}_{run_id}.json"
    payload = dict(entry)
    payload.setdefault("timestamp", timestamp)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "path": str(path), "tracked_by_git": False}
