from __future__ import annotations

from pathlib import Path

from plugins.geo_expert.satellite_workflows.pack_registry import list_packs, load_pack
from plugins.geo_expert.satellite_workflows.pack_runner import run_pack
from plugins.geo_expert.user_data.user_data_ingest import import_user_data
from plugins.geo_expert.user_data import user_data_store


def _dataset_for_pack(pack_id: str, tmp_path: Path) -> str:
    pack = load_pack(pack_id)["pack"]
    txt = tmp_path / f"{pack_id}.txt"
    txt.write_text(f"{pack_id} sample user evidence for deterministic pack testing.", encoding="utf-8")
    payload = import_user_data(pack=pack, source_files=[str(txt)])
    return str(payload["dataset_id"])


def test_all_packs_safe_run_with_dataset(tmp_path: Path, monkeypatch) -> None:
    runtime_dir = tmp_path / "user_data_runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(user_data_store, "get_runtime_user_data_dir", lambda: runtime_dir)
    for pack in list_packs()["packs"]:
        pack_id = str(pack["pack_id"])
        dataset_id = _dataset_for_pack(pack_id, tmp_path)
        payload = run_pack(
            pack_id,
            f"Run {pack_id} in safe mode.",
            {
                "aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47},
                "dataset_ids": [dataset_id],
            },
            mode="safe_run",
        )
        assert payload["success"] is True
        assert payload["pack_id"] == pack_id
        assert payload["status"] in {"success", "degraded"}
        assert payload["satellite_evidence"]
        assert payload["user_rag"]
        assert payload["analysis"]["observations"]
        assert len(payload["analysis"]["observations"]) >= 5
        assert payload["analysis"]["risks"]
        assert payload["analysis"]["next_actions"]
        assert payload["report"]["sections"]
        assert payload["next_actions"]


def test_pack_runner_without_user_data_is_grounded(tmp_path: Path, monkeypatch) -> None:
    runtime_dir = tmp_path / "user_data_runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(user_data_store, "get_runtime_user_data_dir", lambda: runtime_dir)
    payload = run_pack(
        "real_estate_insight",
        "Run without user data.",
        {"aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47}},
        mode="safe_run",
    )
    assert payload["success"] is True
    assert payload["user_rag"]["status"] == "no_user_data_available"
    assert "目前未提供使用者資料" in str(payload["report"]["sections_map"]["User Data Evidence / 使用者資料佐證"]["summary"])
