# Real Service Wiring

This plugin keeps all real services optional and read-only by default.

## Detector

Set these variables to enable a YOLO smoke path without copying weights into the repo:

```powershell
$env:GEO_EXPERT_DETECTOR_BACKEND="yolo"
$env:GEO_EXPERT_DETECTOR_MODEL_PATH="C:\Users\34620\OneDrive\Desktop\geo-orchestrator\yolo11n.pt"
$env:GEO_EXPERT_DETECTOR_DEVICE="cpu"
$env:GEO_EXPERT_DETECTOR_CONFIDENCE="0.25"
```

Notes:
- `yolo11n.pt` is a generic visual detector, not a domain-specific illegal-factory model.
- If `ultralytics` is missing, the adapter returns a degraded result and keeps the mock fallback available.
- Install explicitly if you want to try the real model path:

```powershell
py -3.11 -m pip install ultralytics
```

## ChromaDB

The plugin supports collection aliases so an existing `urban_regulations` collection can be used without rewriting Hermes core settings.

Preferred environment variables:

```powershell
$env:CHROMA_COLLECTION_REGULATIONS="urban_regulations"
$env:CHROMA_COLLECTION_WORKFLOWS="urban_regulations"
$env:CHROMA_COLLECTION_MAP_METADATA="urban_regulations"
```

If these are not set, the adapter tries:
- regulations: `geo_regulations`, then `urban_regulations`
- workflows: `geo_workflows`, then `urban_regulations`
- map metadata: `geo_map_data`, then `urban_regulations`

If the original ingest script requires `GOOGLE_API_KEY`, you have two safe options:
- Use the original source ingest flow with a valid `GOOGLE_API_KEY`
- Use `scripts/ingest_geo_expert_local_chroma.py` for an offline/local fallback ingest path

## EO Cache

Use the source repo cache directory as a read-only image source:

```powershell
$env:GEO_EXPERT_EO_CACHE_DIR="C:\Users\34620\OneDrive\Desktop\geo-orchestrator\data\eo_cache"
```

The plugin will use EO cache images as local inputs when explicit imagery is missing.

## PostGIS

PostGIS remains read-only in plugin runtime. If your database has only default/tiger tables, use:

```powershell
py -3.11 scripts/plan_geo_expert_postgis_import.py
```

This script only produces a JSON import plan. It does not run `pg_restore`, `psql`, or `ogr2ogr`.
