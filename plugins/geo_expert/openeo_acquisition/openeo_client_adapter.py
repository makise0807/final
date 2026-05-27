from __future__ import annotations

from typing import Any

from .openeo_config import openeo_runtime_config


def submit_openeo_job(request: dict[str, Any]) -> dict[str, Any]:
    cfg = openeo_runtime_config()
    if not cfg.get("provider"):
        return {"success": False, "status": "degraded", "error": "openeo_provider_not_configured"}
    if not cfg.get("allow_submit"):
        return {"success": False, "status": "approval_required", "error": "openeo_submit_disabled"}
    if not cfg.get("url") or not cfg.get("user") or not cfg.get("password_present"):
        return {"success": False, "status": "degraded", "error": "openeo_auth_required"}
    try:
        import openeo  # type: ignore
    except Exception:
        return {"success": False, "status": "degraded", "error": "openeo_dependency_missing"}
    return {
        "success": False,
        "status": "degraded",
        "error": "openeo_real_submit_not_executed_in_tests",
        "message": "Runtime adapter is wired, but tests and default path do not execute real OpenEO jobs.",
        "request": request,
        "dependency_loaded": bool(openeo),
    }
