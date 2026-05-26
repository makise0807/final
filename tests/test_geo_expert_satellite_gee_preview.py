from __future__ import annotations

from plugins.geo_expert.adapters import satellite_tools


def test_geo_expert_satellite_gee_preview_disabled_by_default(monkeypatch) -> None:
    monkeypatch.setenv("GEO_EXPERT_ALLOW_SATELLITE_FETCH", "0")
    monkeypatch.setenv("GEO_EXPERT_GEE_ENABLED", "0")
    payload = satellite_tools.acquire_satellite_preview(
        aoi={"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47},
        mode="preview",
        provider="gee",
    )
    assert payload["success"] is False
    assert payload["status"] == "degraded"
    assert payload["error"] == "satellite_acquisition_disabled"


def test_geo_expert_satellite_gee_preview_success_with_monkeypatch(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GEO_EXPERT_ALLOW_SATELLITE_FETCH", "1")
    monkeypatch.setenv("GEO_EXPERT_GEE_ENABLED", "1")
    monkeypatch.setenv("GEO_EXPERT_EO_CACHE_DIR", str(tmp_path))

    def fake_fetch(_request):
        return {
            "success": True,
            "provider": "gee",
            "mode": "thumbnail",
            "thumbnail_url": "https://example.com/thumb.png",
            "warnings": [],
            "limitations": ["preview only"],
        }

    def fake_download(_url, target_path):
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(b"png")

    from plugins.geo_expert.geo_database import image_provider_gee

    monkeypatch.setattr(image_provider_gee, "gee_fetch_thumbnail_preview", fake_fetch)
    monkeypatch.setattr(satellite_tools, "_download_preview_image", fake_download)
    payload = satellite_tools.acquire_satellite_preview(
        aoi={"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47},
        workflow_id="WF-002",
        mode="preview",
        provider="gee",
    )
    assert payload["success"] is True
    assert payload["service"] == "gee_preview"
    assert payload["used_real_service"] is True
    assert payload["is_formal_analysis"] is False
    assert payload["geotiff_download"] is False
