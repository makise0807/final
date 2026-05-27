from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def openeo_runtime_config() -> dict[str, Any]:
    return {
        "url": os.getenv("OPENEO_URL"),
        "user": os.getenv("OPENEO_USER"),
        "password_present": bool(os.getenv("OPENEO_PASSWORD")),
        "provider": os.getenv("GEO_EXPERT_OPENEO_PROVIDER") or os.getenv("OPENEO_URL"),
        "allow_submit": str(os.getenv("GEO_EXPERT_ALLOW_OPENEO_SUBMIT", "0")).strip().lower() in {"1", "true", "yes", "on"},
        "allow_download": str(os.getenv("GEO_EXPERT_ALLOW_GEOTIFF_DOWNLOAD", "0")).strip().lower() in {"1", "true", "yes", "on"},
        "cache_dir": str((Path("outputs") / "geo_expert" / "geotiff_cache").resolve()),
        "required_config": [
            "OPENEO_URL",
            "OPENEO_USER",
            "OPENEO_PASSWORD",
            "GEO_EXPERT_ALLOW_OPENEO_SUBMIT",
            "GEO_EXPERT_ALLOW_GEOTIFF_DOWNLOAD",
        ],
    }
