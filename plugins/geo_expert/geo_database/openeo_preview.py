"""Preview-only conversion from geo workflow plans to OpenEO job contracts."""

from __future__ import annotations

from typing import Any

from .openeo_contracts import (
    BACKEND_EXTENSION_PROCESSES,
    NOTEBOOK_COLLECTION_CANDIDATES,
    OpenEOCollectionSpec,
    OpenEOJobPreview,
)
from .openeo_validator import build_backend_config, collect_missing_preview_inputs, reject_real_backend_execution


def _normalize_workflow_plan(workflow_plan: dict[str, Any]) -> dict[str, Any]:
    if isinstance(workflow_plan, dict) and "steps" in workflow_plan:
        return workflow_plan
    if isinstance(workflow_plan, dict) and isinstance(workflow_plan.get("workflow_plan"), dict):
        nested = workflow_plan["workflow_plan"]
        if "steps" in nested:
            return nested
    return workflow_plan


def _infer_collection_candidate(workflow_plan: dict[str, Any], provided_inputs: dict[str, Any]) -> OpenEOCollectionSpec | None:
    explicit = provided_inputs.get("collection_id")
    if explicit:
        meta = NOTEBOOK_COLLECTION_CANDIDATES.get(explicit, {})
        return OpenEOCollectionSpec(
            collection_id=explicit,
            spatial_extent=provided_inputs.get("aoi"),
            temporal_extent=provided_inputs.get("time_range") or [],
            bands=provided_inputs.get("bands") or [],
            candidate_only=False,
            backend_specific=bool(meta.get("backend_specific", False)),
        )

    uses_openeo = any(
        step.get("tool") in {
            "geo.openeo.select_collection",
            "geo.openeo.cloud_mask",
            "geo.openeo.compute_indices",
        }
        for step in (workflow_plan or {}).get("steps", [])
    )
    if not uses_openeo:
        return None

    candidate = "SENTINEL2_L2A"
    return OpenEOCollectionSpec(
        collection_id=candidate,
        spatial_extent=provided_inputs.get("aoi"),
        temporal_extent=provided_inputs.get("time_range") or [],
        bands=provided_inputs.get("bands") or ["B04", "B08", "B11", "SCL"],
        candidate_only=True,
        backend_specific=False,
    )


def _indices_for_preview(provided_inputs: dict[str, Any]) -> list[str]:
    indices = provided_inputs.get("indices") or []
    normalized = [str(item).upper() for item in indices]
    if normalized:
        return normalized
    return ["NDVI", "NDBI"]


def _build_process_graph(workflow_plan: dict[str, Any], collection: OpenEOCollectionSpec | None, provided_inputs: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    graph: dict[str, Any] = {}
    risks: list[str] = []
    collection_ref = None
    step_counter = 1
    has_cloud_mask = False
    has_landuse_overlay = False

    if collection is not None:
        collection_ref = f"node_{step_counter}"
        graph[collection_ref] = {
            "process_id": "load_collection",
            "arguments": {
                "collection_id": collection.collection_id,
                "spatial_extent": collection.spatial_extent,
                "temporal_extent": collection.temporal_extent,
                "bands": collection.bands,
            },
            "metadata": {
                "candidate_only": collection.candidate_only,
                "backend_specific": collection.backend_specific,
            },
        }
        step_counter += 1

    current_ref = collection_ref
    for step in (workflow_plan or {}).get("steps", []):
        tool = step.get("tool")
        if tool == "geo.openeo.cloud_mask":
            has_cloud_mask = True
            node_id = f"node_{step_counter}"
            graph[node_id] = {
                "process_id": "cloudmask",
                "arguments": {
                    "data_10m": {"from_node": current_ref},
                    "data_20m": {"from_collection": "SouthTW_20m"},
                    "data_60m": {"from_collection": "SouthTW_60m"},
                    "threshold": provided_inputs.get("cloud_threshold", 0.4),
                    "reference_resolution": provided_inputs.get("reference_resolution", "10m"),
                },
                "metadata": BACKEND_EXTENSION_PROCESSES["cloudmask"],
            }
            current_ref = node_id
            step_counter += 1
            continue
        if tool == "geo.openeo.compute_indices":
            node_id = f"node_{step_counter}"
            indices = _indices_for_preview(provided_inputs)
            graph[node_id] = {
                "process_id": "compute_indices",
                "arguments": {
                    "data": {"from_node": current_ref},
                    "indices": indices,
                },
                "metadata": {
                    "preview_only": True,
                    "candidate_processes": [
                        {
                            "process_id": "ndvi",
                            "arguments": {"nir": "nir", "red": "red"},
                        }
                        for index in indices
                        if index == "NDVI"
                    ] + [
                        {
                            "process_id": "ndbi",
                            "arguments": {"swir": "swir_1", "nir": "nir"},
                        }
                        for index in indices
                        if index == "NDBI"
                    ],
                },
            }
            current_ref = node_id
            step_counter += 1
            continue
        if tool == "geo.gis.overlay_landuse":
            has_landuse_overlay = True
            risks.append(
                "Local landuse overlay may require data outside OpenEO core processes and may not be supported on every backend."
            )
            continue
        if tool == "geo.eo.landcover_classify":
            node_id = f"node_{step_counter}"
            graph[node_id] = {
                "process_id": "landcover",
                "arguments": {
                    "data": {"from_node": current_ref},
                    "blue": "blue",
                    "green": "green",
                    "red": "red",
                    "nir": "nir",
                },
                "metadata": BACKEND_EXTENSION_PROCESSES["landcover"],
            }
            current_ref = node_id
            step_counter += 1
            continue

    save_node = f"node_{step_counter}"
    graph[save_node] = {
        "process_id": "save_result",
        "arguments": {
            "data": {"from_node": current_ref},
            "format": provided_inputs.get("output_format", "GeoTIFF"),
        },
        "result": True,
    }

    if has_cloud_mask:
        risks.append("cloudmask is backend-specific and requires multi-resolution collections.")
    if has_landuse_overlay:
        risks.append("Landuse overlay remains a preview risk because local vector overlay may need a non-backend GIS step.")
    return graph, list(dict.fromkeys(risks))


def build_openeo_job_preview(
    workflow_plan: dict[str, Any],
    provided_inputs: dict[str, Any] | None = None,
    backend_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    provided = dict(provided_inputs or {})
    workflow_plan = _normalize_workflow_plan(workflow_plan)
    config = build_backend_config(backend_config)
    rejection = reject_real_backend_execution(config)
    if rejection is not None:
        return rejection

    collection = _infer_collection_candidate(workflow_plan, provided)
    missing_inputs = collect_missing_preview_inputs(workflow_plan, provided)
    if collection is not None and collection.candidate_only and "collection_id" in missing_inputs:
        missing_inputs.remove("collection_id")

    process_graph_preview, estimated_risks = _build_process_graph(workflow_plan, collection, provided)
    preview = OpenEOJobPreview(
        success=True,
        execution_mode="preview_only",
        requires_approval=True,
        backend_url=config.backend_url,
        collection=collection.to_dict() if collection is not None else {},
        process_graph_preview=process_graph_preview,
        estimated_risks=estimated_risks,
        missing_inputs=missing_inputs,
        approval_message=(
            "This is a preview only. Real OpenEO backend execution is not supported in this version "
            "and would require explicit user approval plus a separate approval-enabled adapter."
        ),
    )
    return preview.to_dict()
