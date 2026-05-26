"""Safe response contract for controlled real OpenEO job submission."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class OpenEOCreateJobResponse:
    success: bool
    submitted: bool
    job_id: str | None
    backend_url: str | None
    request_id: str
    preview_id: str
    status: str = "unknown"
    location: str | None = None
    raw_response_summary: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utcnow_iso)
    warnings: list[str] = field(default_factory=list)
    downloaded: bool = False
    polling_started: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
