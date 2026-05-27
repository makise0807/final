from __future__ import annotations

from pathlib import Path

from plugins.geo_expert.satellite_workflows.pack_registry import load_pack
from plugins.geo_expert.user_data.user_data_ingest import import_user_data


def test_user_data_ingest_txt_md_json_csv(tmp_path: Path) -> None:
    pack = load_pack("real_estate_insight")["pack"]
    txt = tmp_path / "notes.txt"
    md = tmp_path / "brief.md"
    js = tmp_path / "data.json"
    csv_file = tmp_path / "table.csv"
    txt.write_text("附近有學校與公園", encoding="utf-8")
    md.write_text("# 場勘\n周邊道路寬度待確認", encoding="utf-8")
    js.write_text('{"owner":"A","risk":"medium"}', encoding="utf-8")
    csv_file.write_text("item,value\nroad,wide\npark,yes\n", encoding="utf-8")
    payload = import_user_data(pack=pack, source_files=[str(txt), str(md), str(js), str(csv_file)])
    assert payload["success"] is True
    assert payload["chunk_count"] > 0
    assert "outputs\\geo_expert\\user_data" in payload["runtime_dir"] or "outputs/geo_expert/user_data" in payload["runtime_dir"]


def test_user_data_ingest_no_data_is_structured_degraded() -> None:
    pack = load_pack("real_estate_insight")["pack"]
    payload = import_user_data(pack=pack, source_files=[])
    assert payload["success"] is False
    assert payload["error"] == "no_source_files"


def test_user_data_runtime_copy_not_in_repo_path(tmp_path: Path) -> None:
    pack = load_pack("real_estate_insight")["pack"]
    txt = tmp_path / "notes.txt"
    txt.write_text("外部資料", encoding="utf-8")
    payload = import_user_data(pack=pack, source_files=[str(txt)])
    assert payload["success"] is True
    assert all("plugins\\geo_expert\\data" not in item and "plugins/geo_expert/data" not in item for item in payload["stored_files"])
