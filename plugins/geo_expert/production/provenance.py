from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_provenance(path_like: str, *, source_type: str, generated_by: str) -> dict[str, Any]:
    path = Path(path_like)
    return {
        "source_type": source_type,
        "source_path": str(path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sha256": _sha256(path),
        "generated_by": generated_by,
        "is_formal_analysis": False,
    }


def collect_data_provenance(result: dict[str, Any]) -> list[dict[str, Any]]:
    provenance: list[dict[str, Any]] = []
    sat = dict(result.get("satellite_evidence") or {})
    if sat.get("image_path"):
        item = _file_provenance(str(sat["image_path"]), source_type="satellite_preview", generated_by=str(sat.get("service") or sat.get("provider") or "satellite"))
        item["aoi"] = sat.get("aoi") or result.get("inputs", {}).get("aoi")
        provenance.append(item)
    for step in result.get("steps") or []:
        evidence = dict(step.get("evidence") or {})
        if evidence.get("selected_collection"):
            provenance.append(
                {
                    "source_type": "chromadb_collection",
                    "collection": evidence.get("selected_collection"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "generated_by": step.get("adapter"),
                    "is_formal_analysis": False,
                }
            )
        if evidence.get("service") == "postgis" or evidence.get("used_real_service") and step.get("adapter") == "spatial":
            provenance.append(
                {
                    "source_type": "postgis_table",
                    "table": evidence.get("target_table") or evidence.get("table_name"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "generated_by": "postgis",
                    "srid": evidence.get("srid"),
                    "is_formal_analysis": False,
                }
            )
    return provenance
