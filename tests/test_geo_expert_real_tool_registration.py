from __future__ import annotations

from plugins.geo_expert import register


class FakeCtx:
    def __init__(self) -> None:
        self.tools = []
        self.skills = []

    def register_tool(self, **kwargs) -> None:
        self.tools.append(kwargs)

    def register_skill(self, **kwargs) -> None:
        self.skills.append(kwargs)


def test_geo_expert_real_tool_registration() -> None:
    ctx = FakeCtx()
    register(ctx)
    assert len(ctx.tools) == 20
    assert all(item["toolset"] == "geo_expert" for item in ctx.tools)
    names = [item["name"] for item in ctx.tools]
    for expected in (
        "geo_expert.workflow_list",
        "geo_expert.workflow_show",
        "geo_expert.rag_search_regulations",
        "geo_expert.spatial_query",
        "geo_expert.eo_local_analysis",
        "geo_expert.eo_openeo_status",
        "geo_expert.eo_openeo_prepare",
        "geo_expert.workflow_dry_run",
        "geo_expert.workflow_run",
        "geo_expert.workflow_eval_all",
        "geo_expert.workflow_route",
        "geo_expert.case_plan",
        "geo_expert.case_run",
        "geo_expert.satellite_acquire_preview",
    ):
        assert expected in names
