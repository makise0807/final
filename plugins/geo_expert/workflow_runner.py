from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .adapters.config import detector_config
from .adapters.detector_tools import detector_status, run_detection
from .adapters.eo_tools import eo_local_analysis, list_eo_cache_images, openeo_status, prepare_openeo_request, select_eo_cache_image
from .adapters.rag_tools import search_regulations, search_workflows
from .adapters.satellite_tools import acquire_satellite_preview, satellite_status
from .adapters.spatial_tools import spatial_query, spatial_status
from .adapters.workflow_tools import get_execution_spec, list_workflows
from .geo_database.image_provider_local import load_local_image_fixture
from .reporting.workflow_report import write_workflow_report

DEFAULT_LIMITATIONS = [
    "Preliminary only.",
    "Requires verification.",
    "Not a formal legal conclusion.",
    "No OpenEO real submit performed.",
    "No GeoTIFF/export/download performed.",
]
DEFAULT_AOI = {
    "west": 120.70,
    "south": 23.45,
    "east": 120.72,
    "north": 23.47,
}


def _step_result(
    step: dict[str, Any],
    *,
    status: str,
    used_real_service: bool = False,
    evidence: Any = None,
    warnings: list[str] | None = None,
    limitations: list[str] | None = None,
    error: Any = None,
) -> dict[str, Any]:
    return {
        "step_id": step.get("step_id"),
        "adapter": step.get("adapter"),
        "operation": step.get("operation"),
        "status": status,
        "used_real_service": used_real_service,
        "evidence": evidence if evidence is not None else {},
        "warnings": list(warnings or []),
        "limitations": list(limitations or []),
        "error": error,
    }


def _summarize_warnings(step_results: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    for step in step_results:
        warnings.extend(str(item) for item in (step.get("warnings") or []))
        if step.get("status") == "degraded" and step.get("error"):
            warnings.append(f"{step.get('step_id')}: {step.get('error')}")
    return list(dict.fromkeys(warnings))


def _missing_required_inputs(spec: dict[str, Any], inputs: dict[str, Any]) -> list[str]:
    return [str(item) for item in (spec.get("required_inputs") or []) if not inputs.get(item)]


def _maybe_fill_image_from_eo_cache(workflow_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(inputs)
    if enriched.get("image_path"):
        return enriched
    selected = select_eo_cache_image(
        workflow_id=workflow_id,
        case_id=str(enriched.get("image_case_id") or ""),
        preferred_name=str(enriched.get("preferred_image_name") or ""),
    )
    if not selected.get("success"):
        return enriched
    image = dict(selected.get("selected_image") or {})
    if image.get("image_path"):
        enriched["image_path"] = image["image_path"]
        enriched["image_source"] = "eo_cache"
        enriched["used_real_input"] = True
    if image.get("aoi") and not enriched.get("image_aoi") and not enriched.get("aoi"):
        enriched["aoi"] = image.get("aoi")
    return enriched


def _resolve_satellite_inputs(workflow_id: str, inputs: dict[str, Any], mode: str) -> dict[str, Any]:
    enriched = dict(inputs)
    if enriched.get("image_path"):
        return enriched
    aoi = enriched.get("image_aoi") or enriched.get("aoi") or enriched.get("bbox")
    satellite = acquire_satellite_preview(
        aoi=aoi,
        bbox=enriched.get("bbox"),
        case_id=str(enriched.get("image_case_id") or ""),
        workflow_id=workflow_id,
        mode="prepare_only" if mode == "dry_run" else "cache_only",
    )
    if mode != "dry_run" and aoi and not satellite.get("image_path"):
        satellite = acquire_satellite_preview(
            aoi=aoi,
            bbox=enriched.get("bbox"),
            case_id=str(enriched.get("image_case_id") or ""),
            workflow_id=workflow_id,
            mode="preview",
        )
    enriched["satellite_evidence"] = satellite
    if satellite.get("success") and satellite.get("image_path"):
        enriched["image_path"] = satellite.get("image_path")
        enriched["image_source"] = satellite.get("source") or satellite.get("provider") or "eo_cache"
        enriched["used_real_input"] = bool(satellite.get("used_real_input"))
    if satellite.get("aoi") and not enriched.get("image_aoi") and not enriched.get("aoi"):
        enriched["aoi"] = satellite.get("aoi")
    if satellite.get("warnings"):
        enriched["satellite_warnings"] = list(satellite.get("warnings") or [])
    return enriched


def _wf001_real_detector_enabled(inputs: dict[str, Any]) -> bool:
    if inputs.get("real_detector") is True:
        return True
    return str(os.getenv("GEO_EXPERT_WF001_REAL_DETECTOR", "")).strip().lower() in {"1", "true", "yes", "on"}


def _summarize_service_coverage(results: list[dict[str, Any]]) -> dict[str, Any]:
    eo_cache_info = list_eo_cache_images()
    spatial_info = spatial_status()
    rag_info = search_regulations("都市計畫", top_k=1)
    detector_info = detector_status()
    sat_info = satellite_status()

    chroma_selected: list[str] = []
    chroma_used = 0
    chroma_degraded = 0
    postgis_used = 0
    postgis_degraded = 0
    eo_used = 0
    detector_real_used = 0
    detector_mock_used = 0
    precise_aoi_matches = 0
    fallback_latest_matches = 0
    acquisition_disabled_steps = 0
    preview_fetch_steps = 0
    for workflow in results:
        sat = dict(workflow.get("satellite_evidence") or {})
        if sat.get("match_strategy") in {"case_id_exact", "workflow_hint", "bbox_overlap", "aoi_match"}:
            precise_aoi_matches += 1
        if sat.get("match_strategy") == "latest_without_metadata":
            fallback_latest_matches += 1
        if sat.get("error") == "satellite_acquisition_disabled":
            acquisition_disabled_steps += 1
        if sat.get("service") == "gee_preview" and sat.get("success"):
            preview_fetch_steps += 1
        for step in workflow.get("steps") or []:
            evidence = dict(step.get("evidence") or {})
            adapter = str(step.get("adapter") or "")
            if adapter == "rag":
                if evidence.get("selected_collection"):
                    chroma_selected.append(str(evidence.get("selected_collection")))
                if evidence.get("used_real_service"):
                    chroma_used += 1
                elif step.get("status") == "degraded":
                    chroma_degraded += 1
            if adapter == "spatial":
                if evidence.get("used_real_service"):
                    postgis_used += 1
                elif step.get("status") == "degraded":
                    postgis_degraded += 1
            if adapter in {"eo", "detector"} and (evidence.get("source") == "eo_cache" or evidence.get("image_source") == "eo_cache"):
                eo_used += 1
            if adapter == "detector":
                if evidence.get("used_real_model"):
                    detector_real_used += 1
                elif evidence.get("detector_used") == "mock":
                    detector_mock_used += 1

    alias_checks = list((spatial_info.get("alias_checks") or []))
    missing_aliases = [str(item.get("alias")) for item in alias_checks if not item.get("exists")]
    blockers: list[str] = []
    next_actions: list[str] = []
    if missing_aliases:
        blockers.append(f"PostGIS missing {len(missing_aliases)} aliases: {', '.join(missing_aliases)}")
        next_actions.extend(
            [
                "Import building footprint layer.",
                "Import river or floodplain layer.",
                "Import landuse/agricultural zoning layer.",
                "Import hazard, slope, and ecological layers.",
            ]
        )
    if not rag_info.get("used_real_service"):
        blockers.append("ChromaDB real-service retrieval is unavailable for the audit query.")
        next_actions.append("Re-run offline/local Chroma ingest and verify urban_regulations contains documents.")
    if not eo_cache_info.get("success"):
        blockers.append("EO cache is unavailable.")
        next_actions.append("Set GEO_EXPERT_EO_CACHE_DIR to a readable image cache directory.")
    if detector_info.get("real_model_configured") and detector_real_used == 0:
        blockers.append("YOLO is configured but no workflow step used the real model in this evaluation.")
        next_actions.append("Provide workflow image inputs or enable WF-001 optional real detector mode for manual validation.")
    if fallback_latest_matches:
        blockers.append("Some EO cache selections used latest_without_metadata fallback instead of precise AOI match.")
        next_actions.append("Add EO cache sidecar metadata with AOI or case_id to improve match precision.")
    if not sat_info.get("allow_fetch"):
        next_actions.append("Keep GEO_EXPERT_ALLOW_SATELLITE_FETCH=0 for safe path, or enable it explicitly for GEE preview testing only.")

    total_real = chroma_used + postgis_used + detector_real_used + (1 if eo_used else 0)
    total_possible = max(1, chroma_used + chroma_degraded + postgis_used + postgis_degraded + detector_real_used + detector_mock_used + 1)
    score = round(total_real / total_possible, 2)
    readiness_level = "prototype"
    if score >= 0.85 and not missing_aliases and not fallback_latest_matches:
        readiness_level = "real_service_operational"
    elif score >= 0.35:
        readiness_level = "real_service_partial"
    return {
        "chromadb": {
            "available": bool(rag_info.get("used_real_service")),
            "selected_collections": sorted(set(chroma_selected)),
            "used_steps": chroma_used,
            "degraded_steps": chroma_degraded,
            "embedding_backend": rag_info.get("embedding_backend") or "deterministic_hash_v1",
            "quality_note": [
                str(rag_info.get("quality_note") or "dev_offline_validation"),
                "production_embedding_recommended",
            ],
        },
        "postgis": {
            "available": bool(spatial_info.get("configured") or spatial_info.get("success")),
            "configured": bool(spatial_info.get("configured") or spatial_info.get("database_url") or spatial_info.get("host")),
            "aliases_resolved": sum(1 for item in alias_checks if item.get("exists")),
            "aliases_missing": sum(1 for item in alias_checks if not item.get("exists")),
            "missing_aliases": missing_aliases,
            "used_steps": postgis_used,
            "degraded_steps": postgis_degraded,
            "layer_coverage": {
                "resolved": sum(1 for item in alias_checks if item.get("exists")),
                "missing": sum(1 for item in alias_checks if not item.get("exists")),
                "missing_aliases": missing_aliases,
            },
        },
        "eo_cache": {
            "available": bool(eo_cache_info.get("success") and eo_cache_info.get("image_count")),
            "image_count": int(eo_cache_info.get("image_count") or 0),
            "used_steps": eo_used,
        },
        "satellite": {
            "provider": sat_info.get("provider"),
            "allow_fetch": bool(sat_info.get("allow_fetch")),
            "cache_available": bool(sat_info.get("cache_available")),
            "cache_image_count": int(sat_info.get("cache_image_count") or 0),
            "precise_aoi_matches": precise_aoi_matches,
            "fallback_latest_matches": fallback_latest_matches,
            "acquisition_disabled_steps": acquisition_disabled_steps,
            "preview_fetch_steps": preview_fetch_steps,
            "aoi_match_quality": {
                "precise_count": precise_aoi_matches,
                "fallback_count": fallback_latest_matches,
                "unknown_metadata_count": fallback_latest_matches,
            },
            "blockers": ["EO cache metadata is incomplete for precise AOI matching."] if fallback_latest_matches else [],
            "next_actions": ["Run scripts/index_geo_expert_eo_cache.py after adding sidecar metadata."] if fallback_latest_matches else [],
        },
        "detector": {
            "backend": detector_info.get("backend") or detector_config().get("backend"),
            "real_model_configured": bool(detector_info.get("real_model_configured")),
            "used_real_model_steps": detector_real_used,
            "mock_fallback_steps": detector_mock_used,
            "quality_note": [
                "yolo11n_general_model",
                "domain_specific_training_recommended",
            ],
        },
        "overall_real_service_score": score,
        "readiness_level": readiness_level,
        "real_service_summary": {
            "real_rag_steps": chroma_used,
            "real_spatial_steps": postgis_used,
            "real_detector_steps": detector_real_used,
            "eo_cache_assisted_steps": eo_used,
        },
        "blockers": list(dict.fromkeys(blockers)),
        "next_actions": list(dict.fromkeys(next_actions)),
    }


def _execute_step(step: dict[str, Any], workflow_id: str, user_request: str, inputs: dict[str, Any], mode: str) -> dict[str, Any]:
    inputs = _resolve_satellite_inputs(workflow_id, inputs, mode)
    adapter = str(step.get("adapter") or "").strip().lower()
    operation = str(step.get("operation") or "").strip()
    external_service = str(step.get("external_service") or "none").strip().lower()
    fallback = str(step.get("fallback") or "degraded").strip().lower()
    approval_required = bool(step.get("approval_required"))

    if approval_required:
        return _step_result(
            step,
            status="approval_required",
            evidence={"message": "This step is gated and was not auto-executed."},
            limitations=DEFAULT_LIMITATIONS,
        )

    if adapter == "workflow":
        if operation == "search_workflow":
            result = search_workflows(user_request or workflow_id, top_k=3)
        elif operation == "load_execution_spec":
            result = get_execution_spec(workflow_id)
        elif operation == "validate_inputs":
            result = {"success": True, "required_inputs": list(inputs.keys()), "missing_inputs": []}
        else:
            result = {"success": True, "message": f"Workflow operation noted: {operation}"}
    elif adapter == "rag":
        result = {"success": True, "prepare_only": True, "message": "RAG step planned only in dry_run."} if mode == "dry_run" else search_regulations(user_request or workflow_id, top_k=3)
    elif adapter == "spatial":
        if mode == "dry_run":
            result = spatial_status()
        else:
            parameters = dict(step.get("parameters") or {})
            if operation == "layer_check":
                parameters.setdefault("layer_names", step.get("layer_names") or [])
            result = spatial_query(operation, parameters)
    elif adapter == "eo":
        if operation == "openeo_prepare":
            result = prepare_openeo_request(operation, dict(step.get("parameters") or {}))
        elif operation == "openeo_status":
            result = openeo_status()
        else:
            if mode == "dry_run":
                result = {"success": True, "prepare_only": True, "message": "EO step planned only in dry_run."}
            else:
                params = dict(step.get("parameters") or {})
                if inputs.get("image_path"):
                    params.setdefault("image_path", inputs.get("image_path"))
                if inputs.get("lon") is not None:
                    params.setdefault("lon", inputs.get("lon"))
                if inputs.get("lat") is not None:
                    params.setdefault("lat", inputs.get("lat"))
                result = eo_local_analysis(operation, params)
                if inputs.get("image_source") == "eo_cache":
                    result.setdefault("source", "eo_cache")
                    result.setdefault("used_real_input", True)
    elif adapter == "detector":
        if mode == "dry_run":
            result = {"success": True, "prepare_only": True, "message": "Detector step planned only in dry_run."}
        else:
            image_case_id = str(inputs.get("image_case_id") or "")
            image_path = inputs.get("image_path")
            aoi = inputs.get("image_aoi") or inputs.get("aoi") or dict(DEFAULT_AOI)
            if image_case_id and not image_path:
                fixture = load_local_image_fixture(image_case_id)
                if fixture.get("success"):
                    image_path = fixture.get("image_path")
                    aoi = fixture.get("aoi") or aoi
            if not image_path:
                cache_pick = select_eo_cache_image(workflow_id=workflow_id, case_id=image_case_id)
                if cache_pick.get("success"):
                    selected = dict(cache_pick.get("selected_image") or {})
                    image_path = selected.get("image_path")
                    aoi = selected.get("aoi") or aoi
            result = run_detection(
                {
                    "task": operation or "preliminary_image_recognition",
                    "sop_id": workflow_id,
                    "image_source": "local_fixture" if image_case_id and not inputs.get("image_source") else ("eo_cache" if inputs.get("image_source") == "eo_cache" or (image_path and "eo_cache" in str(image_path).lower()) else ("local_image" if image_path else "mock")),
                    "local_image_path": image_path,
                    "aoi": aoi,
                    "mode": "safe" if mode == "safe_run" else "real",
                    "image_case_id": image_case_id,
                }
            )
    elif adapter == "report":
        result = {"success": True, "message": "Structured workflow report will be generated."}
    else:
        result = {"success": False, "error": "unsupported_adapter", "message": f"Unsupported adapter: {adapter}"}

    success = bool(result.get("success"))
    sat = dict(inputs.get("satellite_evidence") or {})
    if adapter in {"eo", "detector"} and sat:
        result.setdefault("satellite_source", sat.get("source") or sat.get("provider"))
        result.setdefault("satellite_match_strategy", sat.get("match_strategy"))
        result.setdefault("satellite_confidence", sat.get("confidence"))
        result.setdefault("satellite_image_path", sat.get("image_path"))
        result.setdefault("satellite_warning", ", ".join(str(item) for item in (sat.get("warnings") or [])))
    warnings = list(result.get("warnings") or [])
    if adapter in {"eo", "detector"} and sat.get("warnings"):
        warnings.extend(str(item) for item in sat.get("warnings") or [])
    warnings = list(dict.fromkeys(warnings))
    used_real_service = bool(result.get("used_real_service") or result.get("used_real_model"))
    if success:
        if result.get("approval_required"):
            status = "approval_required"
        elif result.get("fallback_used") or result.get("prepare_only"):
            status = "degraded" if mode != "dry_run" else "success"
        else:
            status = "success"
    else:
        status = "degraded" if external_service != "none" or fallback in {"degraded", "skip", "local_text", "local_fixture"} else "failed"

    return _step_result(
        step,
        status=status,
        used_real_service=used_real_service,
        evidence=result,
        warnings=warnings,
        limitations=list(result.get("limitations") or []),
        error=result.get("error") or result.get("message"),
    )


def _run_wf001_compat(user_request: str, inputs: dict[str, Any]) -> dict[str, Any]:
    from .tools import run_preliminary_case_check_handler

    payload = {
        "user_request": user_request,
        "image_case_id": inputs.get("image_case_id", "sample_taichung_case"),
        "image_path": inputs.get("image_path"),
        "image_aoi": inputs.get("image_aoi"),
        "require_satellite": bool(inputs.get("require_satellite", False)),
        "use_llm": bool(inputs.get("use_llm", False)),
        "output_dir": inputs.get("output_dir"),
    }
    return json.loads(run_preliminary_case_check_handler(payload))


def _run_wf001_real_detector(user_request: str, inputs: dict[str, Any], spec: dict[str, Any], mode: str) -> dict[str, Any]:
    compat = _run_wf001_compat(user_request, inputs)
    image_case_id = str(inputs.get("image_case_id") or "sample_taichung_case")
    fixture = load_local_image_fixture(image_case_id)
    image_path = inputs.get("image_path") or fixture.get("image_path")
    image_aoi = inputs.get("image_aoi") or inputs.get("aoi") or fixture.get("aoi") or dict(DEFAULT_AOI)
    image_source = "local_fixture" if fixture.get("success") else (inputs.get("image_source") or "eo_cache")
    detector_result = run_detection(
        {
            "task": "run_preliminary_case_check",
            "sop_id": "WF-001",
            "local_image_path": image_path,
            "aoi": image_aoi,
            "image_source": image_source,
            "image_case_id": image_case_id,
            "mode": "safe" if mode == "safe_run" else "real",
        }
    )
    steps = []
    for step in spec.get("steps") or []:
        op = str(step.get("operation") or "")
        if op == "run_preliminary_case_check":
            status = "success" if detector_result.get("success") else "degraded"
            steps.append(
                _step_result(
                    step,
                    status=status,
                    used_real_service=bool(detector_result.get("used_real_model") or detector_result.get("used_real_service")),
                    evidence=detector_result,
                    warnings=list(detector_result.get("warnings") or []),
                    limitations=list(detector_result.get("limitations") or DEFAULT_LIMITATIONS),
                    error=detector_result.get("error"),
                )
            )
        else:
            steps.append(
                _step_result(
                    step,
                    status="success",
                    evidence={"message": "Step satisfied by compatible WF-001 preliminary workflow run."},
                    limitations=list(DEFAULT_LIMITATIONS),
                )
            )
    result = {
        "success": bool(compat.get("success")),
        "workflow_id": "WF-001",
        "title": spec.get("title"),
        "status": "success" if compat.get("success") else "degraded",
        "mode": mode,
        "user_request": user_request,
        "inputs": inputs,
        "completed_steps": [step["step_id"] for step in steps if step["status"] == "success"],
        "degraded_steps": [step["step_id"] for step in steps if step["status"] == "degraded"],
        "approval_required_steps": [],
        "failed_steps": [],
        "steps": steps,
        "outputs": {
            "report_path": compat.get("report_path"),
            "geojson_path": compat.get("geojson_path"),
            "overlay_path": compat.get("overlay_path"),
        },
        "report_path": compat.get("report_path"),
        "warnings": list(dict.fromkeys([*(compat.get("warnings") or []), *(detector_result.get("warnings") or [])])),
        "satellite_evidence": inputs.get("satellite_evidence"),
        "recommended_next_actions": [
            "Verify parcel and permit records.",
            "If needed, escalate to field inspection or legal review.",
        ],
        "limitations": list(dict.fromkeys([*(compat.get("limitations") or DEFAULT_LIMITATIONS), *(detector_result.get("limitations") or [])])),
    }
    result.update(write_workflow_report(result, inputs.get("workflow_output_root")))
    return result


def run_workflow(
    *,
    workflow_id: str,
    user_request: str = "",
    inputs: dict[str, Any] | None = None,
    mode: str = "safe_run",
    require_approval: bool = False,
) -> dict[str, Any]:
    del require_approval
    inputs = _resolve_satellite_inputs(workflow_id, dict(inputs or {}), mode)
    spec_result = get_execution_spec(workflow_id)
    if not spec_result.get("success"):
        return spec_result

    spec = dict(spec_result["workflow"])
    missing_inputs = _missing_required_inputs(spec, inputs)
    if mode == "dry_run":
        steps = [
            _step_result(
                step,
                status="success",
                evidence={"planned": True, "external_service": step.get("external_service"), "fallback": step.get("fallback")},
                limitations=DEFAULT_LIMITATIONS,
            )
            for step in spec.get("steps") or []
        ]
        return {
            "success": True,
            "workflow_id": workflow_id,
            "title": spec.get("title"),
            "status": "success",
            "mode": mode,
            "user_request": user_request,
            "inputs": inputs,
            "plan": spec.get("steps") or [],
            "missing_inputs": missing_inputs,
            "approval_required_steps": [step.get("step_id") for step in spec.get("steps") or [] if step.get("approval_required")],
            "completed_steps": [step["step_id"] for step in steps],
            "degraded_steps": [],
            "failed_steps": [],
            "steps": steps,
            "outputs": {},
            "warnings": [],
            "satellite_evidence": inputs.get("satellite_evidence"),
            "recommended_next_actions": ["Provide any missing inputs, then run safe_run for preliminary evidence gathering."],
            "limitations": list(DEFAULT_LIMITATIONS),
        }

    if workflow_id == "WF-001":
        if _wf001_real_detector_enabled(inputs):
            return _run_wf001_real_detector(user_request, inputs, spec, mode)

        compat = _run_wf001_compat(user_request, inputs)
        steps = []
        for step in spec.get("steps") or []:
            op = str(step.get("operation") or "")
            if op == "run_preliminary_case_check":
                evidence = compat
                status = "success" if compat.get("success") else "degraded"
            else:
                evidence = {"message": "Step satisfied by compatible WF-001 preliminary workflow run."}
                status = "success"
            steps.append(_step_result(step, status=status, evidence=evidence, limitations=list(DEFAULT_LIMITATIONS)))
        result = {
            "success": bool(compat.get("success")),
            "workflow_id": workflow_id,
            "title": spec.get("title"),
            "status": "success" if compat.get("success") else "degraded",
            "mode": mode,
            "user_request": user_request,
            "inputs": inputs,
            "completed_steps": [step["step_id"] for step in steps if step["status"] == "success"],
            "degraded_steps": [step["step_id"] for step in steps if step["status"] == "degraded"],
            "approval_required_steps": [step["step_id"] for step in steps if step["status"] == "approval_required"],
            "failed_steps": [step["step_id"] for step in steps if step["status"] == "failed"],
            "steps": steps,
            "outputs": {
                "report_path": compat.get("report_path"),
                "geojson_path": compat.get("geojson_path"),
                "overlay_path": compat.get("overlay_path"),
            },
            "report_path": compat.get("report_path"),
            "warnings": list(compat.get("warnings") or []),
            "satellite_evidence": inputs.get("satellite_evidence"),
            "recommended_next_actions": [
                "Verify parcel and permit records.",
                "If needed, escalate to field inspection or legal review.",
            ],
            "limitations": list(compat.get("limitations") or DEFAULT_LIMITATIONS),
        }
        result.update(write_workflow_report(result, inputs.get("workflow_output_root")))
        return result

    step_results = [_execute_step(step, workflow_id, user_request, inputs, mode) for step in (spec.get("steps") or [])]
    warnings = _summarize_warnings(step_results)
    degraded_steps = [step["step_id"] for step in step_results if step["status"] == "degraded"]
    approval_required_steps = [step["step_id"] for step in step_results if step["status"] == "approval_required"]
    failed_steps = [step["step_id"] for step in step_results if step["status"] == "failed"]
    result = {
        "success": not failed_steps,
        "workflow_id": workflow_id,
        "title": spec.get("title"),
        "status": "degraded" if degraded_steps else ("approval_required" if approval_required_steps else "success"),
        "mode": mode,
        "user_request": user_request,
        "inputs": inputs,
        "completed_steps": [step["step_id"] for step in step_results if step["status"] == "success"],
        "degraded_steps": degraded_steps,
        "approval_required_steps": approval_required_steps,
        "failed_steps": failed_steps,
        "steps": step_results,
        "outputs": {},
        "warnings": warnings,
        "satellite_evidence": inputs.get("satellite_evidence"),
        "recommended_next_actions": [
            "Review degraded steps and supply missing imagery, AOI, or service configuration.",
            "Use approval flow before any high-risk external execution.",
        ],
        "limitations": list(DEFAULT_LIMITATIONS),
    }
    result.update(write_workflow_report(result, inputs.get("workflow_output_root")))
    return result


def eval_all_workflows(mode: str = "dry_run") -> dict[str, Any]:
    listed = list_workflows()
    if not listed.get("success"):
        return listed
    results = []
    for item in listed.get("workflows") or []:
        workflow_id = str(item.get("workflow_id") or "")
        inputs: dict[str, Any] = {}
        if workflow_id == "WF-001":
            inputs = {
                "image_case_id": "sample_taichung_case",
                "require_satellite": False,
                "use_llm": False,
                "output_dir": str(Path("outputs") / "geo_expert" / "plugin_direct_test"),
            }
        results.append(run_workflow(workflow_id=workflow_id, user_request=str(item.get("title") or workflow_id), inputs=inputs, mode=mode))
    return {
        "success": True,
        "mode": mode,
        "count": len(results),
        "results": results,
        "service_coverage": _summarize_service_coverage(results),
    }
