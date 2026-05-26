"""Deterministic planning and dry-run workflow logic for geo tasks."""

from __future__ import annotations

from copy import deepcopy

from .contracts import READ_ONLY_WORKFLOW_TOOLS, WORKFLOW_CONTRACTS
from .rag import answer_question
from .search import search_database


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _missing_inputs_from_task(task: str) -> list[str]:
    missing = []
    lowered = task.lower()
    if not any(token in lowered for token in ("aoi", "區域", "範圍", "地塊", "鄉鎮", "polygon", "bbox")):
        missing.append("aoi")
    if not any(token in lowered for token in ("time", "時間", "日期", "年", "月", "season", "range")):
        missing.append("time_range")
    if _contains_any(task, ("農地", "農業區", "landuse", "zoning", "土地使用", "分區")):
        if not any(token in lowered for token in ("landuse_layer", "zoning_layer", "土地使用圖", "分區圖", "landuse layer")):
            missing.append("landuse_layer")
    return missing


def generate_workflow_plan(task: str, db_path: str | None = None) -> dict:
    steps = []
    citations = []
    contracts = WORKFLOW_CONTRACTS

    def add_step(step_id: str, tool: str, name: str, risk: str = "low") -> None:
        contract = contracts[tool]
        steps.append(
            {
                "step_id": step_id,
                "name": name,
                "tool": tool,
                "required_inputs": list(contract["required_inputs"]),
                "outputs": list(contract["outputs"]),
                "risk": risk,
            }
        )

    add_step("step_1", "geo.input.collect", "collect_inputs")

    needs_openeo = _contains_any(task, ("Sentinel-2", "光學", "NDVI", "NDBI", "openEO", "sentinel"))
    if needs_openeo:
        add_step("step_2", "geo.openeo.select_collection", "select_collection")
        add_step("step_3", "geo.openeo.cloud_mask", "cloud_mask")
        add_step("step_4", "geo.openeo.compute_indices", "compute_indices")

    needs_factory_detection = _contains_any(task, ("工廠", "建物", "鐵皮", "built-up", "違章工廠", "違建工廠"))
    needs_landuse = _contains_any(task, ("農地", "農業區", "landuse", "zoning", "土地使用", "分區"))

    if needs_factory_detection or needs_landuse:
        add_step("step_5", "geo.eo.landcover_classify", "landcover_classify")
    if needs_landuse:
        add_step("step_6", "geo.gis.overlay_landuse", "overlay_landuse")
    if needs_factory_detection:
        add_step("step_7", "geo.analysis.rank_suspicious_sites", "rank_suspicious_sites")

    add_step("step_8", "geo.report.generate", "generate_report")

    if db_path:
        search_result = search_database(task, db_path, top_k=5)
        citations = [
            {
                "title": hit["title"],
                "path": hit["path"],
                "chunk_id": hit["chunk_id"],
                "source_type": hit["source_type"],
                "quote": hit["snippet"],
            }
            for hit in search_result["hits"][:3]
        ]

    return {
        "success": True,
        "task": task,
        "workflow_plan": {"steps": steps},
        "missing_inputs": _missing_inputs_from_task(task),
        "citations": citations,
        "planning_mode": "deterministic_rule_based",
        "execution_mode": "dry_run_only",
    }


def dry_run_workflow(task: str, workflow_plan: dict, provided_inputs: dict | None = None) -> dict:
    provided = dict(provided_inputs or {})
    steps = deepcopy((workflow_plan or {}).get("steps", []))
    available = set(provided)
    executable_steps = []
    blocked_steps = []
    missing_inputs = set()

    for step in steps:
        tool = step.get("tool")
        contract = WORKFLOW_CONTRACTS.get(tool)
        if contract is None:
            blocked_steps.append({"step_id": step.get("step_id"), "tool": tool, "reason": "unknown contract"})
            continue
        if tool not in READ_ONLY_WORKFLOW_TOOLS:
            blocked_steps.append({"step_id": step.get("step_id"), "tool": tool, "reason": "non read-only tool"})
            continue
        unmet = [name for name in contract["required_inputs"] if name not in available]
        if unmet:
            missing_inputs.update(unmet)
            blocked_steps.append({"step_id": step.get("step_id"), "tool": tool, "missing_inputs": unmet})
            continue
        executable_steps.append({"step_id": step.get("step_id"), "tool": tool, "status": "dry_runnable"})
        available.update(contract["outputs"])

    if task:
        missing_inputs.update(_missing_inputs_from_task(task))
    return {
        "success": True,
        "dry_run": {
            "status": "ready" if not blocked_steps else "needs_inputs",
            "missing_inputs": sorted(missing_inputs),
            "executable_steps": executable_steps,
            "blocked_steps": blocked_steps,
        },
    }


def run_workflow(task: str, db_path: str | None = None) -> dict:
    search_result = search_database(task, db_path, top_k=5)
    rag_result = answer_question(task, db_path, top_k=8)
    plan_result = generate_workflow_plan(task, db_path)
    dry_run_result = dry_run_workflow(task, plan_result["workflow_plan"], provided_inputs={})
    dry_run = dry_run_result["dry_run"]
    recommendation = (
        "Grounded facts come only from the cited local geo expert database chunks. "
        "The workflow plan is deterministic_rule_based inference, not real EO execution. "
        f"Missing inputs: {', '.join(dry_run['missing_inputs']) or 'none'}. "
        "You should provide AOI, time_range, and landuse inputs before any downstream implementation. "
        "No real OpenEO backend has been executed; current output is dry-run_only."
    )
    return {
        "success": True,
        "task": task,
        "search_hits": search_result["hits"],
        "rag_summary": rag_result["answer"],
        "workflow_plan": plan_result["workflow_plan"],
        "dry_run": dry_run,
        "missing_inputs": dry_run["missing_inputs"],
        "planning_mode": plan_result["planning_mode"],
        "execution_mode": plan_result["execution_mode"],
        "recommendation": recommendation,
        "citations": rag_result["citations"] or plan_result["citations"],
    }
