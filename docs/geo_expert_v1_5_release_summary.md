# Geo Expert v1.5 Release Summary

## Version Summary

- Version: `Geo Expert Plugin v1.5`
- Readiness: `real_service_partial operational`

## Scope

Geo Expert v1.5 is a hardening and release-preparation milestone for the Hermes native plugin path.
This release does not change Hermes core, does not add OpenEO submit, does not download GeoTIFF exports,
and does not introduce model training.

## Completed Items

- Plugin-native workflow engine remains stable across `WF-001` to `WF-010`.
- `case_plan` and `case_run` continue to work with structured workflow selection and report packaging.
- ChromaDB RAG is operational against `urban_regulations`.
- Local deterministic offline ingest is operational and no longer blocks on default Chroma embeddings.
- YOLO real-model smoke path is operational with external `yolo11n.pt`.
- EO cache indexing, cache-only preview, prepare-only satellite planning, and gated GEE preview path are operational.
- PostGIS parcel-centric coverage is operational for real parcel-based spatial checks.
- Service coverage and workflow reports now distinguish real service usage, fallback usage, and unresolved data gaps more clearly.
- Runtime outputs are ignored and `outputs/` has been removed from git tracking.
- Probe scripts are available for ChromaDB, detector, satellite, EO cache, GEE preview, and PostGIS diagnostics.

## Real Services Status

### RAG / ChromaDB

- Status: usable in local/offline development
- Collection: `urban_regulations`
- Document count: `1079`
- Backend: `deterministic_hash_v1`
- Current quality note: suitable for offline/dev validation, not production semantic quality

### Detector / YOLO

- Status: operational as a real detector smoke path
- Model: external `yolo11n.pt`
- Current scope: general object detector only
- Current quality note: not domain-specific for illegal factory, solar, or waste-site enforcement

### EO Cache / Satellite Adapter

- Status: operational for cache lookup, prepare-only planning, and gated preview path
- Cache images available: `10`
- Current limitation: most cache images do not have AOI sidecar metadata, so many matches still fall back to `latest_without_metadata`
- GEE execute requires explicit environment enablement plus valid dependency/auth state.

### PostGIS

- Status: operational for parcel-centric spatial checks
- Resolved aliases: `4`
- Missing aliases: `9`
- Current limitation: building / river / agricultural / hazard / slope / ecology / habitat / landuse / zoning-change layers still require external source data

## Service Coverage Snapshot

- Readiness level: `real_service_partial`
- Real service summary:
  - Real RAG steps: `7`
  - Real spatial steps: `7`
  - Real detector steps: `3`
  - EO cache assisted steps: `6`
- Satellite AOI match quality:
  - Precise matches: `0`
  - Fallback matches: `10`
  - Unknown metadata count: `10`
- PostGIS layer coverage:
  - Resolved: `4`
  - Missing: `9`

## Remaining Data Gaps

### EO / Satellite

- EO cache images still lack trustworthy AOI sidecar metadata in most cases.
- Precise AOI matching is only available when sidecar AOI metadata exists.
- GEE execute path remains intentionally gated and requires explicit environment enablement plus valid dependency/auth state.

### PostGIS

The following alias families still require real source layers and are not treated as resolved:

- `building_layer`
- `river_zone`
- `agricultural_zone`
- `hazard_zone`
- `slope_layer`
- `ecology_network_layer`
- `sensitive_habitat_layer`
- `landuse_layer`
- `zoning_change_layer`

### RAG Quality

- Deterministic hash embeddings are stable and offline-safe, but production semantic retrieval should migrate to a stronger local semantic embedding backend.

### Detector Quality

- `yolo11n` is only a general detector.
- Production deployment would require a domain-specific detector or downstream review logic, but no training was performed in this release.

### LLM Tool-Calling Path

- LLM automatic tool-calling is not the primary success path for this release.
- Workflow execution, case planning, direct handlers, probes, and reports are independently testable without relying on oneshot tool-calling.

## Safety Boundaries

Geo Expert v1.5 keeps the following boundaries intact:

- No Hermes core changes
- No `toolsets.py` changes
- No `tools/registry.py` changes
- No agent loop changes
- No OpenEO submit
- No GeoTIFF download
- No export pipeline
- No formal legal conclusion generation
- No model training
- No copying large EO cache or model assets into the repository
- No automatic destructive PostGIS restore
- Runtime `outputs/` are ignored and no longer tracked

## Test Results

- Full Geo Expert suite: `79 passed, 1 warning`
- Release hardening maintained and improved the previous `61` / `76` pass baselines without reducing assertions

## How To Run

### Environment Setup

```powershell
$env:PYTHONPATH="C:\Users\34620\OneDrive\Desktop\final;C:\Users\34620\OneDrive\Desktop\final\plugins\geo_expert"
$env:GEO_EXPERT_EO_CACHE_DIR="C:\Users\34620\OneDrive\Desktop\geo-orchestrator\data\eo_cache"
$env:GEO_EXPERT_SATELLITE_PROVIDER="cache_only"
$env:GEO_EXPERT_ALLOW_SATELLITE_FETCH="0"
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5433"
$env:POSTGRES_DB="geodb"
$env:POSTGRES_USER="geouser"
$env:POSTGRES_PASSWORD="geopassword"
$env:CHROMA_HOST="localhost"
$env:CHROMA_PORT="8000"
$env:CHROMA_COLLECTION_REGULATIONS="urban_regulations"
$env:GEO_EXPERT_DETECTOR_BACKEND="yolo"
$env:GEO_EXPERT_DETECTOR_MODEL_PATH="C:\Users\34620\OneDrive\Desktop\geo-orchestrator\yolo11n.pt"
$env:GEO_EXPERT_DETECTOR_DEVICE="cpu"
$env:GEO_EXPERT_DETECTOR_CONFIDENCE="0.25"
```

### Probe Commands

```powershell
py -3.11 scripts\probe_geo_expert_chromadb.py
py -3.11 scripts\probe_geo_expert_detector.py
py -3.11 scripts\probe_geo_expert_satellite.py
py -3.11 scripts\probe_geo_expert_postgis.py
py -3.11 scripts\probe_geo_expert_gee_preview.py --bbox 120.7,23.45,120.72,23.47
```

### Workflow Eval

```powershell
py -3.11 -X utf8 -c "from plugins.geo_expert.tools import workflow_eval_all_handler; print(workflow_eval_all_handler({'mode':'safe_run'}))"
```

### Full Tests

```powershell
$files = Get-ChildItem tests -Filter 'test_geo_expert_*.py' | ForEach-Object { $_.FullName }
py -3.11 -m pytest -q -o addopts="" $files
```

## Recommended v1.6 Priorities

1. Import or wire real spatial source layers for the remaining 9 PostGIS aliases.
2. Add trustworthy EO sidecar metadata or GEE request log recovery so AOI matching can move beyond `latest_without_metadata`.
3. Add optional local semantic embedding backend adoption for RAG validation in environments where a local embedding model is available.
4. Improve detector post-processing and review workflows around YOLO outputs without treating the model as domain-specific.
5. Revisit LLM auto tool-calling only after local provider/tool-calling behavior is stable; keep workflow execution independent from that path.
