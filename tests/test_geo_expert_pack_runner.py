from __future__ import annotations

from pathlib import Path

from plugins.geo_expert.satellite_workflows.pack_registry import load_pack
from plugins.geo_expert.satellite_workflows.pack_runner import run_pack
from plugins.geo_expert.user_data.user_data_ingest import import_user_data


def _dataset_for_pack(pack_id: str, tmp_path: Path) -> str:
    pack = load_pack(pack_id)["pack"]
    txt = tmp_path / f"{pack_id}.txt"
    txt.write_text(f"{pack_id} 使用者資料", encoding="utf-8")
    payload = import_user_data(pack=pack, source_files=[str(txt)])
    return str(payload["dataset_id"])


def test_pack_runner_real_estate_safe_run(tmp_path: Path) -> None:
    dataset_id = _dataset_for_pack("real_estate_insight", tmp_path)
    payload = run_pack("real_estate_insight", "幫我看這塊基地周邊環境", {"aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47}, "dataset_ids": [dataset_id]}, mode="safe_run")
    assert payload["success"] is True
    assert "satellite_evidence" in payload
    assert "user_rag" in payload
    assert "report" in payload


def test_pack_runner_geo_classroom_safe_run(tmp_path: Path) -> None:
    dataset_id = _dataset_for_pack("geo_classroom", tmp_path)
    payload = run_pack("geo_classroom", "做一份教學觀察單", {"aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47}, "dataset_ids": [dataset_id]}, mode="safe_run")
    assert payload["success"] is True
    assert payload["report"]["sections"]["Purpose"]


def test_pack_runner_public_inspection_safe_run(tmp_path: Path) -> None:
    dataset_id = _dataset_for_pack("public_inspection", tmp_path)
    payload = run_pack("public_inspection", "找出需要優先巡查的可疑地點", {"aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47}, "dataset_ids": [dataset_id]}, mode="safe_run")
    assert payload["success"] is True
    assert payload["analysis"]["domain_observations"]
