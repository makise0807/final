from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _entry(path: Path, source: str, ttl_days: int | None) -> dict[str, Any]:
    stat = path.stat() if path.exists() else None
    created = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat() if stat else None
    return {
        "path": str(path),
        "size": int(stat.st_size) if stat else 0,
        "created_at": created,
        "source": source,
        "ttl_days": ttl_days,
        "safe_to_delete": True,
        "tracked_by_git": False,
    }


def list_cache_policy_entries() -> dict[str, Any]:
    roots = [
        (Path("outputs") / "geo_expert" / "eo_cache_index.json", "eo_preview_cache", 30),
        (Path("outputs") / "geo_expert" / "geotiff_cache", "geotiff_cache", None),
        (Path("outputs") / "geo_expert" / "user_data", "rag_user_data_cache", None),
        (Path("outputs") / "geo_expert" / "workflows", "report_output_cache", 14),
        (Path("outputs") / "geo_expert" / "audit_log", "audit_log_cache", 30),
    ]
    entries: list[dict[str, Any]] = []
    for path, source, ttl in roots:
        if path.is_dir():
            for child in sorted(path.iterdir()):
                entries.append(_entry(child, source, ttl))
        else:
            entries.append(_entry(path, source, ttl))
    return {"success": True, "entries": entries}
