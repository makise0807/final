from __future__ import annotations

from pathlib import Path

from plugins.geo_expert import register


class FakeCtx:
    def __init__(self) -> None:
        self.tools = []
        self.skills = []

    def register_tool(self, **kwargs) -> None:
        self.tools.append(kwargs)

    def register_skill(self, **kwargs) -> None:
        self.skills.append(kwargs)


def test_geo_expert_registration() -> None:
    ctx = FakeCtx()
    register(ctx)

    assert len(ctx.tools) == 27
    tool_names = [entry["name"] for entry in ctx.tools]
    for expected in (
        "geo_expert.run_preliminary_case_check",
        "geo_expert.search_sop_database",
        "geo_expert.search_legal_database",
        "geo_expert.preview_satellite_overlay",
        "geo_expert.satellite_acquire_preview",
        "geo_expert.workflow_run",
        "geo_expert.workflow_eval_all",
        "geo_expert.case_plan",
        "geo_expert.case_run",
        "geo_expert.pack_list",
        "geo_expert.pack_show",
        "geo_expert.pack_run",
        "geo_expert.user_data_import",
        "geo_expert.user_data_list",
        "geo_expert.user_data_search",
        "geo_expert.user_data_rag_answer",
    ):
        assert expected in tool_names
    assert all(entry["toolset"] == "geo_expert" for entry in ctx.tools)
    assert ctx.skills
    assert ctx.skills[0]["name"] == "geo-expert-workflow"
    assert Path(ctx.skills[0]["path"]).exists()
