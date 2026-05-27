from __future__ import annotations

from plugins.geo_expert.legal_grounding import build_applicability_check


def test_wf001_applicability_needs_human_review() -> None:
    result = build_applicability_check(
        user_request="農業區違章工廠是否可能涉及非都市土地使用管制",
        workflow_id="WF-001",
        facts={"parcel_location": "台中", "current_use": "疑似工廠"},
    )
    assert result["success"] is True
    assert result["human_review_required"] is True
    assert "illegal_factory_agriculture" in result["issue_tags"]


def test_applicability_needs_more_facts_when_missing_inputs() -> None:
    result = build_applicability_check(
        user_request="農業區違章工廠",
        workflow_id="WF-001",
        facts={"parcel_location": "台中"},
    )
    checklist = result["applicability_checklist"]
    assert checklist
    assert checklist[0]["human_review_required"] is True
    assert checklist[0]["applicability"] in {"needs_more_facts", "not_enough_evidence", "likely_relevant"}
    assert checklist[0]["facts_missing"]
