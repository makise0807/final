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

    assert len(ctx.tools) == 6
    tool_names = [entry["name"] for entry in ctx.tools]
    assert tool_names == [
        "geo_expert.run_preliminary_case_check",
        "geo_expert.search_sop_database",
        "geo_expert.search_legal_database",
        "geo_expert.preview_satellite_overlay",
        "geo_expert.open_last_outputs",
        "geo_expert.handle_approval",
    ]
    assert all(entry["toolset"] == "geo_expert" for entry in ctx.tools)
    assert ctx.skills
    assert ctx.skills[0]["name"] == "geo-expert-workflow"
    assert Path(ctx.skills[0]["path"]).exists()
