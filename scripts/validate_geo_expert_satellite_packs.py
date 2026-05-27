from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKS_PATH = ROOT / "plugins" / "geo_expert" / "data" / "satellite_packs" / "packs.json"
EXAMPLES_DIR = ROOT / "plugins" / "geo_expert" / "data" / "satellite_packs" / "examples"


def validate_packs() -> dict:
    payload = json.loads(PACKS_PATH.read_text(encoding="utf-8"))
    packs = payload.get("packs")
    if not isinstance(packs, list):
        raise ValueError("packs.json must contain a list under 'packs'.")
    required_fields = {
        "pack_id",
        "title",
        "title_zh",
        "target_users",
        "input_types",
        "default_report_type",
        "satellite_required",
        "rag_enabled",
        "user_data_collection",
        "system_collection",
        "workflow_steps",
        "report_sections",
        "safety_notes",
    }
    seen_ids: set[str] = set()
    errors: list[str] = []
    summaries: list[dict] = []
    for pack in packs:
        if not isinstance(pack, dict):
            errors.append("pack entry must be an object")
            continue
        pack_id = str(pack.get("pack_id") or "")
        if not pack_id:
            errors.append("pack missing pack_id")
            continue
        if pack_id in seen_ids:
            errors.append(f"duplicate_pack_id:{pack_id}")
        seen_ids.add(pack_id)
        missing = sorted(field for field in required_fields if field not in pack)
        if missing:
            errors.append(f"{pack_id}:missing_fields:{','.join(missing)}")
        if not str(pack.get("user_data_collection") or "").startswith("satellite_"):
            errors.append(f"{pack_id}:invalid_user_data_collection")
        if not isinstance(pack.get("workflow_steps"), list) or not pack.get("workflow_steps"):
            errors.append(f"{pack_id}:workflow_steps_empty")
        if not isinstance(pack.get("report_sections"), list) or not pack.get("report_sections"):
            errors.append(f"{pack_id}:report_sections_empty")
        example_path = EXAMPLES_DIR / f"{pack_id}.example.json"
        if not example_path.exists():
            errors.append(f"{pack_id}:example_missing")
        else:
            example_payload = json.loads(example_path.read_text(encoding="utf-8"))
            if example_payload.get("pack_id") != pack_id:
                errors.append(f"{pack_id}:example_pack_id_mismatch")
        summaries.append(
            {
                "pack_id": pack_id,
                "user_data_collection": pack.get("user_data_collection"),
                "example_exists": example_path.exists(),
                "report_sections_count": len(pack.get("report_sections") or []),
            }
        )
    if len(packs) != 10:
        errors.append(f"expected_10_packs_found_{len(packs)}")
    return {
        "success": not errors,
        "pack_count": len(packs),
        "packs": summaries,
        "errors": errors,
    }


def main() -> int:
    summary = validate_packs()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
