"""Policy evaluation for future real OpenEO job submission."""

from __future__ import annotations

from typing import Any

from .openeo_approval import verify_approval_token
from .openeo_credentials import OpenEOCredentials
from .openeo_submit_contracts import OpenEOSubmitPolicyDecision


HIGH_COMPUTE_PROCESSES = {"superresolution", "landslide"}


def evaluate_submit_policy(
    preview: dict[str, Any],
    validation_report: dict[str, Any],
    credentials: OpenEOCredentials,
    approval_token: str | None = None,
) -> OpenEOSubmitPolicyDecision:
    reasons: list[str] = []
    required_approvals: list[str] = []
    risks: list[str] = list(preview.get("estimated_risks") or [])
    warnings = list(validation_report.get("warnings") or [])
    validation_source = validation_report.get("validation_source")

    if preview.get("execution_mode") != "preview_only":
        reasons.append("preview_must_be_preview_only")
    if not preview.get("requires_approval", False):
        reasons.append("preview_must_require_approval")
    if not credentials.allow_real_network:
        reasons.append("real_network_disabled")
    if validation_source == "mock":
        reasons.append("mock_capabilities_cannot_approve_real_submit")
    elif validation_source == "real_cached":
        warnings.append("cached capabilities are not live backend state")
    elif validation_source == "real":
        pass
    else:
        warnings.append("validation source is not explicitly real-time")

    missing_collections = list(validation_report.get("missing_collections") or [])
    missing_processes = list(validation_report.get("missing_processes") or [])
    if missing_collections:
        reasons.append("missing_collection")
    if missing_processes:
        reasons.append("missing_process")

    backend_extensions = list(validation_report.get("backend_extensions_required") or [])
    if backend_extensions:
        required_approvals.append("backend_extension_approval")

    process_graph = dict(preview.get("process_graph_preview") or {})
    present_processes = {node.get("process_id") for node in process_graph.values() if node.get("process_id")}
    if HIGH_COMPUTE_PROCESSES & present_processes:
        required_approvals.append("high_compute_approval")

    if any("landuse overlay" in warning.lower() for warning in warnings):
        risks.append("landuse overlay may require non-backend GIS processing")

    approval = verify_approval_token(approval_token, "create_job") if approval_token else {
        "success": False,
        "error": "missing_approval_token",
        "requires_approval": True,
    }
    if not approval["success"]:
        reasons.append(approval["error"])

    if reasons:
        status = "blocked"
        if "mock_capabilities_cannot_approve_real_submit" in reasons:
            status = "blocked"
        elif "real_network_disabled" in reasons:
            status = "blocked"
        elif "missing_approval_token" in reasons or "approval_action_mismatch" in reasons or "approval_token_expired" in reasons:
            status = "awaiting_approval"
        return OpenEOSubmitPolicyDecision(
            allowed=False,
            status=status,
            reasons=list(dict.fromkeys(reasons)),
            required_approvals=list(dict.fromkeys(required_approvals)),
            risks=list(dict.fromkeys(risks)),
            warnings=list(dict.fromkeys(warnings)),
            message="Submit request is not eligible for real execution in the current phase.",
        )

    return OpenEOSubmitPolicyDecision(
        allowed=False,
        status="unsupported",
        reasons=["unsupported_real_execution_in_this_phase"],
        required_approvals=list(dict.fromkeys(required_approvals)),
        risks=list(dict.fromkeys(risks)),
        warnings=list(dict.fromkeys(warnings)),
        message="Approval can be checked, but real OpenEO submit remains unsupported in this phase.",
    )
