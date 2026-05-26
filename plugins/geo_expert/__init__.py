from __future__ import annotations

from pathlib import Path

from . import schemas, tools


PLUGIN_ROOT = Path(__file__).resolve().parent


def register(ctx) -> None:
    ctx.register_tool(
        name="geo_expert.run_preliminary_case_check",
        toolset="geo_expert",
        schema=schemas.RUN_PRELIMINARY_CASE_CHECK_SCHEMA,
        handler=tools.run_preliminary_case_check_handler,
        description="Run a preliminary geo/legal case check.",
        emoji="map",
    )
    ctx.register_tool(
        name="geo_expert.search_sop_database",
        toolset="geo_expert",
        schema=schemas.SEARCH_SOP_DATABASE_SCHEMA,
        handler=tools.search_sop_database_handler,
        description="Search the Geo Expert SOP database.",
        emoji="search",
    )
    ctx.register_tool(
        name="geo_expert.search_legal_database",
        toolset="geo_expert",
        schema=schemas.SEARCH_LEGAL_DATABASE_SCHEMA,
        handler=tools.search_legal_database_handler,
        description="Search legal context for preliminary analysis.",
        emoji="book",
    )
    ctx.register_tool(
        name="geo_expert.preview_satellite_overlay",
        toolset="geo_expert",
        schema=schemas.PREVIEW_SATELLITE_OVERLAY_SCHEMA,
        handler=tools.preview_satellite_overlay_handler,
        description="Generate a preliminary image overlay preview.",
        emoji="image",
    )
    ctx.register_tool(
        name="geo_expert.open_last_outputs",
        toolset="geo_expert",
        schema=schemas.OPEN_LAST_OUTPUTS_SCHEMA,
        handler=tools.open_last_outputs_handler,
        description="Return latest Geo Expert output paths.",
        emoji="folder",
    )
    ctx.register_tool(
        name="geo_expert.handle_approval",
        toolset="geo_expert",
        schema=schemas.HANDLE_APPROVAL_SCHEMA,
        handler=tools.handle_approval_handler,
        description="Record approval or denial without executing high-risk actions.",
        emoji="shield",
    )

    skill_path = PLUGIN_ROOT / "skills" / "geo" / "geo-expert-workflow" / "SKILL.md"
    ctx.register_skill(
        name="geo-expert-workflow",
        path=skill_path,
        description="Geo/legal preliminary case-check workflow.",
    )
