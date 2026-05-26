from __future__ import annotations

import json
from pathlib import Path

import scripts.backfill_geo_expert_eo_cache_metadata as backfill_mod


def test_backfill_dry_run_does_not_write(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "sample.png").write_bytes(b"img")
    payload = backfill_mod.backfill_sidecars(cache_dir=cache_dir, dry_run=True)
    assert payload["success"] is True
    assert payload["sidecars_created"] == 1
    assert not (cache_dir / "sample.json").exists()


def test_backfill_without_aoi_does_not_invent_bbox(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    image_path = cache_dir / "sample.png"
    image_path.write_bytes(b"img")
    backfill_mod.backfill_sidecars(cache_dir=cache_dir, dry_run=False)
    payload = json.loads((cache_dir / "sample.json").read_text(encoding="utf-8"))
    assert payload["aoi"] is None
    assert payload["match_quality"] == "unknown_aoi"


def test_backfill_with_manual_aoi_writes_bbox(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    image_path = cache_dir / "sample.png"
    image_path.write_bytes(b"img")
    backfill_mod.backfill_sidecars(
        cache_dir=cache_dir,
        dry_run=False,
        aoi={"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47},
        workflow_hint="WF-002",
        case_id="sample_case",
    )
    payload = json.loads((cache_dir / "sample.json").read_text(encoding="utf-8"))
    assert payload["aoi"]["west"] == 120.7
    assert payload["workflow_hint"] == "WF-002"
    assert payload["case_id"] == "sample_case"
    assert payload["match_quality"] == "precise_aoi"


def test_existing_sidecar_is_not_overwritten_unless_requested(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    image_path = cache_dir / "sample.png"
    image_path.write_bytes(b"img")
    sidecar = cache_dir / "sample.json"
    sidecar.write_text(json.dumps({"source": "eo_cache", "aoi": None, "workflow_hint": "WF-999"}), encoding="utf-8")
    backfill_mod.backfill_sidecars(cache_dir=cache_dir, dry_run=False, workflow_hint="WF-002")
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload["workflow_hint"] == "WF-999"
    backfill_mod.backfill_sidecars(cache_dir=cache_dir, dry_run=False, workflow_hint="WF-002", overwrite=True)
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload["workflow_hint"] == "WF-002"


def test_backfill_can_use_reference_index_for_aoi(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    image_path = cache_dir / "gee_s2_abc123.png"
    image_path.write_bytes(b"img")
    index_payload = {
        "images": [
            {
                "filename": image_path.name,
                "aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47},
                "workflow_hint": "WF-002",
                "provider": "gee_preview",
            }
        ]
    }
    index_entries = backfill_mod._normalize_reference_entries(index_payload)
    payload = backfill_mod.backfill_sidecars(cache_dir=cache_dir, dry_run=False, index_entries=index_entries)
    assert payload["with_aoi"] == 1
    sidecar = json.loads((cache_dir / "gee_s2_abc123.json").read_text(encoding="utf-8"))
    assert sidecar["aoi"]["west"] == 120.7
    assert sidecar["match_quality"] == "precise_aoi"
