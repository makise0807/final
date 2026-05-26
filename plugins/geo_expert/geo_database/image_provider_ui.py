"""UI card helpers for temporary image-provider preview reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


_REQUIRED_BADGES = [
    "temporary-preview",
    "not-formal-analysis",
    "not-openeo-result",
    "no-download",
    "no-export",
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


def _normalize_text_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        items = value
    else:
        items = [value]
    merged: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in merged:
            merged.append(text)
    return merged


def _has_unsafe_mode(report: dict[str, Any]) -> bool:
    mode = str(report.get("mode") or "").lower()
    if mode in {"export", "geotiff", "drive_export", "cloud_storage_export", "export_preview"}:
        return True
    preview_mode = str(report.get("report_type") or "").lower()
    return preview_mode != "temporary_imagery_preview"


def _thumbnail_from_report(report: dict[str, Any]) -> dict[str, Any]:
    preview = _as_dict(report.get("preview"))
    thumbnail = _as_dict(preview.get("thumbnail") or {})
    url = preview.get("thumbnail_url") or thumbnail.get("url") or ""
    alt = thumbnail.get("alt") or "Temporary satellite imagery preview"
    return {"url": url, "alt": alt}


def _summary_from_report(report: dict[str, Any]) -> dict[str, Any]:
    request_summary = _as_dict(report.get("request_summary"))
    return {
        "collection": request_summary.get("collection") or "",
        "time_range": request_summary.get("time_range") or [],
        "bands": request_summary.get("bands") or [],
        "aoi_area_km2": request_summary.get("aoi_area_km2"),
    }


@dataclass(slots=True)
class ImageProviderPreviewCard:
    success: bool
    card_type: str
    title: str
    subtitle: str
    provider: str
    thumbnail: dict[str, Any] = field(default_factory=dict)
    badges: list[str] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    workflow_relation: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    safe_display: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_image_provider_preview_card(preview_report: Any) -> dict[str, Any]:
    report = _as_dict(preview_report)
    if not report:
        return {
            "success": False,
            "error": "image_provider_preview_card_invalid_report",
            "card_type": "image_provider_preview",
            "safe_display": False,
        }

    if report.get("not_replacing_workflow") is not True:
        return {
            "success": False,
            "error": "image_provider_preview_card_requires_not_replacing_workflow",
            "card_type": "image_provider_preview",
            "safe_display": False,
        }

    if _has_unsafe_mode(report):
        return {
            "success": False,
            "error": "image_provider_preview_card_unsafe_mode",
            "card_type": "image_provider_preview",
            "safe_display": False,
        }

    workflow_relation = _as_dict(report.get("workflow_relation"))
    if workflow_relation.get("does_replace_workflow") is not False:
        return {
            "success": False,
            "error": "image_provider_preview_card_requires_nonreplacement",
            "card_type": "image_provider_preview",
            "safe_display": False,
        }

    provider = str(report.get("provider") or "unknown")
    thumbnail = _thumbnail_from_report(report)
    summary = _summary_from_report(report)
    warnings = _normalize_text_list(report.get("warnings"))
    limitations = _normalize_text_list(report.get("limitations"))
    next_steps = _normalize_text_list(report.get("next_steps"))
    badges = list(dict.fromkeys(_REQUIRED_BADGES))
    if thumbnail.get("url"):
        badges.append("thumbnail-available")
    if provider == "gee":
        badges.append("gee-provider")

    card = ImageProviderPreviewCard(
        success=True,
        card_type="image_provider_preview",
        title="GEE Temporary Imagery Preview",
        subtitle="Temporary preview only - OpenEO workflow remains primary",
        provider=provider,
        thumbnail=thumbnail,
        badges=badges,
        summary=summary,
        workflow_relation={
            "primary_workflow": "openeo",
            "provider_role": "temporary imagery preview only",
            "does_replace_workflow": False,
        },
        warnings=warnings,
        limitations=limitations,
        next_steps=next_steps or [
            "Return to OpenEO workflow validation.",
            "Use this card for preview presentation only.",
        ],
        safe_display=True,
    ).to_dict()

    forbidden_keys = {
        "service_account_key_path",
        "client_secret",
        "password",
        "token",
        "secret",
        "credentials",
    }
    if any(key in report for key in forbidden_keys):
        card["warnings"].append("Sensitive fields were stripped from the UI card.")
    card["safe_display"] = True
    return card

