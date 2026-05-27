# Satellite Workflow Studio v0.2 MVP

Satellite Workflow Studio v0.2 MVP keeps the Geo Expert v1.5 plugin architecture intact and adds a deterministic multi-pack orchestration layer for safe-run satellite workflows.

## Status

- 10 packs are registered.
- 10 packs are safe-run capable.
- Every pack can emit a deterministic report template.
- Every pack can integrate runtime user data RAG from `outputs/geo_expert/user_data/`.
- No Hermes core changes.
- No OpenEO submit.
- No GeoTIFF download/export.

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

## User Data RAG Flow

1. Import user files with `geo_expert.user_data_import`
2. Data is stored only in `outputs/geo_expert/user_data/`
3. `pack_run` searches user data using:
   - `inputs.dataset_ids` when provided
   - the pack's default `user_data_collection` when not provided
4. If no user data exists, the pack report explicitly states that the user-data section is unavailable

## Run a Pack Example

```powershell
py -3.11 -X utf8 -c "from plugins.geo_expert.tools import pack_run_handler; print(pack_run_handler({'pack_id':'real_estate_insight','user_request':'請提供基地周邊環境與買方風險觀察','mode':'safe_run','inputs':{'aoi':{'west':120.7,'south':23.45,'east':120.72,'north':23.47}}}))"
```

## Run Example Inputs

Each pack includes a checked-in example JSON under:

- `plugins/geo_expert/data/satellite_packs/examples/`

You can validate the examples and pack metadata with:

```powershell
py -3.11 scripts\validate_geo_expert_satellite_packs.py
```

## Validation

The validation script checks:

- exactly 10 packs
- unique `pack_id`
- required pack fields
- `user_data_collection` naming
- non-empty `workflow_steps`
- non-empty `report_sections`
- matching example JSON for every pack

## How User Data Appears in Reports

Every MVP report includes:

- Purpose / 用途
- Input Summary / 輸入摘要
- Satellite Evidence / 衛星影像證據
- User Data Evidence / 使用者資料佐證
- Domain Observations / 領域觀察
- Risks or Caveats / 風險與限制
- Next Actions / 下一步

If no user data is available, the report says:

- `目前未提供使用者資料，因此本段僅使用衛星/系統資料。`

## Add the 11th Pack

1. Add a new pack entry to `plugins/geo_expert/data/satellite_packs/packs.json`
2. Add a matching example JSON in `plugins/geo_expert/data/satellite_packs/examples/`
3. Add deterministic observations to `plugins/geo_expert/satellite_workflows/pack_runner.py`
4. Reuse `report_templates.py`
5. Re-run:
   - `py -3.11 scripts\validate_geo_expert_satellite_packs.py`
   - Geo Expert test suite

## Current Limitations

- Satellite evidence is still limited by cache quality and AOI metadata availability
- User data RAG uses deterministic hash embedding by default
- Reports are deterministic templates, not formal domain opinions
- Missing data stays degraded and is not faked as real success
