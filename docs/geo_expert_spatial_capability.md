# Geo Expert Spatial Capability

Geo Expert v1.6 keeps the current PostGIS posture explicit instead of pretending every expert layer is available.

## Current Capability Profile

- cadastral: available
- building: missing_data_required
- river: missing_data_required
- hazard: missing_data_required
- landuse: missing_data_required
- ecology: missing_data_required
- zoning_change: missing_data_required

## What This Means

- parcel-centric workflows can use real PostGIS evidence today
- workflows that require missing layers degrade with a clear reason
- degraded spatial steps should never be described as complete spatial success

## Required Data For Full Analysis

- building footprints
- river / floodplain polygons
- hazard polygons
- slope / hillside layers
- landuse / zoning layers
- ecology / habitat layers
- zoning change proposal boundaries

## Validation Path

1. import the missing layer into PostGIS manually
2. update `plugins/geo_expert/data/spatial/layer_aliases.json`
3. run `py -3.11 scripts\probe_geo_expert_postgis.py`
4. re-run the workflow and confirm `used_real_service=true`
