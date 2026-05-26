from __future__ import annotations

from plugins.geo_expert.workflow_runner import run_workflow


def test_geo_expert_workflow_rag_evidence() -> None:
    for workflow_id in ("WF-001", "WF-003", "WF-005", "WF-008"):
        inputs = {}
        if workflow_id == "WF-001":
            inputs = {"image_case_id": "sample_taichung_case", "require_satellite": False, "use_llm": False}
        result = run_workflow(workflow_id=workflow_id, user_request=workflow_id, inputs=inputs, mode="safe_run")
        rag_steps = [step for step in result["steps"] if step["adapter"] == "rag"]
        assert rag_steps
        for step in rag_steps:
            assert step["evidence"] or step["error"]
