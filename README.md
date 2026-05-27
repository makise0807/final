# Geo Expert Plugin for Hermes

> A Hermes-native geospatial expert workflow plugin for EO preview, PostGIS spatial checks, legal RAG, YOLO-assisted image review, and case planning.

## Satellite Workflow Studio v0.2 MVP

Geo Expert now includes a deterministic `Satellite Workflow Studio` layer for multi-domain pack orchestration. It adds pack-based workflows such as real estate insight, geo classroom, public inspection, agriculture monitoring, disaster rapid scan, ESG environment, outdoor safety, media investigation, urban planning, and climate/land change without changing Hermes core or turning Geo Expert into built-in core tools. Satellite Workflow Studio v0.2 MVP supports 10 safe-run packs with user data RAG and deterministic report templates. Geo Expert v1.6 adds legal grounding for citation-based applicability checklists, a production-readiness framework, and an approval-gated OpenEO / GeoTIFF acquisition path that defaults to prepare-only mode, without claiming formal legal decisions or complete spatial coverage.

See:

- [docs/satellite_workflow_studio.md](C:\Users\34620\OneDrive\Desktop\final\docs\satellite_workflow_studio.md)
- [docs/geo_expert_readme.md](C:\Users\34620\OneDrive\Desktop\final\docs\geo_expert_readme.md)

## Status

- Status: `v1.5 release candidate`
- Tests: `79 passed, 1 warning`
- Hermes core changes: `none`
- OpenEO submit/export: `disabled by default`
- Runtime outputs: `ignored`

## What It Does

- Runs `10` expert workflows from `WF-001` to `WF-010`
- Supports `case_plan` and `case_run` for structured case intake and execution
- Uses ChromaDB legal RAG against `urban_regulations`
- Performs parcel-centric PostGIS spatial checks
- Uses EO cache and a guarded satellite preview adapter
- Supports a real YOLO model path via external `yolo11n.pt`
- Produces structured workflow reports and result packages
- Exposes service coverage diagnostics so real vs fallback paths stay visible

## Current Real-Service Coverage

| Service | Current status | Notes |
| --- | --- | --- |
| ChromaDB RAG | operational | `urban_regulations`, `1079` docs, deterministic hash embedding |
| YOLO detector | operational | `yolo11n` general detector, not domain-specific |
| EO cache / satellite | operational partial | cache/prepare/gated preview, AOI sidecar needed for precise match |
| PostGIS | operational partial | parcel-centric, `aliases_resolved=4`, missing `9` domain layers |
| OpenEO | guarded | no submit/download/export in safe path |

## Quick Start

```powershell
cd C:\Users\34620\OneDrive\Desktop\final

cd C:\Users\34620\OneDrive\Desktop\geo-orchestrator\database
docker compose up -d

cd C:\Users\34620\OneDrive\Desktop\final

$env:PYTHONPATH="C:\Users\34620\OneDrive\Desktop\final;C:\Users\34620\OneDrive\Desktop\final\plugins\geo_expert"
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5433"
$env:POSTGRES_DB="geodb"
$env:POSTGRES_USER="geouser"
$env:POSTGRES_PASSWORD="geopassword"
$env:CHROMA_HOST="localhost"
$env:CHROMA_PORT="8000"
$env:CHROMA_COLLECTION_REGULATIONS="urban_regulations"
$env:CHROMA_COLLECTION_WORKFLOWS="urban_regulations"
$env:CHROMA_COLLECTION_MAP_METADATA="urban_regulations"
$env:GEO_EXPERT_EO_CACHE_DIR="C:\Users\34620\OneDrive\Desktop\geo-orchestrator\data\eo_cache"
$env:GEO_EXPERT_DETECTOR_BACKEND="yolo"
$env:GEO_EXPERT_DETECTOR_MODEL_PATH="C:\Users\34620\OneDrive\Desktop\geo-orchestrator\yolo11n.pt"
$env:GEO_EXPERT_DETECTOR_DEVICE="cpu"
$env:GEO_EXPERT_DETECTOR_CONFIDENCE="0.25"
```

`POSTGRES_PASSWORD` can follow the current docker-compose default `geopassword`, but should be overridden with a local `.env` if your environment differs.

## Run Probes

```powershell
py -3.11 scripts\probe_geo_expert_chromadb.py
py -3.11 scripts\probe_geo_expert_postgis.py
py -3.11 scripts\probe_geo_expert_detector.py
py -3.11 scripts\probe_geo_expert_satellite.py
py -3.11 scripts\probe_geo_expert_gee_preview.py --bbox 120.7,23.45,120.72,23.47
```

## Run Workflows

```powershell
py -3.11 -X utf8 -c "from plugins.geo_expert.tools import workflow_eval_all_handler; print(workflow_eval_all_handler({'mode':'safe_run'}))"
py -3.11 -X utf8 -c "from plugins.geo_expert.tools import case_plan_handler; print(case_plan_handler({'user_request':'我要找台中的違章建築','inputs':{'location':'台中'}}))"
py -3.11 -X utf8 -c "from plugins.geo_expert.tools import case_run_handler; print(case_run_handler({'user_request':'我要找台中的違章建築','mode':'safe_run','inputs':{'image_case_id':'sample_taichung_case','require_satellite':False,'use_llm':False}}))"
py -3.11 -X utf8 -c "from plugins.geo_expert.tools import satellite_acquire_preview_handler; print(satellite_acquire_preview_handler({'aoi':{'west':120.7,'south':23.45,'east':120.72,'north':23.47},'mode':'prepare_only'}))"
py -3.11 -X utf8 -c "from plugins.geo_expert.tools import workflow_run_handler; print(workflow_run_handler({'workflow_id':'WF-001','user_request':'台中農地違章工廠','mode':'safe_run','inputs':{'image_case_id':'sample_taichung_case','require_satellite':False,'use_llm':False,'real_detector':True}}))"
```

## Tools Exposed by the Plugin

- `geo_expert.workflow_show`
- `geo_expert.search_sop_database`
- `geo_expert.workflow_dry_run`
- `geo_expert.workflow_run`
- `geo_expert.workflow_eval_all`
- `geo_expert.case_plan`
- `geo_expert.case_run`
- `geo_expert.satellite_acquire_preview`
- Plus supporting data, preview, and expert-search tools defined in `plugins/geo_expert/plugin.yaml`

## Architecture

```text
Hermes plugin loader
  -> plugins/geo_expert/__init__.py
  -> schemas.py / tools.py
  -> workflow_runner.py
  -> adapters/
      rag_tools.py
      spatial_tools.py
      detector_tools.py
      eo_tools.py
      satellite_tools.py
  -> reporting/
  -> data/workflow_db
  -> data/spatial
  -> scripts/probes
```

## Safety Model

- No Hermes core modification
- No OpenEO submit by default
- No GeoTIFF download/export by default
- No destructive PostGIS restore
- GEE preview requires explicit env enablement plus `--execute`
- YOLO is a general model and does not make legal conclusions
- Reports are preliminary workflow outputs, not formal legal advice
- Missing data remains degraded and is not faked as success

## Testing

```powershell
$files = Get-ChildItem tests -Filter 'test_geo_expert_*.py' | ForEach-Object { $_.FullName }
py -3.11 -m pytest -q -o addopts="" $files
```

Expected:

```text
79 passed, 1 warning
```

## Known Limitations

- EO cache lacks trustworthy AOI sidecar metadata for the current 10 images
- GEE preview execute requires valid Earth Engine auth
- PostGIS is still missing 9 domain layers beyond parcel-centric coverage
- Deterministic hash embedding is dev/offline validation quality
- `yolo11n` is a general detector, not a trained domain enforcement model
- LLM automatic tool-calling is not required for direct workflow validation

## Roadmap / v1.6

- Run a real GEE preview execute smoke with authenticated Earth Engine access
- Import missing spatial layers for river, hazard, landuse, ecology, and zoning workflows
- Add optional semantic embedding backend for stronger local retrieval quality
- Consider domain-specific detector training later
- Revisit LLM tool-call provider validation separately from plugin workflow validation

## Attribution / Relation to Hermes

- This is a Hermes-native plugin and workflow integration.
- Geo Expert functionality remains inside `plugins/geo_expert`.
- It does not turn Geo Expert into Hermes core built-in tools.
- Hermes Agent itself remains attributed to Nous Research in the upstream root README.
