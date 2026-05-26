from __future__ import annotations

from plugins.geo_expert.adapters.workflow_tools import route_workflow


def test_geo_expert_workflow_routing_ambiguity() -> None:
    routed = route_workflow("我想查土地問題", limit=5)
    assert routed["success"] is True
    assert routed["needs_clarification"] is True or len(routed.get("candidates") or []) > 1
