from __future__ import annotations

import json
from pathlib import Path

from plugins.geo_expert.adapters.eo_tools import list_eo_cache_images


def test_eo_cache_probe_unconfigured(monkeypatch) -> None:
    monkeypatch.delenv("GEO_EXPERT_EO_CACHE_DIR", raising=False)
    payload = list_eo_cache_images()
    assert payload["success"] is False
    assert payload["error"] == "eo_cache_unconfigured"


def test_eo_cache_probe_missing_dir(monkeypatch, tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    monkeypatch.setenv("GEO_EXPERT_EO_CACHE_DIR", str(missing))
    payload = list_eo_cache_images()
    assert payload["success"] is False
    assert payload["error"] == "eo_cache_missing"


def test_eo_cache_probe_success(monkeypatch, tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    (tmp_path / "sample.json").write_text(json.dumps({"aoi": {"west": 1, "south": 2, "east": 3, "north": 4}}), encoding="utf-8")
    monkeypatch.setenv("GEO_EXPERT_EO_CACHE_DIR", str(tmp_path))
    payload = list_eo_cache_images()
    assert payload["success"] is True
    assert payload["image_count"] == 1
    assert payload["images"][0]["source"] == "eo_cache"
