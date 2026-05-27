# Geo Expert Production Readiness

Geo Expert v1.6 adds a production-readiness framework for expert review drafts, not a claim of full production completion.

## Included

- Run manifest generation
- Data provenance summary
- Readiness scoring
- Runtime audit log in `outputs/geo_expert/audit_log/`
- Cache policy listing
- Approval gate for external or high-cost actions
- Structured service health checks

## Current Position

- Readiness level is intentionally partial or blocked when major gaps remain.
- Missing spatial layers, general-purpose YOLO, and deterministic hash embeddings prevent a "fully production-grade" claim.
- Human review is still required for legal, regulatory, and enforcement-facing outputs.

## Safety Boundaries

- OpenEO submit is disabled by default.
- GeoTIFF download/export is disabled by default.
- Destructive PostGIS import must remain approval-gated.
- Outputs and runtime caches stay outside Git tracking.
