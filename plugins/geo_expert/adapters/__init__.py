"""Optional external-service adapters for the geo_expert plugin.

These modules are import-safe by design:
- no OpenEO login on import
- no PostGIS connection on import
- no ChromaDB connection on import
- no Docker startup on import

Each adapter exposes lightweight status helpers plus explicit functions that
perform dependency checks only when called.
"""

