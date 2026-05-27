from __future__ import annotations

import uuid
from typing import Any

from ..production.approval_gate import approval_gate_for_action
from .acquisition_plan import create_openeo_acquisition_plan
from .geotiff_cache import find_geotiff_cache
from .openeo_client_adapter import submit_openeo_job
from .openeo_config import openeo_runtime_config


def run_openeo_acquisition(request: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(request or {})
    aoi = payload.get("aoi")
    date_range = payload.get("date_range") or {}
    bands = list(payload.get("bands") or ["B04", "B03", "B02", "B08"])
    resolution = int(payload.get("resolution") or 10)
    mode = str(payload.get("mode") or "prepare_only")
    approved = bool(payload.get("approved"))
    cfg = openeo_runtime_config()

    if mode == "prepare_only":
        return create_openeo_acquisition_plan(aoi, date_range, bands, resolution, output_format=str(payload.get("output_format") or "GeoTIFF"))
    if mode == "cache_only":
        cached = find_geotiff_cache(aoi, date_range, bands)
        cached.update({"mode": "cache_only"})
        return cached
    if mode != "approved_run":
        return {"success": False, "status": "degraded", "error": "unsupported_mode"}

    approval_submit = approval_gate_for_action("openeo_submit", estimated_outputs=["GeoTIFF raster"], approved=approved)
    approval_download = approval_gate_for_action("geotiff_download", estimated_outputs=["GeoTIFF raster"], approved=approved)
    if not (cfg.get("allow_submit") and cfg.get("allow_download") and approved):
        return {
            "success": False,
            "status": "approval_required",
            "mode": "approved_run",
            "approval_required": True,
            "approval_gate": [approval_submit, approval_download],
            "submit_allowed": bool(cfg.get("allow_submit")),
            "download_allowed": bool(cfg.get("allow_download")),
            "next_action": "Set approval env, pass approved=true, and rerun approved_run if you want external submission.",
        }

    submit_result = submit_openeo_job(payload)
    return {
        "success": bool(submit_result.get("success")),
        "status": submit_result.get("status") or "degraded",
        "mode": "approved_run",
        "submitted": bool(submit_result.get("success")),
        "provider": cfg.get("provider"),
        "approval_gate": [approval_submit, approval_download],
        "artifacts": [],
        "run_reference": uuid.uuid4().hex[:12],
        **submit_result,
    }
