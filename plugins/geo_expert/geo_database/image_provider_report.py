"""Report helpers for temporary image-provider preview responses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


_BASE_LIMITATIONS = [
    "temporary preview only",
    "not a formal analysis result",
    "no GeoTIFF/export/download performed",
    "OpenEO workflow remains the primary target",
]

_DEFAULT_NEXT_STEPS = [
    "Return to OpenEO workflow validation when credentials or backend access are available.",
    "Use GEE only for temporary preview and small AOI demonstration.",
    "If OpenEO is still unavailable, keep the result clearly labeled as preview-only.",
]


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            result = value.to_dict()
            if isinstance(result, dict):
                return dict(result)
        except Exception:
            pass
    try:
        result = asdict(value)
        if isinstance(result, dict):
            return dict(result)
    except Exception:
        pass
    return {}


def _normalize_list(*values: Any) -> list[str]:
    merged: list[str] = []
    for value in values:
        if not value:
            continue
        if isinstance(value, (list, tuple, set)):
            items = value
        else:
            items = [value]
        for item in items:
            text = str(item).strip()
            if text and text not in merged:
                merged.append(text)
    return merged


def _request_summary(provider_response: dict[str, Any], original_request: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    aoi = original_request.get("aoi") or metadata.get("aoi") or {}
    return {
        "collection": original_request.get("collection")
        or original_request.get("collection_hint")
        or metadata.get("collection")
        or provider_response.get("collection")
        or "",
        "aoi": aoi,
        "aoi_area_km2": metadata.get("aoi_area_km2"),
        "time_range": original_request.get("time_range") or metadata.get("time_range") or [],
        "bands": original_request.get("bands") or metadata.get("bands") or [],
        "indices": original_request.get("indices") or metadata.get("indices") or [],
    }


@dataclass(slots=True)
class ImageProviderPreviewReport:
    success: bool
    provider: str
    report_type: str
    not_replacing_workflow: bool
    workflow_relation: dict[str, Any]
    preview: dict[str, Any] = field(default_factory=dict)
    request_summary: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_image_provider_preview_report(
    provider_response: Any,
    original_request: Any | None = None,
    workflow_context: Any | None = None,
) -> dict[str, Any]:
    response = _as_dict(provider_response)
    request = _as_dict(original_request)
    workflow = _as_dict(workflow_context)

    mode = str(response.get("mode") or request.get("output_mode") or "").lower()
    if mode in {"export", "geotiff", "drive_export", "cloud_storage_export", "export_preview"}:
        return {
            "success": False,
            "error": "image_provider_report_export_mode_rejected",
            "provider": response.get("provider") or request.get("provider") or "unknown",
            "report_type": "temporary_imagery_preview",
            "not_replacing_workflow": True,
            "limitations": list(_BASE_LIMITATIONS),
            "warnings": ["Export-style preview responses are not allowed in this report layer."],
        }

    preview = {
        "thumbnail_url": response.get("thumbnail_url"),
        "metadata": response.get("metadata") or response.get("data") or {},
    }
    if not preview["metadata"] and response.get("source"):
        preview["metadata"] = {
            "source": response.get("source"),
        }

    warnings = _normalize_list(
        response.get("warnings"),
        request.get("warnings"),
        workflow.get("warnings"),
    )
    if response.get("not_replacing_workflow") is not True:
        warnings.append("provider response did not mark not_replacing_workflow=true; report forced it to true.")

    limitations = _normalize_list(
        _BASE_LIMITATIONS,
        response.get("limitations"),
        workflow.get("limitations"),
    )

    report = ImageProviderPreviewReport(
        success=bool(response.get("success", True)) and response.get("error") is None,
        provider=str(response.get("provider") or request.get("provider") or "unknown"),
        report_type="temporary_imagery_preview",
        not_replacing_workflow=True,
        workflow_relation={
            "primary_workflow": "openeo",
            "provider_role": "temporary imagery preview only",
            "does_replace_workflow": False,
        },
        preview=preview,
        request_summary=_request_summary(response, request, preview["metadata"]),
        limitations=limitations,
        warnings=warnings,
        next_steps=_normalize_list(
            workflow.get("next_steps"),
            _DEFAULT_NEXT_STEPS,
        ),
    ).to_dict()

    report["not_replacing_workflow"] = True
    report["workflow_relation"]["does_replace_workflow"] = False
    report["workflow_relation"]["primary_workflow"] = "openeo"
    report["workflow_relation"]["provider_role"] = "temporary imagery preview only"
    return report
