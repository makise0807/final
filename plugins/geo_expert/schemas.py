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

SATELLITE_ACQUIRE_PREVIEW_SCHEMA = {
    "name": "geo_expert.satellite_acquire_preview",
    "description": "Acquire or locate a preliminary satellite preview through EO cache matching or optional GEE thumbnail preview. No OpenEO submit, GeoTIFF download, or export.",
    "parameters": {
        "type": "object",
        "properties": {
            "aoi": {"type": "object"},
            "bbox": {"type": "object"},
            "case_id": {"type": "string"},
            "workflow_id": {"type": "string"},
            "mode": {
                "type": "string",
                "enum": ["prepare_only", "cache_only", "preview"],
                "default": "prepare_only",
            },
            "provider": {"type": "string"},
            "time_range": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
    },
}

WORKFLOW_LIST_SCHEMA = {
    "name": "geo_expert.workflow_list",
    "description": "List workflow metadata from the plugin-local workflow database.",
    "parameters": {
        "type": "object",
        "properties": {}
    }
}

WORKFLOW_SHOW_SCHEMA = {
    "name": "geo_expert.workflow_show",
    "description": "Show a single workflow by workflow_id from the plugin-local workflow database.",
    "parameters": {
        "type": "object",
        "properties": {
            "workflow_id": {"type": "string"}
        },
        "required": ["workflow_id"]
    }
}

RAG_SEARCH_REGULATIONS_SCHEMA = {
    "name": "geo_expert.rag_search_regulations",
    "description": "Search regulations through the geo_expert RAG adapter with local fallback or structured unavailable response.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "default": 5},
            "source_filter": {"type": "string"}
        },
        "required": ["query"]
    }
}

SPATIAL_QUERY_SCHEMA = {
    "name": "geo_expert.spatial_query",
    "description": "Run a PostGIS-backed spatial adapter operation in unavailable-safe mode.",
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {"type": "string"},
            "parameters": {"type": "object"}
        },
        "required": ["operation"]
    }
}

EO_LOCAL_ANALYSIS_SCHEMA = {
    "name": "geo_expert.eo_local_analysis",
    "description": "Run local-only EO helper operations without external services.",
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {"type": "string"},
            "parameters": {"type": "object"}
        },
        "required": ["operation"]
    }
}

EO_OPENEO_STATUS_SCHEMA = {
    "name": "geo_expert.eo_openeo_status",
    "description": "Check OpenEO configuration availability without submitting jobs or downloading data.",
    "parameters": {
        "type": "object",
        "properties": {}
    }
}

EO_OPENEO_PREPARE_SCHEMA = {
    "name": "geo_expert.eo_openeo_prepare",
    "description": "Prepare an OpenEO request summary without submit/download/export.",
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {"type": "string"},
            "parameters": {"type": "object"}
        },
        "required": ["operation"]
    }
}

WORKFLOW_DRY_RUN_SCHEMA = {
    "name": "geo_expert.workflow_dry_run",
    "description": "Validate and plan a Geo Expert workflow without calling external services.",
    "parameters": {
        "type": "object",
        "properties": {
            "workflow_id": {"type": "string"},
            "user_request": {"type": "string"},
            "inputs": {"type": "object"}
        },
        "required": ["workflow_id"]
    }
}

WORKFLOW_RUN_SCHEMA = {
    "name": "geo_expert.workflow_run",
    "description": "Run a Geo Expert workflow in dry_run, safe_run, or real_run mode with high-risk actions still gated.",
    "parameters": {
        "type": "object",
        "properties": {
            "workflow_id": {"type": "string"},
            "user_request": {"type": "string"},
            "inputs": {"type": "object"},
            "mode": {"type": "string", "enum": ["dry_run", "safe_run", "real_run"], "default": "safe_run"},
            "require_approval": {"type": "boolean", "default": False}
        },
        "required": ["workflow_id"]
    }
}

WORKFLOW_EVAL_ALL_SCHEMA = {
    "name": "geo_expert.workflow_eval_all",
    "description": "Evaluate all 10 Geo Expert workflows in dry_run or safe_run mode.",
    "parameters": {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "enum": ["dry_run", "safe_run"], "default": "dry_run"}
        }
    }
}

WORKFLOW_ROUTE_SCHEMA = {
    "name": "geo_expert.workflow_route",
    "description": "Route a natural-language case description to the most relevant Geo Expert workflow, with clarification if confidence is low.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 5}
        },
        "required": ["query"]
    }
}

CASE_PLAN_SCHEMA = {
    "name": "geo_expert.case_plan",
    "description": "Create a collaborative Geo Expert case plan including workflow selection, missing inputs, approval items, and next actions.",
    "parameters": {
        "type": "object",
        "properties": {
            "user_request": {"type": "string"},
            "inputs": {"type": "object"}
        },
        "required": ["user_request"]
    }
}

CASE_RUN_SCHEMA = {
    "name": "geo_expert.case_run",
    "description": "Plan and execute a Geo Expert case in safe_run or real_run mode, without enabling high-risk actions.",
    "parameters": {
        "type": "object",
        "properties": {
            "user_request": {"type": "string"},
            "inputs": {"type": "object"},
            "mode": {"type": "string", "enum": ["safe_run", "real_run"], "default": "safe_run"}
        },
        "required": ["user_request"]
    }
}

PACK_LIST_SCHEMA = {
    "name": "geo_expert.pack_list",
    "description": "List Satellite Workflow Studio packs.",
    "parameters": {"type": "object", "properties": {}}
}

PACK_SHOW_SCHEMA = {
    "name": "geo_expert.pack_show",
    "description": "Show one Satellite Workflow Studio pack.",
    "parameters": {
        "type": "object",
        "properties": {"pack_id": {"type": "string"}},
        "required": ["pack_id"]
    }
}

PACK_RUN_SCHEMA = {
    "name": "geo_expert.pack_run",
    "description": "Run one Satellite Workflow Studio pack in deterministic safe mode.",
    "parameters": {
        "type": "object",
        "properties": {
            "pack_id": {"type": "string"},
            "user_request": {"type": "string"},
            "inputs": {"type": "object"},
            "mode": {"type": "string", "enum": ["safe_run", "dry_run"], "default": "safe_run"}
        },
        "required": ["pack_id", "user_request"]
    }
}

USER_DATA_IMPORT_SCHEMA = {
    "name": "geo_expert.user_data_import",
    "description": "Import runtime user data for one Satellite Workflow Studio pack.",
    "parameters": {
        "type": "object",
        "properties": {
            "pack_id": {"type": "string"},
            "source_files": {"type": "array", "items": {"type": "string"}},
            "embedding_backend": {"type": "string", "enum": ["hash", "sentence_transformers", "chroma_default"], "default": "hash"}
        },
        "required": ["pack_id", "source_files"]
    }
}

USER_DATA_LIST_SCHEMA = {
    "name": "geo_expert.user_data_list",
    "description": "List imported runtime user datasets for Satellite Workflow Studio.",
    "parameters": {
        "type": "object",
        "properties": {"pack_id": {"type": "string"}}
    }
}

USER_DATA_SEARCH_SCHEMA = {
    "name": "geo_expert.user_data_search",
    "description": "Search imported runtime user data with citations.",
    "parameters": {
        "type": "object",
        "properties": {
            "pack_id": {"type": "string"},
            "query": {"type": "string"},
            "dataset_ids": {"type": "array", "items": {"type": "string"}},
            "top_k": {"type": "integer", "default": 5}
        },
        "required": ["pack_id", "query"]
    }
}

USER_DATA_RAG_ANSWER_SCHEMA = {
    "name": "geo_expert.user_data_rag_answer",
    "description": "Answer using imported runtime user data only, with citations and no hallucinated fallback.",
    "parameters": {
        "type": "object",
        "properties": {
            "pack_id": {"type": "string"},
            "query": {"type": "string"},
            "dataset_ids": {"type": "array", "items": {"type": "string"}},
            "top_k": {"type": "integer", "default": 3}
        },
        "required": ["pack_id", "query"]
    }
}
