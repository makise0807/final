"""In-memory approval token skeleton for future real OpenEO execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import uuid
from typing import Any


_APPROVAL_STORE: dict[str, dict[str, Any]] = {}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class OpenEOApprovalRequest:
    action: str
    preview_id: str
    risks: list[str]
    created_at: str
    expires_at: str
    approved: bool = False
    token: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_approval_request(action: str, preview: dict[str, Any], risks: list[str] | None = None) -> dict[str, Any]:
    now = _utcnow()
    token = f"approve-{uuid.uuid4().hex}"
    preview_id = preview.get("job_id") or preview.get("preview_id") or f"preview-{uuid.uuid4().hex[:12]}"
    request = OpenEOApprovalRequest(
        action=action,
        preview_id=preview_id,
        risks=list(risks or preview.get("estimated_risks") or []),
        created_at=now.isoformat(),
        expires_at=(now + timedelta(minutes=30)).isoformat(),
        approved=False,
        token=token,
    ).to_dict()
    _APPROVAL_STORE[token] = request
    return request


def verify_approval_token(token: str | None, action: str) -> dict[str, Any]:
    if not token:
        return {"success": False, "error": "missing_approval_token", "requires_approval": True}
    request = _APPROVAL_STORE.get(token)
    if request is None:
        return {"success": False, "error": "invalid_approval_token", "requires_approval": True}
    if request["action"] != action:
        return {"success": False, "error": "approval_action_mismatch", "requires_approval": True}
    if _utcnow() > datetime.fromisoformat(request["expires_at"]):
        return {"success": False, "error": "approval_token_expired", "requires_approval": True}
    return {"success": True, "approved": True, "request": request}
