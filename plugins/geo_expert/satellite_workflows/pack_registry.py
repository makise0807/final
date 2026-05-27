from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PACKS_PATH = Path(__file__).resolve().parents[1] / "data" / "satellite_packs" / "packs.json"


def load_packs() -> list[dict[str, Any]]:
    payload = json.loads(PACKS_PATH.read_text(encoding="utf-8"))
    packs = payload.get("packs")
    return [item for item in packs if isinstance(item, dict)] if isinstance(packs, list) else []


def list_packs() -> dict[str, Any]:
    packs = load_packs()
    return {"success": True, "packs": packs, "count": len(packs)}


def load_pack(pack_id: str) -> dict[str, Any]:
    for pack in load_packs():
        if str(pack.get("pack_id")) == str(pack_id):
            return {"success": True, "pack": pack}
    return {"success": False, "error": "pack_not_found", "pack_id": pack_id}
