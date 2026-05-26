"""OpenEO backend-facing contract skeletons for preview and mock execution.

This module intentionally defines stdlib-only data structures. It does not
import the real ``openeo`` package and does not perform any network I/O.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


NOTEBOOK_BACKEND_URL = "https://geodatacube.p.colife.org.tw/SecureData/APIProxy/odc/openeo/"


NOTEBOOK_COLLECTION_CANDIDATES = {
    "sentinel2_taiwan": {
        "backend_specific": True,
        "notes": "Notebook example collection for Sentinel-2 descriptive bands.",
    },
    "SouthTW_10m": {"backend_specific": True},
    "SouthTW_20m": {"backend_specific": True},
    "SouthTW_60m": {"backend_specific": True},
    "wushantou_10m": {"backend_specific": True},
    "wushantou_20m": {"backend_specific": True},
    "Landslide_pre": {"backend_specific": True},
    "Landslide_post": {"backend_specific": True},
    "Landslide_dem": {"backend_specific": True},
    "Landslide_slope": {"backend_specific": True},
    "Landslide_aspect_sin": {"backend_specific": True},
    "Landslide_aspect_cos": {"backend_specific": True},
    "SENTINEL2_L2A": {
        "backend_specific": False,
        "notes": "Generic candidate used for preview when a Sentinel-2 task is inferred.",
    },
}


STANDARD_OPENEO_PROCESSES = {
    "load_collection": {
        "process_type": "openEO_core",
    },
    "ndvi": {
        "process_type": "openEO_core",
    },
    "reduce_dimension": {
        "process_type": "openEO_core",
    },
    "median": {
        "process_type": "openEO_core",
    },
    "apply": {
        "process_type": "openEO_core",
    },
    "clip": {
        "process_type": "openEO_core",
    },
    "save_result": {
        "process_type": "openEO_core",
    },
}


BACKEND_EXTENSION_PROCESSES = {
    "cloudmask": {
        "process_type": "backend_extension",
        "risk": "backend_specific_process",
        "requires_multi_resolution_inputs": True,
        "required_collections": ["SouthTW_10m", "SouthTW_20m", "SouthTW_60m"],
    },
    "landcover": {
        "process_type": "backend_extension",
        "model_type": "UNet landcover classification",
        "output_classes": [
            {"id": 0, "label": "background"},
            {"id": 1, "label": "urban"},
            {"id": 2, "label": "road"},
            {"id": 3, "label": "vegetation"},
            {"id": 4, "label": "water"},
            {"id": 5, "label": "agriculture"},
            {"id": 6, "label": "bare soil"},
        ],
    },
    "resample_spatial": {
        "process_type": "backend_extension",
        "backend_extension": True,
    },
    "superresolution": {
        "process_type": "backend_extension",
        "backend_extension": True,
        "high_compute_cost": True,
        "requires_approval": True,
    },
    "landslide": {
        "process_type": "backend_extension",
        "backend_extension": True,
        "high_compute_cost": True,
        "disaster_assessment": True,
        "requires_approval": True,
    },
}


@dataclass(slots=True)
class OpenEOBackendConfig:
    backend_url: str | None = None
    auth_mode: str = "none"
    workspace: str | None = None
    dry_run: bool = True
    verify_ssl: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OpenEOSpatialExtent:
    west: float
    south: float
    east: float
    north: float
    crs: str = "EPSG:4326"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OpenEOCollectionSpec:
    collection_id: str
    spatial_extent: dict[str, Any] | None = None
    temporal_extent: list[str] = field(default_factory=list)
    bands: list[str] = field(default_factory=list)
    candidate_only: bool = False
    backend_specific: bool = False
    required_collections: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OpenEOProcessingStep:
    step_id: str
    operation: str
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: list[str] = field(default_factory=list)
    process_type: str = "openEO_core"
    backend_extension: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OpenEOJobPreview:
    success: bool
    execution_mode: str = "preview_only"
    requires_approval: bool = True
    backend_url: str | None = None
    collection: dict[str, Any] = field(default_factory=dict)
    process_graph_preview: dict[str, Any] = field(default_factory=dict)
    estimated_risks: list[str] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)
    approval_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OpenEOJobResult:
    success: bool
    mode: str = "mock"
    job_id: str = ""
    status: str = "created"
    logs: list[str] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

