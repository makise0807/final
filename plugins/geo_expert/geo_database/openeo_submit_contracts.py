"""Contracts for approval-gated OpenEO submit design."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Any


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class OpenEOSubmitRequest:
    request_id: str
    preview_id: str
    backend_url: str | None
    process_graph_preview: dict[str, Any]
    capabilities_source: str
    validation_report: dict[str, Any]
    estimated_risks: list[str] = field(default_factory=list)
    required_approvals: list[str] = field(default_factory=list)
    status: str = "draft"
    created_at: str = field(default_factory=_utcnow_iso)
    created_by: str = "local_user"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OpenEOSubmitPolicyDecision:
    allowed: bool
    status: str
    reasons: list[str] = field(default_factory=list)
    required_approvals: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_submit_request(
    preview: dict[str, Any],
    validation_report: dict[str, Any],
    capabilities_source: str,
    backend_url: str | None = None,
) -> OpenEOSubmitRequest:
    preview_id = (
        preview.get("preview_id")
        or preview.get("job_id")
        or f"preview-{uuid.uuid4().hex[:12]}"
    )
    required_approvals: list[str] = []
    if list(validation_report.get("backend_extensions_required") or []):
        required_approvals.append("backend_extension_approval")
    if validation_report.get("approval_required"):
        required_approvals.append("approval_required")
    return OpenEOSubmitRequest(
        request_id=f"submit-{uuid.uuid4().hex[:12]}",
        preview_id=preview_id,
        backend_url=backend_url or preview.get("backend_url"),
        process_graph_preview=dict(preview.get("process_graph_preview") or {}),
        capabilities_source=capabilities_source,
        validation_report=dict(validation_report or {}),
        estimated_risks=list(preview.get("estimated_risks") or []),
        required_approvals=list(dict.fromkeys(required_approvals)),
        status="draft",
    )
