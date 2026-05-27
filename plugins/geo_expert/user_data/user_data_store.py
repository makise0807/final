from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def get_runtime_user_data_dir() -> Path:
    path = Path("outputs") / "geo_expert" / "user_data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _manifest_path() -> Path:
    return get_runtime_user_data_dir() / "manifest.json"


def load_dataset_manifest() -> dict[str, Any]:
    path = _manifest_path()
    if not path.exists():
        return {"datasets": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"datasets": []}
    datasets = payload.get("datasets")
    return {"datasets": datasets if isinstance(datasets, list) else []}


def save_dataset_manifest(payload: dict[str, Any]) -> None:
    _manifest_path().write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert_dataset(entry: dict[str, Any]) -> None:
    manifest = load_dataset_manifest()
    datasets = [item for item in manifest["datasets"] if isinstance(item, dict) and item.get("dataset_id") != entry.get("dataset_id")]
    datasets.append(entry)
    manifest["datasets"] = datasets
    save_dataset_manifest(manifest)


def list_datasets(pack_id: str | None = None) -> list[dict[str, Any]]:
    datasets = [item for item in load_dataset_manifest()["datasets"] if isinstance(item, dict)]
    if pack_id:
        return [item for item in datasets if item.get("pack_id") == pack_id]
    return datasets
