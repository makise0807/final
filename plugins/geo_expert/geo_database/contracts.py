"""Deterministic workflow contracts for geo expert planning."""

from __future__ import annotations

WORKFLOW_CONTRACTS = {
    "geo.input.collect": {
        "tool": "geo.input.collect",
        "required_inputs": ["aoi", "time_range"],
        "optional_inputs": ["landuse_layer", "zoning_layer", "target_description"],
        "outputs": ["validated_inputs"],
        "failure_modes": [
            "missing area of interest",
            "missing time range",
            "invalid input geometry",
        ],
        "dry_run_example": {
            "aoi": "township boundary",
            "time_range": "2025-01-01/2025-12-31",
        },
    },
    "geo.openeo.select_collection": {
        "tool": "geo.openeo.select_collection",
        "required_inputs": ["validated_inputs", "collection"],
        "optional_inputs": ["bands"],
        "outputs": ["imagery_collection"],
        "failure_modes": [
            "missing validated inputs",
            "unsupported collection",
            "missing collection name",
        ],
        "dry_run_example": {
            "collection": "Sentinel-2",
            "bands": ["B04", "B08", "B11"],
        },
    },
    "geo.openeo.cloud_mask": {
        "tool": "geo.openeo.cloud_mask",
        "required_inputs": ["imagery_collection"],
        "optional_inputs": ["cloud_strategy"],
        "outputs": ["clean_imagery"],
        "failure_modes": [
            "missing imagery collection",
            "cloud masking strategy unavailable",
        ],
        "dry_run_example": {
            "cloud_strategy": "scl-mask",
        },
    },
    "geo.openeo.compute_indices": {
        "tool": "geo.openeo.compute_indices",
        "required_inputs": ["clean_imagery", "indices"],
        "optional_inputs": ["scale", "resolution"],
        "outputs": ["index_layers"],
        "failure_modes": [
            "missing clean imagery",
            "unsupported index",
            "invalid resolution",
        ],
        "dry_run_example": {
            "indices": ["NDVI", "NDBI"],
            "resolution": 10,
        },
    },
    "geo.eo.landcover_classify": {
        "tool": "geo.eo.landcover_classify",
        "required_inputs": ["clean_imagery"],
        "optional_inputs": ["index_layers", "label_scheme"],
        "outputs": ["landcover_map"],
        "failure_modes": [
            "missing clean imagery",
            "unknown label scheme",
        ],
        "dry_run_example": {
            "label_scheme": "built_up_vs_agriculture",
        },
    },
    "geo.gis.overlay_landuse": {
        "tool": "geo.gis.overlay_landuse",
        "required_inputs": ["landcover_map", "landuse_layer"],
        "optional_inputs": ["zoning_layer"],
        "outputs": ["overlay_features"],
        "failure_modes": [
            "missing landcover map",
            "missing landuse layer",
            "overlay geometry mismatch",
        ],
        "dry_run_example": {
            "landuse_layer": "agricultural zoning polygons",
        },
    },
    "geo.analysis.rank_suspicious_sites": {
        "tool": "geo.analysis.rank_suspicious_sites",
        "required_inputs": ["overlay_features"],
        "optional_inputs": ["index_layers", "ranking_rules"],
        "outputs": ["ranked_sites"],
        "failure_modes": [
            "missing overlay features",
            "ranking rules invalid",
        ],
        "dry_run_example": {
            "ranking_rules": ["built_up_signature", "agricultural_zone_overlap"],
        },
    },
    "geo.report.generate": {
        "tool": "geo.report.generate",
        "required_inputs": ["ranked_sites"],
        "optional_inputs": ["citations", "notes"],
        "outputs": ["report_summary"],
        "failure_modes": [
            "missing ranked sites",
            "report template unavailable",
        ],
        "dry_run_example": {
            "notes": "dry run only",
        },
    },
}

READ_ONLY_WORKFLOW_TOOLS = set(WORKFLOW_CONTRACTS)
