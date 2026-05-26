"""Validation helpers for preview-only OpenEO backend contracts."""

from __future__ import annotations

from typing import Any

from .openeo_contracts import OpenEOBackendConfig


REAL_EXECUTION_ERROR = "real_backend_execution_not_supported"


def build_backend_config(raw: dict[str, Any] | None = None) -> OpenEOBackendConfig:
    raw = dict(raw or {})
    return OpenEOBackendConfig(
        backend_url=raw.get("backend_url"),
        auth_mode=raw.get("auth_mode", "none"),
        workspace=raw.get("workspace"),
        dry_run=bool(raw.get("dry_run", True)),
        verify_ssl=raw.get("verify_ssl"),
    )


def reject_real_backend_execution(config: OpenEOBackendConfig) -> dict[str, Any] | None:
    if config.dry_run:
        return None
    return {
        "success": False,
        "error": REAL_EXECUTION_ERROR,
        "requires_approval": True,
        "message": (
            "This version only supports preview/mock execution. Real OpenEO backend "
            "execution requires a separate approval-enabled adapter."
        ),
    }


def collect_missing_preview_inputs(workflow_plan: dict[str, Any], provided_inputs: dict[str, Any] | None = None) -> list[str]:
    provided = dict(provided_inputs or {})
    missing: set[str] = set()
    if not provided.get("aoi"):
        missing.add("aoi")
    if not provided.get("time_range"):
        missing.add("time_range")

    needs_landuse = any(
        step.get("tool") == "geo.gis.overlay_landuse"
        for step in (workflow_plan or {}).get("steps", [])
    )
    if needs_landuse and not provided.get("landuse_layer"):
        missing.add("landuse_layer")

    if not provided.get("collection_id"):
        select_collection_present = any(
            step.get("tool") == "geo.openeo.select_collection"
            for step in (workflow_plan or {}).get("steps", [])
        )
        if select_collection_present:
            missing.add("collection_id")
    return sorted(missing)
