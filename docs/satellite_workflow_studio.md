# Satellite Workflow Studio v0.1

Satellite Workflow Studio adds a deterministic pack orchestration layer on top of Geo Expert v1.5 without changing Hermes core.

## Packs

1. `real_estate_insight`
2. `geo_classroom`
3. `public_inspection`
4. `agriculture_monitor`
5. `disaster_rapid_scan`
6. `esg_environment`
7. `outdoor_safety`
8. `media_investigation`
9. `urban_planning`
10. `climate_land_change`

## User Data RAG

Runtime user data can be imported into a pack-specific store:

```powershell
py -3.11 -X utf8 -c "from plugins.geo_expert.tools import user_data_import_handler; print(user_data_import_handler({'pack_id':'real_estate_insight','source_files':['C:\\temp\\notes.txt']}))"
```

The runtime store lives under:

- `outputs/geo_expert/user_data/`

This path is ignored by git and should never be committed.

## Run a Pack

```powershell
py -3.11 -X utf8 -c "from plugins.geo_expert.tools import pack_run_handler; print(pack_run_handler({'pack_id':'real_estate_insight','user_request':'幫我看這塊基地周邊環境','inputs':{'aoi':{'west':120.7,'south':23.45,'east':120.72,'north':23.47}},'mode':'safe_run'}))"
```

## Data Safety Boundary

- No Hermes core changes
- No OpenEO submit
- No GeoTIFF download/export
- No model training
- No hallucinated answers when user data is missing
- No committing runtime user data

## Add the 11th Pack

1. Add a new pack entry to `plugins/geo_expert/data/satellite_packs/packs.json`
2. Assign a unique `user_data_collection`
3. Define `report_sections` and `safety_notes`
4. Reuse the deterministic `pack_runner.py` path
5. Add tests for registry and at least one `pack_run` scenario
