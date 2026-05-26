"""Mock capabilities and validation helpers for future real OpenEO adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .openeo_contracts import (
    BACKEND_EXTENSION_PROCESSES,
    NOTEBOOK_BACKEND_URL,
    NOTEBOOK_COLLECTION_CANDIDATES,
    STANDARD_OPENEO_PROCESSES,
)


@dataclass(slots=True)
class OpenEOCapabilities:
    backend_url: str
    collections: list[dict[str, Any]] = field(default_factory=list)
    processes: list[dict[str, Any]] = field(default_factory=list)
    backend_extensions: list[str] = field(default_factory=list)
    unknown_processes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    retrieved_at: str | None = None
    source: str = "not_loaded"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_mock_capabilities_from_notebook_notes() -> OpenEOCapabilities:
    return OpenEOCapabilities(
        backend_url=NOTEBOOK_BACKEND_URL,
        collections=[
            {
                "id": collection_id,
                "title": collection_id,
                "backend_specific": bool(NOTEBOOK_COLLECTION_CANDIDATES[collection_id].get("backend_specific")),
            }
            for collection_id in sorted(
                collection_id
                for collection_id in NOTEBOOK_COLLECTION_CANDIDATES
                if collection_id != "SENTINEL2_L2A"
            )
        ],
        processes=[
            {"id": process_id, **STANDARD_OPENEO_PROCESSES[process_id]}
            for process_id in sorted(STANDARD_OPENEO_PROCESSES)
        ],
        backend_extensions=sorted(BACKEND_EXTENSION_PROCESSES),
        unknown_processes=[],
        warnings=[],
        retrieved_at=None,
        source="mock",
    )


def real_capabilities_to_contract(
    raw_collections: list[dict[str, Any]] | list[str],
    raw_processes: list[dict[str, Any]] | list[str],
    backend_url: str,
    retrieved_at: str | None = None,
) -> OpenEOCapabilities:
    collection_entries: list[dict[str, Any]] = []
    for item in raw_collections:
        if isinstance(item, str):
            collection_entries.append({"id": item, "title": item})
        elif isinstance(item, dict) and item.get("id"):
            collection_entries.append(
                {
                    "id": str(item["id"]),
                    "title": item.get("title") or item.get("description") or str(item["id"]),
                    "spatial_extent": item.get("extent", {}).get("spatial") if isinstance(item.get("extent"), dict) else item.get("spatial_extent"),
                    "temporal_extent": item.get("extent", {}).get("temporal") if isinstance(item.get("extent"), dict) else item.get("temporal_extent"),
                    "bands": (
                        [band.get("name") for band in item.get("cube:dimensions", {}).get("bands", {}).get("values", [])]
                        if isinstance(item.get("cube:dimensions"), dict)
                        else item.get("bands")
                    ),
                }
            )

    core_processes: list[dict[str, Any]] = []
    backend_extensions: list[str] = []
    unknown_processes: list[str] = []
    warnings: list[str] = []
    known_core = set(STANDARD_OPENEO_PROCESSES)
    known_extension = set(BACKEND_EXTENSION_PROCESSES)

    for item in raw_processes:
        process_id = item if isinstance(item, str) else item.get("id")
        if not process_id:
            continue
        process_id = str(process_id)
        process_entry = {
            "id": process_id,
            "summary": item.get("summary") if isinstance(item, dict) else None,
            "parameters": item.get("parameters") if isinstance(item, dict) else None,
        }
        if process_id in known_core:
            core_processes.append(process_entry)
        elif process_id in known_extension:
            backend_extensions.append(process_id)
        else:
            unknown_processes.append(process_id)

    if unknown_processes:
        warnings.append(
            "Some processes could not be classified as openEO core or known backend extensions."
        )
    expected_extensions = {pid for pid in BACKEND_EXTENSION_PROCESSES}
    missing_extensions = sorted(expected_extensions - set(backend_extensions))
    if missing_extensions:
        warnings.append(f"missing expected notebook extension: {', '.join(missing_extensions)}")
    expected_collections = {cid for cid in NOTEBOOK_COLLECTION_CANDIDATES if cid != 'SENTINEL2_L2A'}
    found_collection_ids = {entry["id"] for entry in collection_entries if entry.get("id")}
    missing_collections = sorted(expected_collections - found_collection_ids)
    if missing_collections:
        warnings.append(f"missing expected notebook collection: {', '.join(missing_collections)}")

    return OpenEOCapabilities(
        backend_url=backend_url,
        collections=sorted(collection_entries, key=lambda item: item["id"]),
        processes=sorted(core_processes, key=lambda item: item["id"]),
        backend_extensions=sorted(dict.fromkeys(backend_extensions)),
        unknown_processes=sorted(dict.fromkeys(unknown_processes)),
        warnings=warnings,
        retrieved_at=retrieved_at or datetime.now(timezone.utc).isoformat(),
        source="real",
    )


def validate_collection_available(collection_id: str, capabilities: OpenEOCapabilities) -> dict[str, Any]:
    if any(item.get("id") == collection_id for item in capabilities.collections):
        return {"success": True, "collection_id": collection_id, "available": True}
    return {
        "success": False,
        "collection_id": collection_id,
        "error": "missing_collection",
        "available": False,
    }


def validate_process_available(process_id: str, capabilities: OpenEOCapabilities) -> dict[str, Any]:
    if any(item.get("id") == process_id for item in capabilities.processes):
        return {"success": True, "process_id": process_id, "available": True, "process_type": "openEO_core"}
    if process_id in capabilities.backend_extensions:
        meta = BACKEND_EXTENSION_PROCESSES[process_id]
        return {
            "success": True,
            "process_id": process_id,
            "available": True,
            "process_type": "backend_extension",
            "requires_approval": bool(meta.get("requires_approval", False)),
            "high_compute_cost": bool(meta.get("high_compute_cost", False)),
        }
    return {
        "success": False,
        "process_id": process_id,
        "error": "missing_process",
        "available": False,
    }


def validate_preview_against_capabilities(preview: dict[str, Any], capabilities: OpenEOCapabilities) -> dict[str, Any]:
    collection = dict(preview.get("collection") or {})
    graph = dict(preview.get("process_graph_preview") or {})
    missing_collections: list[str] = []
    missing_processes: list[str] = []
    backend_extensions_required: list[str] = []
    warnings: list[str] = []
    risks: list[str] = list(preview.get("estimated_risks") or [])
    notes: list[str] = []
    approval_required = False

    if capabilities.source == "mock":
        notes.append("Validation used notebook-derived mock capabilities.")
    elif capabilities.source == "real_cached":
        notes.append("Validation used cached real backend metadata.")
    elif capabilities.source == "real":
        notes.append("Validation used live real backend metadata.")

    collection_id = collection.get("collection_id")
    if collection_id:
        collection_check = validate_collection_available(collection_id, capabilities)
        if not collection_check["success"] and not collection.get("candidate_only"):
            missing_collections.append(collection_id)
        elif not collection_check["success"] and collection.get("candidate_only"):
            warnings.append("candidate collection is not claimed available on the selected capabilities source")
            notes.append("Collection remains a candidate only and is not confirmed as backend-supported.")

    for node in graph.values():
        process_id = node.get("process_id")
        if not process_id:
            continue
        process_check = validate_process_available(process_id, capabilities)
        if not process_check["success"]:
            if process_id not in {"compute_indices"}:
                missing_processes.append(process_id)
            continue
        if process_check.get("process_type") == "backend_extension":
            backend_extensions_required.append(process_id)
            warnings.append(f"backend extension required: {process_id}")
            approval_required = True
        if process_check.get("requires_approval"):
            warnings.append(f"approval required: {process_id}")
            approval_required = True
        if process_check.get("high_compute_cost"):
            warnings.append(f"high compute process requires approval: {process_id}")
            approval_required = True
        if process_id == "save_result":
            notes.append("save_result preview is metadata-only and does not imply backend submission.")

    if any("landuse overlay" in risk.lower() for risk in risks):
        warnings.append("landuse overlay is outside OpenEO core and may require external GIS processing")

    return {
        "success": not missing_collections and not missing_processes,
        "validation_source": capabilities.source,
        "can_validate": True,
        "missing_collections": list(dict.fromkeys(missing_collections)),
        "missing_processes": list(dict.fromkeys(missing_processes)),
        "backend_extensions_required": list(dict.fromkeys(backend_extensions_required)),
        "approval_required": approval_required,
        "warnings": list(dict.fromkeys(warnings)),
        "notes": list(dict.fromkeys(notes)),
        "risks": list(dict.fromkeys(risks)),
    }
