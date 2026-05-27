from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def workflow_output_dir(base_dir: str | Path | None, workflow_id: str) -> Path:
    root = Path(base_dir) if base_dir else Path("outputs") / "geo_expert" / "workflows"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return root / str(workflow_id) / timestamp


def write_workflow_report(result: dict[str, Any], base_dir: str | Path | None = None) -> dict[str, str]:
    workflow_id = str(result.get("workflow_id") or "unknown")
    out_dir = workflow_output_dir(base_dir, workflow_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    report_path = out_dir / "report.md"
    result_path = out_dir / "result.json"

    approval_required = result.get("approval_required_steps") or []
    workflow_warnings = result.get("warnings") or []
    lines = [
        f"# Workflow Report: {workflow_id}",
        "",
        f"- Title: {result.get('title', '')}",
        f"- User request: {result.get('user_request', '')}",
        f"- Mode: {result.get('mode', '')}",
        f"- Success: {result.get('success', False)}",
        "",
        "## Input Summary",
        "",
        f"- Inputs: {json.dumps(result.get('inputs', {}), ensure_ascii=False)}",
        "",
    ]
    satellite = dict(result.get("satellite_evidence") or {})
    lines.extend(["## Satellite / EO Source", ""])
    if satellite:
        lines.extend(
            [
                f"- Source: {satellite.get('source') or satellite.get('provider') or 'unknown'}",
                f"- AOI match quality: {satellite.get('match_strategy') or 'unknown'}",
                f"- Match confidence: {satellite.get('confidence', 'n/a')}",
                f"- Image path: {satellite.get('image_path') or 'none'}",
                f"- Fetched or cached: {'fetched' if satellite.get('service') == 'gee_preview' else 'cached/local'}",
                "- Not formal satellite analysis: true",
                f"- Warnings: {', '.join(str(item) for item in (satellite.get('warnings') or [])) or 'None'}",
                "",
            ]
        )
    else:
        lines.extend(["- None", ""])
    lines.extend(["## Steps", ""])
    for step in result.get("steps", []):
        lines.extend(
            [
                f"### {step.get('step_id', 'unknown')}",
                "",
                f"- Adapter: {step.get('adapter', '')}",
                f"- Operation: {step.get('operation', '')}",
                f"- Status: {step.get('status', '')}",
                f"- Used real service: {step.get('used_real_service', False)}",
            ]
        )
        step_warnings = step.get("warnings") or []
        limitations = step.get("limitations") or []
        if step_warnings:
            lines.append(f"- Warnings: {', '.join(str(item) for item in step_warnings)}")
        if limitations:
            lines.append(f"- Limitations: {', '.join(str(item) for item in limitations)}")
        if step.get("error"):
            lines.append(f"- Error: {step['error']}")
        lines.append("")

    lines.extend(["## Evidence Summary", ""])
    for step in result.get("steps", []):
        evidence = step.get("evidence") or {}
        if evidence:
            lines.append(f"- {step.get('step_id')}: {json.dumps(evidence, ensure_ascii=False)[:500]}")
    lines.append("")

    lines.extend(["## Citations / RAG References", ""])
    citation_found = False
    for step in result.get("steps", []):
        evidence = step.get("evidence") or {}
        for item in evidence.get("results") or []:
            citation = item.get("citation") or item.get("source")
            if citation:
                citation_found = True
                lines.append(f"- {step.get('step_id')}: {citation}")
    if not citation_found:
        lines.append("- None")
    lines.append("")

    lines.extend(["## Approval-required Steps", ""])
    if approval_required:
        for item in approval_required:
            lines.append(f"- {item}")
    else:
        lines.append("- None")
    lines.append("")

    lines.extend(["## Warnings", ""])
    if workflow_warnings:
        for item in workflow_warnings:
            lines.append(f"- {item}")
    else:
        lines.append("- None")
    lines.append("")

    real_steps = [step.get("step_id") for step in result.get("steps", []) if step.get("used_real_service")]
    degraded_steps = [step.get("step_id") for step in result.get("steps", []) if step.get("status") == "degraded"]
    lines.extend(["## Real Service Coverage", ""])
    lines.append(f"- Real-service steps: {', '.join(str(item) for item in real_steps) if real_steps else 'None'}")
    lines.append(f"- Degraded steps: {', '.join(str(item) for item in degraded_steps) if degraded_steps else 'None'}")
    lines.append("")

    lines.extend(["## Limitations", ""])
    for item in result.get("limitations") or []:
        lines.append(f"- {item}")
    legal_grounding = dict(result.get("legal_grounding") or {})
    if legal_grounding:
        lines.extend(["", "## Legal Basis", ""])
        for item in legal_grounding.get("citations") or []:
            lines.append(f"- {item.get('law_name') or item.get('title')}: {item.get('citation') or item.get('article_no')}")
        lines.extend(["", "## Applicability Checklist", ""])
        for item in legal_grounding.get("applicability_checklist") or []:
            lines.append(f"- Issue: {item.get('issue')} | Applicability: {item.get('applicability')} | Missing facts: {', '.join(item.get('facts_missing') or []) or 'None'}")
        lines.extend(["", "## Human Review Required", "", "- True", "", "## Formality Level", ""])
        lines.extend(["- preliminary_screening", "- expert_review_draft", "- not_official_decision"])
    detector_sections = []
    for step in result.get("steps", []):
        evidence = step.get("evidence") or {}
        if evidence.get("model_scope") or evidence.get("detection_limitations"):
            detector_sections.append(evidence)
    if detector_sections:
        lines.extend(["", "## Detection Limitations", ""])
        for evidence in detector_sections:
            lines.append(f"- Model scope: {evidence.get('model_scope')}")
            lines.append(f"- Domain specific: {evidence.get('domain_specific')}")
            for item in evidence.get("detection_limitations") or []:
                lines.append(f"- {item}")
    spatial_capability = dict(result.get("spatial_capability") or {})
    if spatial_capability:
        lines.extend(["", "## Spatial Capability", ""])
        lines.append(f"- Available layers: {', '.join(spatial_capability.get('available_layers') or ['None'])}")
        lines.append(f"- Missing layers: {', '.join(spatial_capability.get('missing_layers') or ['None'])}")
        lines.append(f"- Required data for full analysis: {', '.join(spatial_capability.get('required_data') or ['None'])}")
    if result.get("production_readiness"):
        readiness = dict(result.get("production_readiness") or {})
        lines.extend(["", "## Production Readiness", ""])
        lines.append(f"- Readiness level: {readiness.get('readiness_level')}")
        lines.append(f"- Score: {readiness.get('score')}")
        for item in readiness.get("blocking_gaps") or []:
            lines.append(f"- Blocking gap: {item}")
        for item in readiness.get("non_blocking_gaps") or []:
            lines.append(f"- Non-blocking gap: {item}")
    if result.get("run_manifest"):
        manifest = dict(result.get("run_manifest") or {})
        lines.extend(["", "## Data Provenance", ""])
        for item in manifest.get("data_sources") or []:
            lines.append(f"- {json.dumps(item, ensure_ascii=False)}")
        lines.extend(["", "## Approval Required Actions", ""])
        for item in result.get("approval_required_actions") or manifest.get("approval_required") or ["None"]:
            lines.append(f"- {item}")
        lines.extend(["", "## Reproducibility Manifest", ""])
        lines.append(f"- Run ID: {manifest.get('run_id')}")
        lines.append(f"- Services used: {json.dumps(manifest.get('services_used') or {}, ensure_ascii=False)}")
    if result.get("openeo_acquisition"):
        lines.extend(["", "## GeoTIFF Acquisition", ""])
        lines.append("- GeoTIFF acquisition requires explicit approval.")
        lines.append(f"- Acquisition mode: {result.get('openeo_acquisition', {}).get('mode')}")
    if result.get("service_coverage"):
        coverage = result.get("service_coverage") or {}
        lines.extend(["", "## Service Coverage", ""])
        lines.append(f"- Overall real service score: {coverage.get('overall_real_service_score', 'n/a')}")
        lines.append(f"- Readiness level: {coverage.get('readiness_level', 'n/a')}")
        for item in coverage.get("blockers") or []:
            lines.append(f"- Blocker: {item}")
        for item in coverage.get("next_actions") or []:
            lines.append(f"- Next action: {item}")
        lines.extend(["", "## Remaining Data Gaps", ""])
        for item in coverage.get("postgis", {}).get("layer_coverage", {}).get("missing_aliases", []) or ["None"]:
            lines.append(f"- {item}")
        lines.extend(["", "## Satellite AOI Match Quality", ""])
        sat_quality = coverage.get("satellite", {}).get("aoi_match_quality", {})
        lines.append(f"- Precise matches: {sat_quality.get('precise_count', 0)}")
        lines.append(f"- Fallback matches: {sat_quality.get('fallback_count', 0)}")
        lines.append(f"- Unknown metadata count: {sat_quality.get('unknown_metadata_count', 0)}")
        lines.extend(["", "## PostGIS Layer Coverage", ""])
        layer_cov = coverage.get("postgis", {}).get("layer_coverage", {})
        lines.append(f"- Resolved: {layer_cov.get('resolved', 0)}")
        lines.append(f"- Missing: {layer_cov.get('missing', 0)}")
        lines.append(f"- Missing aliases: {', '.join(str(item) for item in layer_cov.get('missing_aliases', []) or ['None'])}")
        lines.extend(["", "## RAG Embedding Quality Note", ""])
        for item in coverage.get("chromadb", {}).get("quality_note", []) or ["None"]:
            lines.append(f"- {item}")
        lines.extend(["", "## Detector Model Quality Note", ""])
        for item in coverage.get("detector", {}).get("quality_note", []) or ["None"]:
            lines.append(f"- {item}")
        lines.extend(["", "## Recommended Production Upgrade", ""])
        for item in coverage.get("next_actions") or ["Import missing spatial layers and replace deterministic embeddings for production use."]:
            lines.append(f"- {item}")
        if coverage.get("production_readiness"):
            prod = coverage.get("production_readiness") or {}
            lines.append(f"- Production readiness score: {prod.get('score')}")
    lines.extend(["", "## Disclaimer", "", "Not a formal legal conclusion.", "Not formal satellite analysis.", "", "## Next Recommended Actions", ""])
    for item in result.get("recommended_next_actions") or ["Verify field conditions, parcel status, and permit records before any enforcement or legal conclusion."]:
        lines.append(f"- {item}")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "output_dir": str(out_dir),
        "report_path": str(report_path),
        "result_path": str(result_path),
        "result_json_path": str(result_path),
    }
