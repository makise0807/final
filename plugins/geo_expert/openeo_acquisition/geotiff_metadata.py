from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_geotiff_metadata(
    *,
    artifact_id: str,
    path: str,
    aoi: dict[str, Any] | None,
    date_range: dict[str, Any] | None,
    bands: list[str] | None,
    provider: str | None,
    crs: str | None = None,
    resolution: int = 10,
) -> dict[str, Any]:
    file_path = Path(path)
    digest = None
    if file_path.exists() and file_path.is_file():
        sha = hashlib.sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                sha.update(chunk)
        digest = sha.hexdigest()
    return {
        "artifact_id": artifact_id,
        "path": str(file_path),
        "sha256": digest,
        "aoi": aoi,
        "date_range": date_range or {},
        "bands": list(bands or []),
        "provider": provider,
        "crs": crs,
        "resolution": int(resolution),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "openeo",
        "is_formal_analysis": False,
        "requires_verification": True,
    }
