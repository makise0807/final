# Geo Expert OpenEO / GeoTIFF Pipeline

Geo Expert v1.6 adds an approval-gated OpenEO acquisition layer.

## Modes

- `prepare_only`: default, plan only, no submit, no download
- `cache_only`: reuse matching runtime GeoTIFF metadata if present
- `approved_run`: only allowed when all approval conditions are met

## Approval Conditions

All of the following must be true before external submission or download is allowed:

- `GEO_EXPERT_ALLOW_OPENEO_SUBMIT=1`
- `GEO_EXPERT_ALLOW_GEOTIFF_DOWNLOAD=1`
- `approved=true`
- `mode=approved_run`

## Important Limits

- No automatic OpenEO submit by default
- No automatic GeoTIFF download/export by default
- No large raster files should be committed into the repo
- Tests do not require a real OpenEO account
