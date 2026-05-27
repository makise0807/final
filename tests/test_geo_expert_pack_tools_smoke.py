from __future__ import annotations

import json
from pathlib import Path

from plugins.geo_expert.tools import (
    pack_list_handler,
    pack_run_handler,
    pack_show_handler,
    user_data_import_handler,
    user_data_rag_answer_handler,
    user_data_search_handler,
)
from plugins.geo_expert.user_data import user_data_store


def test_pack_tools_smoke_all_packs_safe_run(tmp_path: Path, monkeypatch) -> None:
    runtime_dir = tmp_path / "user_data_runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(user_data_store, "get_runtime_user_data_dir", lambda: runtime_dir)
    listed = json.loads(pack_list_handler({}))
    assert listed["success"] is True
    assert len(listed["packs"]) == 10
    for pack in listed["packs"]:
        pack_id = pack["pack_id"]
        shown = json.loads(pack_show_handler({"pack_id": pack_id}))
        assert shown["success"] is True
        payload = json.loads(
            pack_run_handler(
                {
                    "pack_id": pack_id,
                    "user_request": f"Run {pack_id} pack.",
                    "mode": "safe_run",
                    "inputs": {"aoi": {"west": 120.7, "south": 23.45, "east": 120.72, "north": 23.47}},
                }
            )
        )
        assert payload["success"] is True
        assert payload["satellite_evidence"]
        assert payload["user_rag"]
        assert payload["analysis"]
        assert payload["report"]
        assert payload["user_rag"]["status"] == "no_user_data_available"


def test_user_data_handlers_smoke(tmp_path: Path, monkeypatch) -> None:
    runtime_dir = tmp_path / "user_data_runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(user_data_store, "get_runtime_user_data_dir", lambda: runtime_dir)
    source = tmp_path / "notes.txt"
    source.write_text("Parcel notes with road access and open space reference.", encoding="utf-8")
    imported = json.loads(
        user_data_import_handler(
            {
                "pack_id": "real_estate_insight",
                "source_files": [str(source)],
            }
        )
    )
    assert imported["success"] is True
    dataset_id = imported["dataset_id"]

    search = json.loads(
        user_data_search_handler(
            {
                "pack_id": "real_estate_insight",
                "query": "road access open space",
                "dataset_ids": [dataset_id],
            }
        )
    )
    assert search["hits"]
    assert search["citations"]

    no_data = json.loads(
        user_data_rag_answer_handler(
            {
                "pack_id": "real_estate_insight",
                "query": "No dataset should return no data.",
                "dataset_ids": ["missing-dataset"],
            }
        )
    )
    assert no_data["status"] == "no_user_data_available"
