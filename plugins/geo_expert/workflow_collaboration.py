from __future__ import annotations

from typing import Any

from .adapters.workflow_tools import get_execution_spec, route_workflow
from .workflow_runner import run_workflow

DEFAULT_LIMITATIONS = [
    "Preliminary only.",
    "Requires verification.",
    "Not a formal legal conclusion.",
    "No OpenEO real submit performed.",
    "No GeoTIFF/export/download performed.",
]


def plan_case_workflow(user_request: str, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    inputs = dict(inputs or {})
    routed = route_workflow(user_request, limit=5)
    if not routed.get("success"):
        return routed
    selected_workflow_id = routed.get("selected_workflow_id")
    if not selected_workflow_id:
        return {
            "success": True,
            "user_request": user_request,
            "selected_workflow_id": None,
            "selected_workflow_title": None,
            "confidence": float(routed.get("confidence") or 0.0),
            "candidate_workflows": routed.get("candidates") or [],
            "missing_inputs": [],
            "execution_plan": [],
            "approval_required_steps": [],
            "safe_run_available": False,
            "recommended_next_actions": ["Clarify whether the case concerns agriculture, urban planning, river waste, hazard, or ecology."],
            "limitations": list(DEFAULT_LIMITATIONS),
            "needs_clarification": True,
        }
    spec = get_execution_spec(str(selected_workflow_id))
    workflow = dict(spec.get("workflow") or {})
    required_inputs = list(workflow.get("required_inputs") or [])
    missing_inputs = [item for item in required_inputs if not inputs.get(item)]
    execution_plan = [
        {
            "step_id": step.get("step_id"),
            "adapter": step.get("adapter"),
            "operation": step.get("operation"),
            "external_service": step.get("external_service"),
        }
        for step in (workflow.get("steps") or [])
    ]
    approval_required_steps = [step.get("step_id") for step in (workflow.get("steps") or []) if step.get("approval_required")]
    recommended_next_actions = []
    if missing_inputs:
        recommended_next_actions.append(f"Provide missing inputs: {', '.join(missing_inputs)}")
    recommended_next_actions.append("Run safe_run to gather preliminary evidence and a structured report package.")
    return {
        "success": True,
        "user_request": user_request,
        "selected_workflow_id": selected_workflow_id,
        "selected_workflow_title": routed.get("selected_workflow_title"),
        "confidence": float(routed.get("confidence") or 0.0),
        "candidate_workflows": routed.get("candidates") or [],
        "missing_inputs": missing_inputs,
        "execution_plan": execution_plan,
        "approval_required_steps": approval_required_steps,
        "safe_run_available": True,
        "recommended_next_actions": recommended_next_actions,
        "limitations": list(DEFAULT_LIMITATIONS),
    }


def execute_case_workflow_plan(plan: dict[str, Any], mode: str = "safe_run", inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    inputs = dict(inputs or {})
    selected_workflow_id = str(plan.get("selected_workflow_id") or "")
    if not selected_workflow_id:
        return {
            "success": False,
            "error": "workflow_not_selected",
            "message": "No workflow was selected in the case plan.",
        }
    result = run_workflow(
        workflow_id=selected_workflow_id,
        user_request=str(plan.get("user_request") or ""),
        inputs=inputs,
        mode=mode,
    )
    result["recommended_next_actions"] = list(plan.get("recommended_next_actions") or [])
    return result
