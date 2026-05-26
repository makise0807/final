"""Contracts for temporary imagery providers that do not replace OpenEO workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ImageProviderRequest:
    provider: str
    task: str
    collection_hint: str | None = None
    collection: str | None = None
    aoi: dict[str, Any] = field(default_factory=dict)
    time_range: list[str] = field(default_factory=list)
    bands: list[str] = field(default_factory=list)
    indices: list[str] = field(default_factory=list)
    vis_params: dict[str, Any] = field(default_factory=dict)
    output_mode: str = "metadata"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ImageProviderResponse:
    success: bool
    provider: str
    mode: str
    source: str
    not_replacing_workflow: bool = True
    data: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
