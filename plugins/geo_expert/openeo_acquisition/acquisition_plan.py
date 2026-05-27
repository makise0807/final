from __future__ import annotations

from typing import Any

from ..production.approval_gate import approval_gate_for_action
from .openeo_config import openeo_runtime_config


def create_openeo_acquisition_plan(
    aoi: dict[str, Any] | None,
    date_range: dict[str, Any] | None,
    bands: list[str] | None,
    resolution: int,
    output_format: str = "GeoTIFF",
) -> dict[str, Any]:
    cfg = openeo_runtime_config()
    approval = approval_gate_for_action(
        "openeo_submit",
        estimated_outputs=[f"{output_format} preview metadata", f"{output_format} raster at {resolution}m"],
    )
    return {
        "success": True,
        "mode": "prepare_only",
        "provider": cfg.get("provider"),
        "aoi": aoi,
        "date_range": date_range or {},
        "bands": list(bands or ["B04", "B03", "B02", "B08"]),
        "resolution": int(resolution or 10),
        "output_format": output_format,
        "estimated_artifacts": [
            {"type": "geotiff", "description": "Potential raster output after approved run."},
            {"type": "sidecar_metadata", "description": "GeoTIFF sidecar metadata file."},
        ],
        "approval_required": True,
        "submit_allowed": False,
        "download_allowed": False,
        "approval_gate": approval,
        "next_action": "Set approval env and run approved_run if you want to submit.",
    }
