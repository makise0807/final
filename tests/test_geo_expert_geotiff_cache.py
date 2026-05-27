from __future__ import annotations

import json
from pathlib import Path

from plugins.geo_expert.openeo_acquisition import list_geotiff_cache
from plugins.geo_expert.openeo_acquisition.geotiff_cache import write_geotiff_sidecar


def test_geotiff_cache_sidecar_metadata(tmp_path: Path) -> None:
    tiff_path = tmp_path / "sample.tif"
    tiff_path.write_bytes(b"fake")
    result = write_geotiff_sidecar(
        artifact_id="artifact-1",
        path=str(tiff_path),
        aoi={"west": 1, "south": 2, "east": 3, "north": 4},
        date_range={"start": "2025-01-01", "end": "2025-01-31"},
        bands=["B04"],
        provider="example",
    )
    metadata = json.loads(Path(result["sidecar_path"]).read_text(encoding="utf-8"))
    assert metadata["artifact_id"] == "artifact-1"
    assert metadata["requires_verification"] is True


def test_geotiff_cache_list_is_structured() -> None:
    listing = list_geotiff_cache()
    assert listing["success"] is True
    assert "items" in listing
