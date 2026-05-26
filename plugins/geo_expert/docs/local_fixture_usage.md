# Local Fixture Image Usage

This document explains how to use local fixture images with Geo Expert tools.

## Purpose

Local fixture images provide a stable, reproducible image source for testing Geo Expert workflows without relying on Google Earth Engine or external network calls.

The local fixture flow is useful for:

- deterministic overlay testing
- local demo runs
- unit tests
- verifying AOI alignment
- avoiding GEE authentication or dataset availability issues

## Folder Format

Each fixture case should be placed under:

```text
data/geo_fixtures/<case_id>/