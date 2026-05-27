# Geo Expert PostGIS Layer Import Guide

## Goal

Geo Expert currently has parcel-centric PostGIS coverage. This guide explains how to plan the remaining layer imports without dropping the database or faking resolved aliases.

## Current State

- Resolved aliases: `4`
- Missing aliases: `9`
- Current real coverage is parcel-based only

## Supported Input Formats

- SHP
- GeoJSON
- GPKG

## Do Not Do This

- Do not drop the database
- Do not run destructive restore blindly
- Do not mark aliases as resolved before the real layer exists

## Missing Layers and Required Data

| Alias | Required data type |
| --- | --- |
| `building_layer` | building footprints |
| `river_zone` | river / floodplain polygon |
| `agricultural_zone` | agricultural zoning / land-use zone |
| `hazard_zone` | hazard potential polygon |
| `slope_layer` | slope / hillside polygon or raster-derived vector |
| `ecology_network_layer` | ecological corridor / green network polygon |
| `sensitive_habitat_layer` | sensitive habitat polygon |
| `landuse_layer` | land-use zoning |
| `zoning_change_layer` | zoning change proposal boundaries |

## Import Planning

Generate a read-only import plan first:

```powershell
py -3.11 scripts\plan_geo_expert_postgis_import.py
```

The plan will report:

- `required_data_type`
- `acceptable_formats`
- `suggested_source_keywords`
- `example_target_table`
- `ogr2ogr_command_template`
- `validation_query`

If the source file does not exist, the plan will keep:

- `status=source_missing`

## Example Import Pattern

After you have a real layer file and explicit approval, follow the command template from the plan. For vector sources this will usually look like:

```powershell
ogr2ogr -f PostgreSQL PG:"host=localhost port=5433 dbname=geodb user=geouser" "<SOURCE_FILE>" -nln public.<target_layer> -lco GEOMETRY_NAME=geom -overwrite
```

## After Import

1. Update `plugins/geo_expert/data/spatial/layer_aliases.json`
2. Point the alias at the real imported table
3. Re-run:

```powershell
py -3.11 scripts\probe_geo_expert_postgis.py
```

4. Confirm the layer appears in:

- `aliases_resolved`
- `geometry_columns`

5. Re-run workflow validation and confirm the relevant spatial step can reach `used_real_service=true`

## Validation

Use the validation query reported by the plan after import, for example:

```sql
SELECT COUNT(*) AS row_count FROM public.building_layer;
```

This guide is planning-only. It does not authorize import commands by itself.
