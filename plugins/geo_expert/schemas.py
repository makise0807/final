RUN_PRELIMINARY_CASE_CHECK_SCHEMA = {
    "name": "geo_expert.run_preliminary_case_check",
    "description": "Run a preliminary geo/legal case check. Produces report, GeoJSON, and overlay preview. Preliminary only; no OpenEO submit, no GeoTIFF, no export, no formal legal conclusion.",
    "parameters": {
        "type": "object",
        "properties": {
            "user_request": {
                "type": "string",
                "description": "Original user request."
            },
            "image_case_id": {
                "type": "string",
                "description": "Optional local fixture case id, such as sample_taichung_case."
            },
            "image_path": {
                "type": "string",
                "description": "Optional direct local image path."
            },
            "image_aoi": {
                "type": "object",
                "description": "AOI for direct local image mode."
            },
            "require_satellite": {
                "type": "boolean",
                "description": "Require real satellite thumbnail. If unavailable, structured-fail instead of placeholder.",
                "default": False
            },
            "use_llm": {
                "type": "boolean",
                "description": "Use LLM-assisted explanation if available.",
                "default": True
            },
            "output_dir": {
                "type": "string",
                "description": "Output directory for report, GeoJSON, and overlay.",
                "default": "outputs/geo_expert/latest"
            }
        },
        "required": ["user_request"]
    }
}

SEARCH_SOP_DATABASE_SCHEMA = {
    "name": "geo_expert.search_sop_database",
    "description": "Search Geo Expert SOP database without running the full workflow.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 5}
        },
        "required": ["query"]
    }
}

SEARCH_LEGAL_DATABASE_SCHEMA = {
    "name": "geo_expert.search_legal_database",
    "description": "Search legal database for preliminary legal context. Not formal legal advice.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 5}
        },
        "required": ["query"]
    }
}

PREVIEW_SATELLITE_OVERLAY_SCHEMA = {
    "name": "geo_expert.preview_satellite_overlay",
    "description": "Generate a preliminary image overlay preview from local fixture, local image, GEE thumbnail, or placeholder fallback.",
    "parameters": {
        "type": "object",
        "properties": {
            "image_case_id": {"type": "string"},
            "image_path": {"type": "string"},
            "image_aoi": {"type": "object"},
            "aoi": {"type": "object"},
            "require_satellite": {"type": "boolean", "default": False},
            "output_dir": {"type": "string", "default": "outputs/geo_expert/latest"}
        }
    }
}

OPEN_LAST_OUTPUTS_SCHEMA = {
    "name": "geo_expert.open_last_outputs",
    "description": "Return latest Geo Expert output paths.",
    "parameters": {
        "type": "object",
        "properties": {
            "output_dir": {"type": "string", "default": "outputs/geo_expert/latest"}
        }
    }
}

HANDLE_APPROVAL_SCHEMA = {
    "name": "geo_expert.handle_approval",
    "description": "Record an approval or denial decision. Does not execute high-risk actions.",
    "parameters": {
        "type": "object",
        "properties": {
            "approval_id": {"type": "string"},
            "decision": {
                "type": "string",
                "enum": ["approve", "deny"]
            }
        },
        "required": ["decision"]
    }
}