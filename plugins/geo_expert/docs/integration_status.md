# Geo Expert Integration Status

## Integrated Into Current 6 Tools

- Local fixture image loading
- Mock detector path
- `detections.geojson` output
- `overlay_preview.png` output
- `report.md` output
- Workflow metadata lookup for `WF-001`
- Safety boundaries for read-only preliminary mode

## Migrated As Optional Adapters

- `adapters/eo_tools.py`
- `adapters/spatial_tools.py`
- `adapters/rag_tools.py`
- `data/regulations/`
- `data/workflow_db/expert_workflows.json`
- `docs/README_交接說明.md`

## Disabled By Default External Adapters

- OpenEO
- PostGIS
- ChromaDB RAG
- Docker-managed database startup
- GeoTIFF download
- Real OpenEO submit
- Export flows

## Design Notes

- No external adapter connects on import.
- Missing dependencies return structured JSON-like dict results instead of crashing.
- Existing direct handler behavior remains fixture-first and does not depend on PostGIS, ChromaDB, or OpenEO.
