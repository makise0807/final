from __future__ import annotations

from pathlib import Path


FORBIDDEN_PATTERNS = [
    "Export.image.toDrive",
    "Export.image.toCloudStorage",
    "Export.table.toDrive",
    "Export.table.toCloudStorage",
    ".create_job(",
    "submit_process_graph",
    ".start_job(",
    "docker compose up",
    "pg_restore",
    "save_result(",
    ").download",
]


def test_geo_expert_python_surface_has_no_forbidden_external_patterns() -> None:
    plugin_root = Path(__file__).resolve().parents[1] / "plugins" / "geo_expert"
    checked_files: list[Path] = []

    for path in plugin_root.rglob("*.py"):
        if "tests" in path.parts or "__pycache__" in path.parts:
            continue
        checked_files.append(path)
        content = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in FORBIDDEN_PATTERNS:
            assert pattern not in content, f"{pattern} found in {path}"

    assert checked_files
