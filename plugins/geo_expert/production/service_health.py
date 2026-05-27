from __future__ import annotations

from typing import Any

from ..adapters.detector_tools import detector_status
from ..adapters.eo_tools import list_eo_cache_images
from ..adapters.satellite_tools import satellite_status
from ..adapters.spatial_tools import spatial_status
from ..legal_grounding import build_applicability_check
from ..adapters.rag_tools import search_regulations


def check_service_health() -> dict[str, Any]:
    chroma = search_regulations("農地種電", top_k=1)
    postgis = spatial_status()
    detector = detector_status()
    sat = satellite_status()
    eo_cache = list_eo_cache_images()
    legal = build_applicability_check(user_request="農業區違章工廠", workflow_id="WF-001", facts={})
    openeo = {
        "success": False,
        "status": "degraded",
        "message": "Use geo_expert.openeo_acquisition_plan or run tool for approval-gated checks.",
    }
    gee = {
        "success": bool(sat.get("gee_enabled")),
        "status": "success" if sat.get("gee_enabled") else "degraded",
        "allow_fetch": bool(sat.get("allow_fetch")),
    }
    return {
        "success": True,
        "chromadb": chroma,
        "postgis": postgis,
        "detector": detector,
        "satellite_cache": eo_cache,
        "gee": gee,
        "openeo": openeo,
        "legal_grounding": legal,
    }
