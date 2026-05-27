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
        name="geo_expert.satellite_acquire_preview",
        toolset="geo_expert",
        schema=schemas.SATELLITE_ACQUIRE_PREVIEW_SCHEMA,
        handler=tools.satellite_acquire_preview_handler,
        description="Acquire or locate a preliminary satellite preview through EO cache or optional GEE preview.",
        emoji="satellite",
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
    ctx.register_tool(
        name="geo_expert.workflow_list",
        toolset="geo_expert",
        schema=schemas.WORKFLOW_LIST_SCHEMA,
        handler=tools.workflow_list_handler,
        description="List Geo Expert workflows from local plugin data.",
        emoji="list",
    )
    ctx.register_tool(
        name="geo_expert.workflow_show",
        toolset="geo_expert",
        schema=schemas.WORKFLOW_SHOW_SCHEMA,
        handler=tools.workflow_show_handler,
        description="Show one Geo Expert workflow from local plugin data.",
        emoji="book",
    )
    ctx.register_tool(
        name="geo_expert.rag_search_regulations",
        toolset="geo_expert",
        schema=schemas.RAG_SEARCH_REGULATIONS_SCHEMA,
        handler=tools.rag_search_regulations_handler,
        description="Search regulations through the geo_expert RAG adapter.",
        emoji="scroll",
    )
    ctx.register_tool(
        name="geo_expert.spatial_query",
        toolset="geo_expert",
        schema=schemas.SPATIAL_QUERY_SCHEMA,
        handler=tools.spatial_query_handler,
        description="Run a geo_expert spatial adapter operation.",
        emoji="triangle",
    )
    ctx.register_tool(
        name="geo_expert.eo_local_analysis",
        toolset="geo_expert",
        schema=schemas.EO_LOCAL_ANALYSIS_SCHEMA,
        handler=tools.eo_local_analysis_handler,
        description="Run local-only EO helper operations.",
        emoji="satellite",
    )
    ctx.register_tool(
        name="geo_expert.eo_openeo_status",
        toolset="geo_expert",
        schema=schemas.EO_OPENEO_STATUS_SCHEMA,
        handler=tools.eo_openeo_status_handler,
        description="Check OpenEO adapter configuration without submit/download.",
        emoji="status",
    )
    ctx.register_tool(
        name="geo_expert.eo_openeo_prepare",
        toolset="geo_expert",
        schema=schemas.EO_OPENEO_PREPARE_SCHEMA,
        handler=tools.eo_openeo_prepare_handler,
        description="Prepare an OpenEO request summary without submit/download/export.",
        emoji="gear",
    )
    ctx.register_tool(
        name="geo_expert.workflow_dry_run",
        toolset="geo_expert",
        schema=schemas.WORKFLOW_DRY_RUN_SCHEMA,
        handler=tools.workflow_dry_run_handler,
        description="Validate and plan one Geo Expert workflow without external execution.",
        emoji="clipboard",
    )
    ctx.register_tool(
        name="geo_expert.workflow_run",
        toolset="geo_expert",
        schema=schemas.WORKFLOW_RUN_SCHEMA,
        handler=tools.workflow_run_handler,
        description="Run one Geo Expert workflow in dry_run, safe_run, or real_run mode.",
        emoji="play",
    )
    ctx.register_tool(
        name="geo_expert.workflow_eval_all",
        toolset="geo_expert",
        schema=schemas.WORKFLOW_EVAL_ALL_SCHEMA,
        handler=tools.workflow_eval_all_handler,
        description="Evaluate all Geo Expert workflows for coverage and safety.",
        emoji="checklist",
    )
    ctx.register_tool(
        name="geo_expert.workflow_route",
        toolset="geo_expert",
        schema=schemas.WORKFLOW_ROUTE_SCHEMA,
        handler=tools.workflow_route_handler,
        description="Route a case description to the best Geo Expert workflow.",
        emoji="route",
    )
    ctx.register_tool(
        name="geo_expert.case_plan",
        toolset="geo_expert",
        schema=schemas.CASE_PLAN_SCHEMA,
        handler=tools.case_plan_handler,
        description="Create a collaborative case plan before running a workflow.",
        emoji="plan",
    )
    ctx.register_tool(
        name="geo_expert.case_run",
        toolset="geo_expert",
        schema=schemas.CASE_RUN_SCHEMA,
        handler=tools.case_run_handler,
        description="Run a collaborative Geo Expert case workflow with a report package.",
        emoji="play",
    )
    ctx.register_tool(
        name="geo_expert.pack_list",
        toolset="geo_expert",
        schema=schemas.PACK_LIST_SCHEMA,
        handler=tools.pack_list_handler,
        description="List Satellite Workflow Studio packs.",
        emoji="list",
    )
    ctx.register_tool(
        name="geo_expert.pack_show",
        toolset="geo_expert",
        schema=schemas.PACK_SHOW_SCHEMA,
        handler=tools.pack_show_handler,
        description="Show one Satellite Workflow Studio pack.",
        emoji="book",
    )
    ctx.register_tool(
        name="geo_expert.pack_run",
        toolset="geo_expert",
        schema=schemas.PACK_RUN_SCHEMA,
        handler=tools.pack_run_handler,
        description="Run one Satellite Workflow Studio pack in deterministic safe mode.",
        emoji="play",
    )
    ctx.register_tool(
        name="geo_expert.user_data_import",
        toolset="geo_expert",
        schema=schemas.USER_DATA_IMPORT_SCHEMA,
        handler=tools.user_data_import_handler,
        description="Import runtime user data for one Satellite Workflow Studio pack.",
        emoji="upload",
    )
    ctx.register_tool(
        name="geo_expert.user_data_list",
        toolset="geo_expert",
        schema=schemas.USER_DATA_LIST_SCHEMA,
        handler=tools.user_data_list_handler,
        description="List imported runtime user datasets.",
        emoji="folder",
    )
    ctx.register_tool(
        name="geo_expert.user_data_search",
        toolset="geo_expert",
        schema=schemas.USER_DATA_SEARCH_SCHEMA,
        handler=tools.user_data_search_handler,
        description="Search imported runtime user data with citations.",
        emoji="search",
    )
    ctx.register_tool(
        name="geo_expert.user_data_rag_answer",
        toolset="geo_expert",
        schema=schemas.USER_DATA_RAG_ANSWER_SCHEMA,
        handler=tools.user_data_rag_answer_handler,
        description="Answer from imported runtime user data only.",
        emoji="quote",
    )
    ctx.register_tool(
        name="geo_expert.legal_audit",
        toolset="geo_expert",
        schema=schemas.LEGAL_AUDIT_SCHEMA,
        handler=tools.legal_audit_handler,
        description="Audit legal RAG grounding coverage and citation readiness.",
        emoji="scroll",
    )
    ctx.register_tool(
        name="geo_expert.legal_applicability_check",
        toolset="geo_expert",
        schema=schemas.LEGAL_APPLICABILITY_CHECK_SCHEMA,
        handler=tools.legal_applicability_check_handler,
        description="Run a grounded legal applicability checklist for expert review draft reporting.",
        emoji="balance_scale",
    )
    ctx.register_tool(
        name="geo_expert.spatial_capability_show",
        toolset="geo_expert",
        schema=schemas.SPATIAL_CAPABILITY_SHOW_SCHEMA,
        handler=tools.spatial_capability_show_handler,
        description="Show PostGIS available and missing layer capability tiers with import next actions.",
        emoji="layers",
    )
    ctx.register_tool(
        name="geo_expert.production_readiness_show",
        toolset="geo_expert",
        schema=schemas.PRODUCTION_READINESS_SHOW_SCHEMA,
        handler=tools.production_readiness_show_handler,
        description="Show readiness score, blockers, approval gates, and cache policy.",
        emoji="checklist",
    )
    ctx.register_tool(
        name="geo_expert.run_manifest_create",
        toolset="geo_expert",
        schema=schemas.RUN_MANIFEST_CREATE_SCHEMA,
        handler=tools.run_manifest_create_handler,
        description="Create a reproducibility manifest for a workflow or pack result.",
        emoji="clipboard",
    )
    ctx.register_tool(
        name="geo_expert.service_health_check",
        toolset="geo_expert",
        schema=schemas.SERVICE_HEALTH_CHECK_SCHEMA,
        handler=tools.service_health_check_handler,
        description="Check Geo Expert runtime service health with structured degraded responses.",
        emoji="status",
    )
    ctx.register_tool(
        name="geo_expert.openeo_acquisition_plan",
        toolset="geo_expert",
        schema=schemas.OPENEO_ACQUISITION_PLAN_SCHEMA,
        handler=tools.openeo_acquisition_plan_handler,
        description="Prepare an approval-gated OpenEO GeoTIFF acquisition plan.",
        emoji="satellite",
    )
    ctx.register_tool(
        name="geo_expert.openeo_acquisition_run",
        toolset="geo_expert",
        schema=schemas.OPENEO_ACQUISITION_RUN_SCHEMA,
        handler=tools.openeo_acquisition_run_handler,
        description="Run OpenEO acquisition in prepare_only, cache_only, or explicit approved_run mode.",
        emoji="play",
    )
    ctx.register_tool(
        name="geo_expert.geotiff_cache_list",
        toolset="geo_expert",
        schema=schemas.GEOTIFF_CACHE_LIST_SCHEMA,
        handler=tools.geotiff_cache_list_handler,
        description="List runtime GeoTIFF cache metadata from outputs.",
        emoji="folder",
    )

    skill_path = PLUGIN_ROOT / "skills" / "geo" / "geo-expert-workflow" / "SKILL.md"
    ctx.register_skill(
        name="geo-expert-workflow",
        path=skill_path,
        description="Geo/legal preliminary case-check workflow.",
    )
