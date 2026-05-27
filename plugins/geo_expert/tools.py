from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

from .adapters.eo_tools import eo_local_analysis, openeo_status, prepare_openeo_request
from .adapters.rag_tools import search_regulations as adapter_search_regulations
from .adapters.satellite_tools import acquire_satellite_preview
from .adapters.spatial_tools import spatial_query as adapter_spatial_query
from .adapters.workflow_tools import list_workflows, show_workflow
from .geo_database.case_report import build_case_report
from .geo_database.detection_overlay_preview_renderer import (
    render_detection_overlay_preview,
)
from .geo_database.image_provider_local import load_local_image_fixture
from .geo_database.image_recognition_detector import run_detector
from .geo_database.legal_database import search_legal_database as _search_legal_database
from .geo_database.sop_workflow import match_sop_candidates, retrieve_sop_candidates
from .openeo_acquisition import create_openeo_acquisition_plan, list_geotiff_cache, run_openeo_acquisition
from .production import calculate_readiness_score, check_service_health, create_run_manifest, list_cache_policy_entries
from .workflow_runner import eval_all_workflows, run_workflow


PLUGIN_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = Path("outputs") / "geo_expert" / "latest"
DEFAULT_FIXTURES_ROOT = PLUGIN_ROOT / "data" / "geo_fixtures"
DEFAULT_AOI = {
    "west": 120.70,
    "south": 23.45,
    "east": 120.72,
    "north": 23.47,
}
DEFAULT_LIMITATIONS = [
    "Preliminary only.",
    "Requires verification.",
    "Not a formal legal conclusion.",
    "No OpenEO real submit performed.",
    "No GeoTIFF/export/download performed.",
]


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _as_output_dir(value: str | None) -> Path:
    return Path(value) if value else DEFAULT_OUTPUT_DIR


def _normalize_aoi(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    try:
        west = float(value["west"])
        south = float(value["south"])
        east = float(value["east"])
        north = float(value["north"])
    except Exception:
        return None
    if west >= east or south >= north:
        return None
    return {
        "west": west,
        "south": south,
        "east": east,
        "north": north,
    }


def _write_geojson(path: Path, geojson: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")


def _resolve_image_inputs(args: dict[str, Any]) -> tuple[str | None, dict[str, float], dict[str, Any], list[str]]:
    warnings: list[str] = []
    image_case_id = str(args.get("image_case_id") or "").strip()
    direct_image_path = str(args.get("image_path") or "").strip()
    direct_image_aoi = _normalize_aoi(args.get("image_aoi")) or _normalize_aoi(args.get("aoi"))

    if image_case_id:
        fixture = load_local_image_fixture(image_case_id, fixtures_root=str(DEFAULT_FIXTURES_ROOT))
        if fixture.get("success"):
            image_path = str(fixture.get("image_path"))
            aoi = fixture.get("aoi") or dict(DEFAULT_AOI)
            image_background = {
                "source": "local_fixture",
                "case_id": image_case_id,
                "path": image_path,
                "is_geotiff": False,
                "is_export": False,
                "is_formal_analysis": False,
            }
            return image_path, aoi, image_background, warnings
        warnings.append(str(fixture.get("error") or "fixture_not_found"))

    if direct_image_path:
        image_path = str(Path(direct_image_path).resolve())
        if Path(image_path).exists() and direct_image_aoi:
            image_background = {
                "source": "local_image",
                "path": image_path,
                "is_geotiff": False,
                "is_export": False,
                "is_formal_analysis": False,
            }
            return image_path, direct_image_aoi, image_background, warnings
        if not Path(image_path).exists():
            warnings.append("direct_image_missing")
        if direct_image_aoi is None:
            warnings.append("direct_image_aoi_invalid")

    require_satellite = bool(args.get("require_satellite"))
    if require_satellite:
        return None, dict(DEFAULT_AOI), {"source": "unavailable"}, warnings

    image_background = {
        "source": "placeholder",
        "is_geotiff": False,
        "is_export": False,
        "is_formal_analysis": False,
    }
    return None, dict(DEFAULT_AOI), image_background, warnings


def _render_overlay_preview(
    *,
    geojson_path: Path,
    overlay_path: Path,
    background_image_path: str | None,
    overlay_aoi: dict[str, Any] | None,
) -> dict[str, Any]:
    params = inspect.signature(render_detection_overlay_preview).parameters
    names = set(params.keys())
    base_kwargs: dict[str, Any] = {}

    if "output_path" in names:
        base_kwargs["output_path"] = str(overlay_path)
    elif "overlay_path" in names:
        base_kwargs["overlay_path"] = str(overlay_path)

    if "background_image_path" in names:
        base_kwargs["background_image_path"] = background_image_path
    elif "background_path" in names:
        base_kwargs["background_path"] = background_image_path

    if "overlay_aoi" in names:
        base_kwargs["overlay_aoi"] = overlay_aoi
    elif "aoi" in names:
        base_kwargs["aoi"] = overlay_aoi

    if "detections_geojson_path" in names:
        return render_detection_overlay_preview(
            detections_geojson_path=str(geojson_path),
            **base_kwargs,
        )
    if "detection_geojson_path" in names:
        return render_detection_overlay_preview(
            detection_geojson_path=str(geojson_path),
            **base_kwargs,
        )
    if "geojson_path" in names:
        return render_detection_overlay_preview(
            geojson_path=str(geojson_path),
            **base_kwargs,
        )
    if "detections_path" in names:
        return render_detection_overlay_preview(
            detections_path=str(geojson_path),
            **base_kwargs,
        )
    if "detections_geojson" in names:
        detections_geojson = json.loads(geojson_path.read_text(encoding="utf-8"))
        return render_detection_overlay_preview(detections_geojson=detections_geojson, **base_kwargs)
    if "geojson" in names:
        detections_geojson = json.loads(geojson_path.read_text(encoding="utf-8"))
        return render_detection_overlay_preview(geojson=detections_geojson, **base_kwargs)

    try:
        return render_detection_overlay_preview(
            str(geojson_path),
            str(overlay_path),
            background_image_path,
            overlay_aoi,
        )
    except TypeError:
        return render_detection_overlay_preview(str(geojson_path), str(overlay_path))


def _normalize_sop_candidates(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    if isinstance(raw, dict):
        for key in ("sop_candidates", "candidates", "results", "items", "sops"):
            value = raw.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        if raw.get("sop_id") or raw.get("workflow_id") or raw.get("title"):
            return [raw]
        return []
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def _fallback_sop_candidates() -> list[dict[str, Any]]:
    return [
        {
            "sop_id": "WF-001",
            "workflow_id": "WF-001",
            "title": "農業區違章工廠盤查",
            "score": 0.5,
            "matched_terms": ["違章建築", "違章工廠", "農業區"],
        }
    ]


def _normalize_sop_match(raw: Any) -> dict[str, Any]:
    if raw is None:
        return _fallback_sop_candidates()[0]
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return _fallback_sop_candidates()[0]
    if isinstance(raw, list):
        return raw[0] if raw and isinstance(raw[0], dict) else _fallback_sop_candidates()[0]
    if isinstance(raw, dict):
        if isinstance(raw.get("selected_sop"), dict):
            selected = dict(raw["selected_sop"])
            selected.setdefault("selected_sop_title", raw.get("selected_sop_title"))
            return selected
        if raw.get("selected_sop") or raw.get("sop_id") or raw.get("workflow_id"):
            return raw
        for key in ("match", "selected", "best", "result"):
            value = raw.get(key)
            if isinstance(value, dict):
                return value
    return _fallback_sop_candidates()[0]


def _flatten_selected_sop(sop_match: dict[str, Any]) -> dict[str, Any]:
    flattened = dict(sop_match or {})
    selected = flattened.get("selected_sop")
    if isinstance(selected, dict):
        flattened.setdefault("sop_id", selected.get("sop_id") or selected.get("workflow_id"))
        flattened.setdefault("workflow_id", selected.get("workflow_id") or selected.get("sop_id"))
        flattened.setdefault("title", selected.get("title") or selected.get("selected_sop_title"))
    elif isinstance(selected, str):
        flattened.setdefault("sop_id", selected)
        flattened.setdefault("workflow_id", selected)
    flattened["selected_sop"] = _selected_sop_id(flattened)
    flattened["selected_sop_title"] = _selected_sop_title(flattened)
    return flattened


def _selected_sop_id(sop_match: dict[str, Any]) -> str:
    selected = sop_match.get("selected_sop")
    if isinstance(selected, dict):
        return selected.get("sop_id") or selected.get("workflow_id") or selected.get("id") or "WF-001"
    return str(
        selected
        or sop_match.get("sop_id")
        or sop_match.get("workflow_id")
        or "WF-001"
    )


def _selected_sop_title(sop_match: dict[str, Any]) -> str:
    selected = sop_match.get("selected_sop")
    if isinstance(selected, dict):
        return str(
            selected.get("title")
            or selected.get("selected_sop_title")
            or sop_match.get("selected_sop_title")
            or sop_match.get("title")
            or "農業區違章工廠盤查"
        )
    return str(
        sop_match.get("selected_sop_title")
        or sop_match.get("title")
        or "農業區違章工廠盤查"
    )


def _build_case_report_compat(
    *,
    user_request: str,
    selected_sop: dict[str, Any],
    recognition_result: dict[str, Any],
    legal_context: dict[str, Any],
    report_path: Path,
) -> dict[str, Any]:
    fallback_error = None
    params = inspect.signature(build_case_report).parameters
    names = set(params.keys())
    compiled_plan = {
        "workflow_id": _selected_sop_id(selected_sop),
        "title": _selected_sop_title(selected_sop),
        "steps": [
            {
                "step_id": "local_fixture_image",
                "status": "completed",
                "description": "Load local fixture image source.",
            },
            {
                "step_id": "preliminary_detection",
                "status": "completed",
                "description": "Run preliminary deterministic detector.",
            },
            {
                "step_id": "overlay_preview",
                "status": "completed",
                "description": "Generate overlay preview.",
            },
            {
                "step_id": "case_report",
                "status": "completed",
                "description": "Generate preliminary case report.",
            },
        ],
        "safety": {
            "preliminary_only": True,
            "formal_legal_conclusion": False,
            "openeo_submit": False,
            "geotiff_download": False,
            "export": False,
        },
    }

    candidate_kwargs: dict[str, Any] = {}
    if "selected_sop" in names:
        candidate_kwargs["selected_sop"] = selected_sop
    if "recognition_result" in names:
        candidate_kwargs["recognition_result"] = recognition_result
    if "legal_answer" in names:
        candidate_kwargs["legal_answer"] = legal_context
    if "legal_context" in names:
        candidate_kwargs["legal_context"] = legal_context
    if "compiled_plan" in names:
        candidate_kwargs["compiled_plan"] = compiled_plan
    if "readonly_results" in names:
        candidate_kwargs["readonly_results"] = {
            "success": True,
            "summary": {"status": "read_only_complete"},
            "warnings": [],
            "limitations": DEFAULT_LIMITATIONS,
        }
    if "limitations" in names:
        candidate_kwargs["limitations"] = list(DEFAULT_LIMITATIONS)
    if "missing_inputs" in names:
        candidate_kwargs["missing_inputs"] = []

    try:
        result = build_case_report(**candidate_kwargs)
        if isinstance(result, dict):
            report_text = _report_markdown_from_payload(user_request, selected_sop, recognition_result, result)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report_text, encoding="utf-8")
            result.setdefault("report_path", str(report_path))
            return result
        if isinstance(result, str):
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(result, encoding="utf-8")
            return {"success": True, "report_path": str(report_path), "method": "case_report_string"}
    except Exception as exc:
        fallback_error = str(exc)

    report_text = _report_markdown_from_payload(
        user_request,
        selected_sop,
        recognition_result,
        {"limitations": DEFAULT_LIMITATIONS, "fallback_error": fallback_error},
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    return {
        "success": True,
        "report_path": str(report_path),
        "method": "deterministic_fallback",
        "fallback_used": True,
        "error": fallback_error,
        "compiled_plan": compiled_plan,
    }


def _report_markdown_from_payload(
    user_request: str,
    selected_sop: dict[str, Any],
    recognition_result: dict[str, Any],
    report_payload: dict[str, Any],
) -> str:
    detection_count = (
        recognition_result.get("overlay_summary", {}).get("detection_count")
        or len(recognition_result.get("detections") or [])
    )
    lines = [
        "# Geo Expert Preliminary Report",
        "",
        "## User Request",
        "",
        user_request or "(none)",
        "",
        "## Selected SOP",
        "",
        f"- SOP: {_selected_sop_id(selected_sop)}",
        f"- Title: {_selected_sop_title(selected_sop)}",
        "",
        "## Preliminary Detection Summary",
        "",
        f"- Detector: {recognition_result.get('detector_used', 'mock')}",
        f"- Detection count: {detection_count}",
        f"- Fallback used: {recognition_result.get('fallback_used', False)}",
        "",
        "## Limitations",
        "",
    ]
    for item in report_payload.get("limitations") or DEFAULT_LIMITATIONS:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Legal Context",
            "",
            "This report is preliminary only and is not a formal legal conclusion.",
        ]
    )
    if report_payload.get("fallback_error"):
        lines.extend(["", "## Report Builder Fallback Note", "", str(report_payload["fallback_error"])])
    return "\n".join(lines) + "\n"


def run_preliminary_case_check_handler(args: dict, **_kwargs) -> str:
    user_request = str(args.get("user_request") or "")
    output_dir = _as_output_dir(args.get("output_dir"))
    output_dir.mkdir(parents=True, exist_ok=True)

    image_path, aoi, image_background, input_warnings = _resolve_image_inputs(args)
    if bool(args.get("require_satellite")) and image_background.get("source") == "unavailable":
        return _json(
            {
                "success": False,
                "error": "satellite_thumbnail_required_but_unavailable",
                "warnings": input_warnings + ["No satellite thumbnail available in plugin local fallback mode."],
            }
        )

    raw_sop_candidates = retrieve_sop_candidates(user_request)
    sop_candidates = _normalize_sop_candidates(raw_sop_candidates) or _fallback_sop_candidates()
    raw_sop_match = match_sop_candidates(user_request, sop_candidates)
    sop_match = _flatten_selected_sop(_normalize_sop_match(raw_sop_match))

    recognition = run_detector(
        {
            "task": "illegal_building_preliminary_check",
            "sop_id": _selected_sop_id(sop_match),
            "image_source": image_background["source"],
            "local_image_path": image_path,
            "aoi": aoi,
            "mode": "mock",
        }
    )

    geojson_path = output_dir / "detections.geojson"
    overlay_path = output_dir / "overlay_preview.png"
    report_path = output_dir / "report.md"
    geojson = recognition.get("geojson") or {"type": "FeatureCollection", "features": []}
    _write_geojson(geojson_path, geojson)

    overlay_result = _render_overlay_preview(
        geojson_path=geojson_path,
        overlay_path=overlay_path,
        background_image_path=image_path,
        overlay_aoi=aoi,
    )
    legal_context = {
        "success": True,
        "results": [],
        "citations": [],
        "limitations": ["Preliminary only.", "Not formal legal advice."],
    }
    report = _build_case_report_compat(
        user_request=user_request,
        selected_sop=sop_match,
        recognition_result=recognition,
        legal_context=legal_context,
        report_path=report_path,
    )

    warnings = list(dict.fromkeys(input_warnings + recognition.get("warnings", []) + overlay_result.get("warnings", [])))
    return _json(
        {
            "success": True,
            "selected_sop": _selected_sop_id(sop_match),
            "selected_sop_title": _selected_sop_title(sop_match),
            "detector_used": recognition.get("detector_used", "mock"),
            "fallback_used": recognition.get("fallback_used", False),
            "detection_count": recognition.get("overlay_summary", {}).get("detection_count", 0),
            "report_path": str(report_path),
            "geojson_path": str(geojson_path),
            "overlay_path": str(overlay_path),
            "image_background": image_background,
            "aoi_used_for_image": aoi,
            "aoi_used_for_detection": aoi,
            "aoi_used_for_overlay": aoi,
            "aoi_consistent": True,
            "warnings": warnings,
            "limitations": list(DEFAULT_LIMITATIONS),
            "approval_items": [],
            "report": report,
        }
    )


def search_sop_database_handler(args: dict, **_kwargs) -> str:
    query = str(args.get("query") or "")
    limit = int(args.get("limit", 5))
    raw_results = retrieve_sop_candidates(query)
    results = _normalize_sop_candidates(raw_results)[:limit]
    if not results:
        results = _fallback_sop_candidates()[:limit]
    for item in results:
        item.setdefault("selected_sop_title", item.get("title"))
    return _json({"success": True, "results": results})


def search_legal_database_handler(args: dict, **_kwargs) -> str:
    query = str(args.get("query") or "")
    limit = int(args.get("limit", 5))
    return _json(_search_legal_database(query=query, limit=limit))


def preview_satellite_overlay_handler(args: dict, **_kwargs) -> str:
    output_dir = _as_output_dir(args.get("output_dir"))
    output_dir.mkdir(parents=True, exist_ok=True)

    image_path, aoi, image_background, input_warnings = _resolve_image_inputs(args)
    if bool(args.get("require_satellite")) and image_background.get("source") == "unavailable":
        return _json(
            {
                "success": False,
                "error": "satellite_thumbnail_required_but_unavailable",
                "warnings": input_warnings + ["No satellite thumbnail available in plugin local fallback mode."],
            }
        )

    recognition = run_detector(
        {
            "image_source": image_background["source"],
            "local_image_path": image_path,
            "aoi": aoi,
            "mode": "mock",
        }
    )
    geojson_path = output_dir / "detections.geojson"
    overlay_path = output_dir / "overlay_preview.png"
    _write_geojson(geojson_path, recognition.get("geojson") or {"type": "FeatureCollection", "features": []})
    overlay_result = _render_overlay_preview(
        geojson_path=geojson_path,
        overlay_path=overlay_path,
        background_image_path=image_path,
        overlay_aoi=aoi,
    )

    warnings = list(dict.fromkeys(input_warnings + recognition.get("warnings", []) + overlay_result.get("warnings", [])))
    return _json(
        {
            "success": True,
            "geojson_path": str(geojson_path),
            "overlay_path": str(overlay_path),
            "image_background": image_background,
            "aoi_used_for_image": aoi,
            "aoi_used_for_detection": aoi,
            "aoi_used_for_overlay": aoi,
            "aoi_consistent": True,
            "warnings": warnings,
            "limitations": list(DEFAULT_LIMITATIONS),
        }
    )


def satellite_acquire_preview_handler(args: dict, **_kwargs) -> str:
    return _json(
        acquire_satellite_preview(
            aoi=args.get("aoi"),
            bbox=args.get("bbox"),
            case_id=str(args.get("case_id") or ""),
            workflow_id=str(args.get("workflow_id") or ""),
            mode=str(args.get("mode") or "prepare_only"),
            provider=str(args.get("provider") or ""),
            time_range=list(args.get("time_range") or []),
        )
    )


def open_last_outputs_handler(args: dict, **_kwargs) -> str:
    output_dir = _as_output_dir(args.get("output_dir"))
    return _json(
        {
            "success": True,
            "latest_dir": str(output_dir),
            "report_path": str(output_dir / "report.md"),
            "geojson_path": str(output_dir / "detections.geojson"),
            "overlay_path": str(output_dir / "overlay_preview.png"),
            "thumbnail_path": None,
        }
    )


def handle_approval_handler(args: dict, **_kwargs) -> str:
    return _json(
        {
            "success": True,
            "recorded": True,
            "approval_id": args.get("approval_id"),
            "decision": args.get("decision"),
            "executed_high_risk_action": False,
            "message": "Decision recorded. No high-risk action was executed.",
        }
    )


def workflow_list_handler(args: dict, **_kwargs) -> str:
    return _json(list_workflows())


def workflow_show_handler(args: dict, **_kwargs) -> str:
    return _json(show_workflow(str(args.get("workflow_id") or "")))


def rag_search_regulations_handler(args: dict, **_kwargs) -> str:
    query = str(args.get("query") or "")
    top_k = int(args.get("top_k", 5))
    source_filter = args.get("source_filter")
    return _json(adapter_search_regulations(query, source_filter=source_filter, top_k=top_k))


def spatial_query_handler(args: dict, **_kwargs) -> str:
    operation = str(args.get("operation") or "")
    parameters = args.get("parameters") or {}
    return _json(adapter_spatial_query(operation, parameters))


def eo_local_analysis_handler(args: dict, **_kwargs) -> str:
    operation = str(args.get("operation") or "")
    parameters = args.get("parameters") or {}
    return _json(eo_local_analysis(operation, parameters))


def eo_openeo_status_handler(args: dict, **_kwargs) -> str:
    return _json(openeo_status())


def eo_openeo_prepare_handler(args: dict, **_kwargs) -> str:
    operation = str(args.get("operation") or "")
    parameters = args.get("parameters") or {}
    return _json(prepare_openeo_request(operation, parameters))


def _fallback_sop_candidates() -> list[dict[str, Any]]:
    return [
        {
            "sop_id": "WF-001",
            "workflow_id": "WF-001",
            "title": "農業區違章工廠盤查",
            "score": 0.5,
            "matched_terms": ["違章建築", "違章工廠", "農業區"],
        }
    ]


def _selected_sop_title(sop_match: dict[str, Any]) -> str:
    selected = sop_match.get("selected_sop")
    if isinstance(selected, dict):
        title = (
            selected.get("title")
            or selected.get("selected_sop_title")
            or sop_match.get("selected_sop_title")
            or sop_match.get("title")
            or "農業區違章工廠盤查"
        )
    else:
        title = (
            sop_match.get("selected_sop_title")
            or sop_match.get("title")
            or "農業區違章工廠盤查"
        )
    if _selected_sop_id(sop_match) == "WF-001":
        return "農業區違章工廠盤查"
    return str(title)


def workflow_dry_run_handler(args: dict, **_kwargs) -> str:
    return _json(
        run_workflow(
            workflow_id=str(args.get("workflow_id") or ""),
            user_request=str(args.get("user_request") or ""),
            inputs=dict(args.get("inputs") or {}),
            mode="dry_run",
            require_approval=bool(args.get("require_approval", False)),
        )
    )


def workflow_run_handler(args: dict, **_kwargs) -> str:
    return _json(
        run_workflow(
            workflow_id=str(args.get("workflow_id") or ""),
            user_request=str(args.get("user_request") or ""),
            inputs=dict(args.get("inputs") or {}),
            mode=str(args.get("mode") or "safe_run"),
            require_approval=bool(args.get("require_approval", False)),
        )
    )


def workflow_eval_all_handler(args: dict, **_kwargs) -> str:
    return _json(eval_all_workflows(mode=str(args.get("mode") or "dry_run")))


def _fallback_sop_candidates() -> list[dict[str, Any]]:
    return [
        {
            "sop_id": "WF-001",
            "workflow_id": "WF-001",
            "title": "農業區違章工廠盤查",
            "score": 0.5,
            "matched_terms": ["違章建築", "違章工廠", "農業區"],
        }
    ]


def _selected_sop_title(sop_match: dict[str, Any]) -> str:
    selected = sop_match.get("selected_sop")
    if isinstance(selected, dict):
        title = (
            selected.get("title")
            or selected.get("selected_sop_title")
            or sop_match.get("selected_sop_title")
            or sop_match.get("title")
            or "農業區違章工廠盤查"
        )
    else:
        title = (
            sop_match.get("selected_sop_title")
            or sop_match.get("title")
            or "農業區違章工廠盤查"
        )
    if _selected_sop_id(sop_match) == "WF-001":
        return "農業區違章工廠盤查"
    return str(title)


def search_sop_database_handler(args: dict, **_kwargs) -> str:
    from .adapters.workflow_tools import route_workflow

    query = str(args.get("query") or "")
    limit = int(args.get("limit", 5))
    routed = route_workflow(query, limit=limit)
    results = [
        {
            "workflow_id": item.get("workflow_id"),
            "sop_id": item.get("workflow_id"),
            "title": item.get("title"),
            "selected_sop_title": item.get("title"),
            "score": item.get("score"),
            "matched_terms": item.get("matched_terms") or [],
            "reason": item.get("reason"),
        }
        for item in (routed.get("candidates") or [])
    ]
    if not results:
        raw_results = retrieve_sop_candidates(query)
        results = _normalize_sop_candidates(raw_results)[:limit]
        if not results:
            results = _fallback_sop_candidates()[:limit]
        for item in results:
            item.setdefault("selected_sop_title", item.get("title"))
    return _json({"success": True, "results": results, "needs_clarification": routed.get("needs_clarification", False)})


def workflow_route_handler(args: dict, **_kwargs) -> str:
    from .adapters.workflow_tools import route_workflow

    return _json(route_workflow(str(args.get("query") or ""), limit=int(args.get("limit", 5))))


def case_plan_handler(args: dict, **_kwargs) -> str:
    from .workflow_collaboration import plan_case_workflow

    return _json(plan_case_workflow(str(args.get("user_request") or ""), inputs=dict(args.get("inputs") or {})))


def case_run_handler(args: dict, **_kwargs) -> str:
    from .workflow_collaboration import execute_case_workflow_plan, plan_case_workflow

    user_request = str(args.get("user_request") or "")
    inputs = dict(args.get("inputs") or {})
    mode = str(args.get("mode") or "safe_run")
    plan = plan_case_workflow(user_request, inputs=inputs)
    result = execute_case_workflow_plan(plan, mode=mode, inputs=inputs)
    result["case_plan"] = plan
    return _json(result)


def pack_list_handler(args: dict, **_kwargs) -> str:
    from .satellite_workflows.pack_registry import list_packs

    return _json(list_packs())


def pack_show_handler(args: dict, **_kwargs) -> str:
    from .satellite_workflows.pack_registry import load_pack

    return _json(load_pack(str(args.get("pack_id") or "")))


def pack_run_handler(args: dict, **_kwargs) -> str:
    from .satellite_workflows.pack_runner import run_pack

    return _json(
        run_pack(
            str(args.get("pack_id") or ""),
            str(args.get("user_request") or ""),
            inputs=dict(args.get("inputs") or {}),
            mode=str(args.get("mode") or "safe_run"),
        )
    )


def user_data_import_handler(args: dict, **_kwargs) -> str:
    from .satellite_workflows.pack_registry import load_pack
    from .user_data.user_data_ingest import import_user_data

    loaded = load_pack(str(args.get("pack_id") or ""))
    if not loaded.get("success"):
        return _json(loaded)
    return _json(
        import_user_data(
            pack=dict(loaded["pack"]),
            source_files=[str(item) for item in list(args.get("source_files") or [])],
            embedding_backend=str(args.get("embedding_backend") or "hash"),
        )
    )


def user_data_list_handler(args: dict, **_kwargs) -> str:
    from .user_data.user_data_store import list_datasets

    pack_id = str(args.get("pack_id") or "").strip() or None
    datasets = list_datasets(pack_id)
    return _json({"success": True, "datasets": datasets, "count": len(datasets)})


def user_data_search_handler(args: dict, **_kwargs) -> str:
    from .user_data.user_data_rag import search_user_data

    return _json(
        search_user_data(
            str(args.get("pack_id") or ""),
            str(args.get("query") or ""),
            dataset_ids=[str(item) for item in list(args.get("dataset_ids") or [])],
            top_k=int(args.get("top_k", 5)),
        )
    )


def user_data_rag_answer_handler(args: dict, **_kwargs) -> str:
    from .user_data.user_data_rag import answer_user_data_question

    return _json(
        answer_user_data_question(
            str(args.get("pack_id") or ""),
            str(args.get("query") or ""),
            dataset_ids=[str(item) for item in list(args.get("dataset_ids") or [])],
            top_k=int(args.get("top_k", 3)),
        )
    )


def legal_audit_handler(args: dict, **_kwargs) -> str:
    from scripts.audit_geo_expert_legal_rag import audit_legal_rag

    return _json(audit_legal_rag())


def legal_applicability_check_handler(args: dict, **_kwargs) -> str:
    from .legal_grounding import build_applicability_check

    return _json(
        build_applicability_check(
            user_request=str(args.get("user_request") or ""),
            workflow_id=str(args.get("workflow_id") or ""),
            facts=dict(args.get("facts") or {}),
        )
    )


def spatial_capability_show_handler(args: dict, **_kwargs) -> str:
    from .adapters.spatial_tools import spatial_capability_profile

    return _json(spatial_capability_profile())


def production_readiness_show_handler(args: dict, **_kwargs) -> str:
    coverage = dict(args.get("service_coverage") or {})
    return _json(
        {
            "success": True,
            "production_readiness": calculate_readiness_score(coverage),
            "cache_policy": list_cache_policy_entries(),
        }
    )


def run_manifest_create_handler(args: dict, **_kwargs) -> str:
    return _json(create_run_manifest(dict(args.get("result") or {})))


def service_health_check_handler(args: dict, **_kwargs) -> str:
    return _json(check_service_health())


def openeo_acquisition_plan_handler(args: dict, **_kwargs) -> str:
    return _json(
        create_openeo_acquisition_plan(
            args.get("aoi"),
            dict(args.get("date_range") or {}),
            [str(item) for item in list(args.get("bands") or [])],
            int(args.get("resolution") or 10),
            output_format=str(args.get("output_format") or "GeoTIFF"),
        )
    )


def openeo_acquisition_run_handler(args: dict, **_kwargs) -> str:
    return _json(run_openeo_acquisition(dict(args)))


def geotiff_cache_list_handler(args: dict, **_kwargs) -> str:
    return _json(list_geotiff_cache())
