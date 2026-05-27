from __future__ import annotations

from typing import Any


def approval_gate_for_action(
    action: str,
    *,
    estimated_outputs: list[str] | None = None,
    approved: bool = False,
) -> dict[str, Any]:
    risk_map = {
        "openeo_submit": "external_job_and_large_download",
        "geotiff_download": "external_job_and_large_download",
        "large_raster_export": "large_output_generation",
        "destructive_postgis_import": "database_mutation",
        "paid_api_call": "external_paid_api_call",
    }
    approval_required = action in risk_map
    return {
        "success": True,
        "approval_required": approval_required,
        "action": action,
        "risk": risk_map.get(action, "low_risk"),
        "estimated_outputs": list(estimated_outputs or []),
        "requires_user_confirmation": approval_required,
        "approved": bool(approved),
        "status": "approved" if approval_required and approved else ("approval_required" if approval_required else "not_required"),
    }
