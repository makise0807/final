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


def test_pack_tools_registration() -> None:
    ctx = FakeCtx()
    register(ctx)
    names = [item["name"] for item in ctx.tools]
    for expected in (
        "geo_expert.pack_list",
        "geo_expert.pack_show",
        "geo_expert.pack_run",
        "geo_expert.user_data_import",
        "geo_expert.user_data_list",
        "geo_expert.user_data_search",
        "geo_expert.user_data_rag_answer",
    ):
        assert expected in names
