from __future__ import annotations

from pathlib import Path


FORBIDDEN = [
    "Export.image.toDrive",
    "Export.image.toCloudStorage",
    "Export.table.toDrive",
    "Export.table.toCloudStorage",
    ".create_job(",
    "submit_process_graph",
    ".start_job(",
    "docker compose up",
    "pg_restore",
]


def test_geo_expert_no_high_risk_auto_execution() -> None:
    root = Path("C:/Users/34620/OneDrive/Desktop/final/plugins/geo_expert")
    runtime_files = [path for path in root.rglob("*.py") if "tests" not in path.parts]
    for path in runtime_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for forbidden in FORBIDDEN:
            assert forbidden not in text, f"{forbidden} found in {path}"
