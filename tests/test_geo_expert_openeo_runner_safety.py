from __future__ import annotations

from plugins.geo_expert.openeo_acquisition import run_openeo_acquisition


REQUEST = {
    "aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47},
    "date_range": {"start": "2025-01-01", "end": "2025-01-31"},
    "bands": ["B04", "B03", "B02", "B08"],
}


def test_approved_run_without_env_requires_approval(monkeypatch) -> None:
    monkeypatch.delenv("GEO_EXPERT_ALLOW_OPENEO_SUBMIT", raising=False)
    monkeypatch.delenv("GEO_EXPERT_ALLOW_GEOTIFF_DOWNLOAD", raising=False)
    result = run_openeo_acquisition({**REQUEST, "mode": "approved_run", "approved": False})
    assert result["status"] == "approval_required"


def test_prepare_only_does_not_submit() -> None:
    result = run_openeo_acquisition({**REQUEST, "mode": "prepare_only"})
    assert result["mode"] == "prepare_only"
    assert result["approval_required"] is True
