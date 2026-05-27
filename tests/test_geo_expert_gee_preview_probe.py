from __future__ import annotations

import json
from pathlib import Path

import scripts.probe_geo_expert_gee_preview as probe_mod
from plugins.geo_expert.adapters import satellite_tools


def test_gee_preview_probe_prepare_only(monkeypatch, capsys) -> None:
    monkeypatch.setenv("GEO_EXPERT_ALLOW_SATELLITE_FETCH", "0")
    monkeypatch.setenv("GEO_EXPERT_GEE_ENABLED", "0")
    monkeypatch.setattr("sys.argv", ["probe"])
    assert probe_mod.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert "dependency_available" in payload
    assert "auth_available" in payload
    assert "fetch_enabled" in payload
    assert "execute_required_env" in payload
    assert payload["probe"]["prepare_only"] is True


def test_gee_preview_probe_execute_disabled(monkeypatch, capsys) -> None:
    monkeypatch.setenv("GEO_EXPERT_ALLOW_SATELLITE_FETCH", "0")
    monkeypatch.setenv("GEO_EXPERT_GEE_ENABLED", "1")
    monkeypatch.setattr("sys.argv", ["probe", "--execute"])
    assert probe_mod.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["fetch_enabled"] is False
    assert payload["probe"]["error"] == "satellite_acquisition_disabled"


def test_gee_preview_probe_mocked_success(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("GEO_EXPERT_ALLOW_SATELLITE_FETCH", "1")
    monkeypatch.setenv("GEO_EXPERT_GEE_ENABLED", "1")
    monkeypatch.setenv("GEO_EXPERT_EO_CACHE_DIR", str(tmp_path))

    def fake_acquire(**_kwargs):
        preview = tmp_path / "preview.png"
        preview.write_bytes(b"png")
        sidecar = preview.with_suffix(".json")
        sidecar.write_text(json.dumps({"is_formal_analysis": False, "is_export": False, "requires_verification": True}), encoding="utf-8")
        return {
            "success": True,
            "service": "gee_preview",
            "image_path": str(preview),
            "sidecar_path": str(sidecar),
            "is_formal_analysis": False,
            "is_export": False,
            "geotiff_download": False,
        }

    monkeypatch.setattr(satellite_tools, "acquire_satellite_preview", fake_acquire)
    monkeypatch.setattr(probe_mod, "acquire_satellite_preview", fake_acquire)
    monkeypatch.setattr("sys.argv", ["probe", "--execute"])
    assert probe_mod.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["planned_bbox"]
    assert payload["next_action"]
    assert payload["probe"]["success"] is True
    assert payload["probe"]["geotiff_download"] is False
