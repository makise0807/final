from __future__ import annotations

from pathlib import Path


def test_geo_expert_regulations_data() -> None:
    regulations_root = Path(__file__).resolve().parents[1] / "plugins" / "geo_expert" / "data" / "regulations"
    assert regulations_root.exists()
    files = [path for path in regulations_root.rglob("*") if path.is_file() and path.suffix.lower() in {".txt", ".md"}]
    assert files

