# Geo Expert Plugin Handoff

## TL;DR

- Geo Expert Plugin v1.5 is runnable and release-ready.
- Real services currently working: ChromaDB RAG, YOLO detector path, EO cache/satellite cache path, and parcel-centric PostGIS checks.
- Still degraded or partial: EO cache AOI precision for most existing images, 9 missing PostGIS domain layers, production-grade embeddings, and domain-specific detector quality.
- Full Geo Expert test status: `79 passed, 1 warning`.

## Repo / Path Map

- Final repo: `C:\Users\34620\OneDrive\Desktop\final`
- Source repo: `C:\Users\34620\OneDrive\Desktop\geo-orchestrator`
- Docker services: `C:\Users\34620\OneDrive\Desktop\geo-orchestrator\database`
- Plugin path: `C:\Users\34620\OneDrive\Desktop\final\plugins\geo_expert`
- Workflow data: `C:\Users\34620\OneDrive\Desktop\final\plugins\geo_expert\data\workflow_db`
- Spatial alias data: `C:\Users\34620\OneDrive\Desktop\final\plugins\geo_expert\data\spatial`
- Probe scripts: `C:\Users\34620\OneDrive\Desktop\final\scripts`
- Runtime outputs: `C:\Users\34620\OneDrive\Desktop\final\outputs`

## Current Commits

- `27fd5b1 feat(geo-expert): add real-service satellite and coverage hardening`
- `a395dfd chore: stop tracking Geo Expert runtime outputs`

## Environment Setup

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
$env:CHROMA_COLLECTION_WORKFLOWS="urban_regulations"
$env:CHROMA_COLLECTION_MAP_METADATA="urban_regulations"
$env:GEO_EXPERT_DETECTOR_BACKEND="yolo"
$env:GEO_EXPERT_DETECTOR_MODEL_PATH="C:\Users\34620\OneDrive\Desktop\geo-orchestrator\yolo11n.pt"
$env:GEO_EXPERT_DETECTOR_DEVICE="cpu"
$env:GEO_EXPERT_DETECTOR_CONFIDENCE="0.25"
```

## Start Services

```powershell
cd C:\Users\34620\OneDrive\Desktop\geo-orchestrator\database
docker compose up -d
docker compose ps
```

Ports:

- PostGIS host `5433` -> container `5432`
- ChromaDB `8000`
- pgAdmin `5050`

## Verification Checklist

```powershell
py -3.11 scripts\probe_geo_expert_chromadb.py
py -3.11 scripts\probe_geo_expert_postgis.py
py -3.11 scripts\probe_geo_expert_detector.py
py -3.11 scripts\probe_geo_expert_satellite.py
py -3.11 -X utf8 -c "from plugins.geo_expert.tools import workflow_eval_all_handler; print(workflow_eval_all_handler({'mode':'safe_run'}))"
```

Full tests:

```powershell
$files = Get-ChildItem tests -Filter 'test_geo_expert_*.py' | ForEach-Object { $_.FullName }
py -3.11 -m pytest -q -o addopts="" $files
```

## What Is Real vs Fallback

| Component | Real | Fallback | Current limitation |
| --- | --- | --- | --- |
| ChromaDB RAG | Yes | local fallback remains available | deterministic hash embedding is dev/offline quality |
| YOLO detector | Yes | mock fallback remains available | `yolo11n` is general, not domain-specific |
| EO cache | Yes | latest image fallback | most images have no trusted AOI sidecar |
| GEE preview | Guarded | prepare/degraded | execute requires explicit env + auth |
| PostGIS | Partial | degraded for missing aliases | only parcel-centric coverage is real today |

## Workflows

- `WF-001` 農業區違章工廠盤查: parcel review plus detector-assisted preliminary case check
- `WF-002` 山坡地保育區超限利用監測: EO-assisted hillside overuse review
- `WF-003` 都市更新單元劃定條件評估: urban renewal unit condition assessment
- `WF-004` 河川行水區違法傾倒廢棄物監測: river/floodplain waste dumping review
- `WF-005` 農地種電（光電設施）合法性稽查: farmland solar legality check
- `WF-006` 新訂都市計畫區區位適宜性分析: new urban plan siting suitability analysis
- `WF-007` 變更特定農業區為一般農業區檢核: agricultural zoning change review
- `WF-008` 捷運場站周邊（TOD）容積獎勵試算盤點: TOD incentive review
- `WF-009` 崩塌地與淹塞湖防災潛勢評估: landslide and barrier-lake hazard assessment
- `WF-010` 國土綠網與生態敏感區開發干擾評估: ecological network and sensitive habitat impact review

## Important Tools / Handlers

- `workflow_eval_all_handler`
- `workflow_run_handler`
- `case_plan_handler`
- `case_run_handler`
- `satellite_acquire_preview_handler`

## Data Gaps

- EO sidecar metadata is missing for most current cache images
- Current EO cache artifacts in the available source tree do not provide a trustworthy AOI recovery path; precise sidecars will require a new GEE preview execute run or a manually verified mapping file
- PostGIS still lacks 9 domain layers
- RAG embedding quality is intentionally offline-safe rather than production semantic quality
- YOLO path is real but remains a general detector

## Do-Not-Touch / Safety Notes

- Do not modify Hermes core for Geo Expert work
- Do not use `git add .`
- Do not commit `outputs/`
- Do not run automatic `pg_restore`
- Do not enable OpenEO submit/export in the safe path
- Do not copy `yolo11n.pt` or EO cache imagery into the repo
- Do not present fallback/degraded outputs as real success

## How To Continue

- Add trustworthy EO sidecar metadata or run a real GEE preview execute flow with auth
- Import missing spatial layers for river, hazard, ecology, landuse, zoning, and building coverage
- Switch to an optional local semantic embedding backend if a suitable model is available
- Consider future domain-specific detector training in a separate project phase

## Troubleshooting

- Chroma collection empty: rerun local ingest and verify `urban_regulations`
- PostGIS alias missing: inspect `layer_alias_audit.md` and import plans before changing aliases
- SQLAlchemy missing: install the Python dependency in the active environment
- ultralytics missing: install it before expecting real YOLO usage
- GEE auth missing: keep preview in prepare mode until Earth Engine auth is configured
- `latest_without_metadata` warning: expected until cache images gain trustworthy AOI sidecars
- Existing EO cache cannot be safely backfilled with precise AOI unless a new GEE preview execute or a manually verified mapping file is provided
- outputs still tracked: `git ls-files outputs` should be empty; if not, stop and fix git tracking before release

## Final Acceptance State

- Full Geo Expert tests: `79 passed, 1 warning`
- `outputs/` is ignored and untracked
- Release summary: `C:\Users\34620\OneDrive\Desktop\final\docs\geo_expert_v1_5_release_summary.md`
- README for delivery: `C:\Users\34620\OneDrive\Desktop\final\docs\geo_expert_readme.md`
