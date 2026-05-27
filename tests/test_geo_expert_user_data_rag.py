from __future__ import annotations

from pathlib import Path

from plugins.geo_expert.satellite_workflows.pack_registry import load_pack
from plugins.geo_expert.user_data.user_data_ingest import import_user_data
from plugins.geo_expert.user_data.user_data_rag import answer_user_data_question, search_user_data


def test_user_data_rag_import_search_and_answer(tmp_path: Path) -> None:
    pack = load_pack("real_estate_insight")["pack"]
    txt = tmp_path / "notes.txt"
    txt.write_text(
        "This site is near open space and water frontage. Buyer concerns include flooding and slope access.",
        encoding="utf-8",
    )
    imported = import_user_data(pack=pack, source_files=[str(txt)])
    assert imported["success"] is True

    search = search_user_data(
        "real_estate_insight",
        "water frontage buyer risk",
        dataset_ids=[imported["dataset_id"]],
    )
    assert search["results"]
    assert search["results"][0]["citation"]

    answer = answer_user_data_question(
        "real_estate_insight",
        "What risks should a buyer verify?",
        dataset_ids=[imported["dataset_id"]],
    )
    assert answer["success"] is True
    assert answer["answer"]
    assert answer["citations"]


def test_user_data_rag_no_hallucination_when_empty() -> None:
    answer = answer_user_data_question(
        "real_estate_insight",
        "Do not invent an answer when there is no data.",
        dataset_ids=["missing-dataset"],
    )
    assert answer["status"] == "degraded"
    assert answer["error"] == "no_user_data_available"
    assert answer["answer"] is None
