# Geo Expert GEE Preview Smoke

## Purpose

This guide explains how to run a guarded Google Earth Engine thumbnail preview smoke test for Geo Expert without enabling exports, GeoTIFF downloads, or OpenEO submit flows.

## Safety Boundary

- Preview fetch is disabled by default.
- No OpenEO submit is performed.
- No GeoTIFF download is performed.
- No export pipeline is performed.
- Only PNG/JPG preview output is expected.

## Install Dependency

```powershell
py -3.11 -m pip install earthengine-api
```

## Authenticate Earth Engine

Use your normal Earth Engine login flow before running execute mode.

```powershell
py -3.11 -m ee authenticate
```

If you use a project-bound setup, make sure the same project is available to the active Python environment.

## Required Environment

```powershell
$env:GEO_EXPERT_ALLOW_SATELLITE_FETCH="1"
$env:GEO_EXPERT_GEE_ENABLED="1"
$env:GEO_EXPERT_GEE_PROJECT="<your-ee-project>"
```

Optional output override:

```powershell
$env:GEO_EXPERT_SATELLITE_OUTPUT_DIR="C:\path\to\preview_output"
```

## Prepare-Only Smoke

This is the safe default and does not fetch imagery:

```powershell
py -3.11 scripts\probe_geo_expert_gee_preview.py --bbox 120.7,23.45,120.72,23.47
```

## Execute Smoke

Only run this after the dependency and auth are ready:

```powershell
py -3.11 scripts\probe_geo_expert_gee_preview.py --execute --bbox 120.7,23.45,120.72,23.47
```

## Expected Output

On success, the probe will produce:

- a preview PNG or JPG
- a sidecar metadata JSON

The sidecar will still mark:

- `is_formal_analysis=false`
- `is_export=false`
- `requires_verification=true`
- `geotiff_download=false`

## Failure Modes

Structured degraded output is expected for:

- `satellite_fetch_disabled`
- `gee_dependency_missing`
- `gee_not_authenticated`
- `gee_preview_failed`

## Notes

- Successful GEE preview execute can later be used to create trustworthy AOI sidecars for EO cache matching.
- This smoke test is about safe preview retrieval only, not formal satellite analysis.
