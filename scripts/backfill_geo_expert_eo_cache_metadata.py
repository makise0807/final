from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def _normalize_aoi(raw: str | None) -> dict[str, float] | None:
    if not raw:
        return None
    parts = [item.strip() for item in str(raw).split(",")]
    if len(parts) != 4:
        return None
    try:
        west, south, east, north = [float(item) for item in parts]
    except Exception:
        return None
    if west >= east or south >= north:
        return None
    return {"west": west, "south": south, "east": east, "north": north}


def _infer_provider(filename: str) -> str:
    lowered = filename.lower()
    if lowered.startswith("gee_") or "gee" in lowered or lowered.startswith("s2_") or "sentinel" in lowered:
        return "gee_preview"
    if lowered.startswith("mock_"):
        return "mock_preview"
    return "unknown_or_gee_preview"


def _infer_workflow_hint(filename: str) -> str | None:
    lowered = filename.lower()
    for workflow_id, token in (
        ("WF-001", "factory"),
        ("WF-002", "slope"),
        ("WF-004", "river"),
        ("WF-005", "solar"),
        ("WF-008", "tod"),
        ("WF-009", "hazard"),
        ("WF-010", "eco"),
    ):
        if token in lowered:
            return workflow_id
    return None


def _infer_case_id(filename: str) -> str | None:
    lowered = filename.lower()
    if "sample_taichung_case" in lowered:
        return "sample_taichung_case"
    return None


def _bbox_to_hash(bbox: dict[str, float], date_start: str, date_end: str) -> str:
    key = f"{bbox['west']:.4f}_{bbox['south']:.4f}_{bbox['east']:.4f}_{bbox['north']:.4f}_{date_start}_{date_end}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()[:12]


def _validate_sidecar(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    if payload.get("source") != "eo_cache":
        warnings.append("source should be eo_cache")
    aoi = payload.get("aoi")
    if aoi is not None:
        try:
            west = float(aoi["west"])
            south = float(aoi["south"])
            east = float(aoi["east"])
            north = float(aoi["north"])
            if west >= east or south >= north:
                warnings.append("invalid_aoi")
        except Exception:
            warnings.append("invalid_aoi")
    return (not warnings), warnings


def _build_sidecar(
    image_path: Path,
    *,
    aoi: dict[str, float] | None,
    workflow_hint: str | None,
    case_id: str | None,
    provider: str | None = None,
    confidence: float | None = None,
    match_quality: str | None = None,
    extra_warnings: list[str] | None = None,
) -> dict[str, Any]:
    has_aoi = aoi is not None
    has_workflow = bool(workflow_hint)
    warnings = [] if has_aoi else ["AOI metadata unavailable; this image cannot be used for precise AOI matching."]
    warnings.extend(str(item) for item in (extra_warnings or []) if str(item).strip())
    return {
        "source": "eo_cache",
        "provider": provider or _infer_provider(image_path.name),
        "case_id": case_id,
        "workflow_hint": workflow_hint,
        "aoi": aoi,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "is_formal_analysis": False,
        "is_export": False,
        "requires_verification": True,
        "match_quality": match_quality or ("precise_aoi" if has_aoi else ("workflow_hint_only" if has_workflow else "unknown_aoi")),
        "confidence": confidence if confidence is not None else (0.95 if has_aoi else (0.6 if has_workflow else 0.2)),
        "warnings": warnings,
    }


def _candidate_keys(path: Path) -> set[str]:
    stem = path.stem.lower()
    return {
        str(path).lower(),
        str(path.resolve()).lower(),
        path.name.lower(),
        stem,
    }


def _load_jsonish(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _normalize_reference_entries(payload: Any) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    raw_items: list[Any]
    if isinstance(payload, dict):
        raw_items = payload.get("images") or payload.get("entries") or payload.get("items") or []
    elif isinstance(payload, list):
        raw_items = payload
    else:
        raw_items = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        for raw_key in (
            item.get("image_path"),
            item.get("local_path"),
            item.get("thumb_local_path"),
            item.get("filename"),
            item.get("path"),
        ):
            if not raw_key:
                continue
            key = str(raw_key).strip().lower()
            entries[key] = item
            stem = Path(str(raw_key)).stem.lower()
            if stem:
                entries.setdefault(stem, item)
    return entries


def _normalize_gee_log_entries(payload: Any) -> dict[str, dict[str, Any]]:
    entries = _normalize_reference_entries(payload)
    raw_items: list[Any]
    if isinstance(payload, dict):
        raw_items = payload.get("entries") or payload.get("items") or payload.get("sessions") or []
    elif isinstance(payload, list):
        raw_items = payload
    else:
        raw_items = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        aoi = item.get("bbox") or item.get("aoi")
        if not isinstance(aoi, dict):
            continue
        date_start = str(item.get("date_start") or "").strip()
        date_end = str(item.get("date_end") or "").strip()
        if not (date_start and date_end):
            continue
        normalized = _normalize_aoi(",".join(str(aoi.get(k)) for k in ("west", "south", "east", "north")))
        if normalized is None:
            continue
        hashed = f"gee_s2_{_bbox_to_hash(normalized, date_start, date_end)}"
        entries.setdefault(hashed.lower(), item)
    return entries


def _sidecar_from_reference(image_path: Path, entry: dict[str, Any]) -> dict[str, Any]:
    raw_aoi = entry.get("aoi") or entry.get("bbox")
    aoi = None
    if isinstance(raw_aoi, dict):
        joined = ",".join(str(raw_aoi.get(key)) for key in ("west", "south", "east", "north"))
        aoi = _normalize_aoi(joined)
    workflow_hint = entry.get("workflow_hint") or entry.get("workflow_id") or _infer_workflow_hint(image_path.name)
    case_id = entry.get("case_id") or entry.get("image_case_id") or _infer_case_id(image_path.name)
    provider = entry.get("provider") or _infer_provider(image_path.name)
    match_quality = "precise_aoi" if aoi else ("workflow_hint_only" if workflow_hint else "unknown_aoi")
    confidence = 0.95 if aoi else (0.6 if workflow_hint else 0.2)
    if entry.get("inferred") and aoi:
        match_quality = "inferred_aoi"
        confidence = 0.75
    warnings = list(entry.get("warnings") or [])
    if entry.get("inferred") and aoi:
        warnings.append("AOI inferred from cached GEE request metadata; verify before relying on precise spatial matching.")
    return _build_sidecar(
        image_path,
        aoi=aoi,
        workflow_hint=str(workflow_hint) if workflow_hint else None,
        case_id=str(case_id) if case_id else None,
        provider=str(provider) if provider else None,
        confidence=confidence,
        match_quality=match_quality,
        extra_warnings=warnings,
    )


def backfill_sidecars(
    *,
    cache_dir: Path,
    overwrite: bool = False,
    dry_run: bool = False,
    pattern: str = "*",
    aoi: dict[str, float] | None = None,
    workflow_hint: str | None = None,
    case_id: str | None = None,
    gee_log_entries: dict[str, dict[str, Any]] | None = None,
    index_entries: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    scanned = 0
    sidecars_existing = 0
    sidecars_created = 0
    sidecars_updated = 0
    with_aoi = 0
    without_aoi = 0
    warnings: list[str] = []

    for image_path in sorted(cache_dir.rglob("*")):
        if not image_path.is_file() or image_path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if not fnmatch.fnmatch(image_path.name, pattern):
            continue
        scanned += 1
        sidecar_path = image_path.with_suffix(".json")
        if sidecar_path.exists() and not overwrite:
            sidecars_existing += 1
            payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
            valid, sidecar_warnings = _validate_sidecar(payload)
            if not valid:
                warnings.append(f"{sidecar_path.name}: {', '.join(sidecar_warnings)}")
            if payload.get("aoi"):
                with_aoi += 1
            else:
                without_aoi += 1
            continue

        inferred_workflow = workflow_hint or _infer_workflow_hint(image_path.name)
        inferred_case = case_id or _infer_case_id(image_path.name)
        reference_payload = None
        for key in _candidate_keys(image_path):
            if index_entries and key in index_entries:
                reference_payload = _sidecar_from_reference(image_path, dict(index_entries[key]))
                break
            if gee_log_entries and key in gee_log_entries:
                source_item = dict(gee_log_entries[key])
                source_item.setdefault("inferred", True)
                reference_payload = _sidecar_from_reference(image_path, source_item)
                break
        payload = reference_payload or _build_sidecar(
            image_path,
            aoi=aoi,
            workflow_hint=inferred_workflow,
            case_id=inferred_case,
        )
        if payload.get("aoi"):
            with_aoi += 1
        else:
            without_aoi += 1
        if dry_run:
            if sidecar_path.exists():
                sidecars_updated += 1
            else:
                sidecars_created += 1
            continue
        existed_before = sidecar_path.exists()
        sidecar_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if existed_before:
            sidecars_updated += 1
        else:
            sidecars_created += 1

    return {
        "success": True,
        "scanned": scanned,
        "sidecars_existing": sidecars_existing,
        "sidecars_created": sidecars_created,
        "sidecars_updated": sidecars_updated,
        "with_aoi": with_aoi,
        "without_aoi": without_aoi,
        "warnings": warnings,
        "dry_run": dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill EO cache sidecar metadata for Geo Expert.")
    parser.add_argument("--cache-dir", default=os.getenv("GEO_EXPERT_EO_CACHE_DIR", ""))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--aoi", default=None)
    parser.add_argument("--workflow-hint", default=None)
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--pattern", default="*")
    parser.add_argument("--from-gee-log", default=None)
    parser.add_argument("--from-index", default=None)
    parser.add_argument("--interactive-map-file", default=None)
    parser.add_argument("--output-index", default=os.getenv("GEO_EXPERT_EO_CACHE_INDEX", str(Path("outputs") / "geo_expert" / "eo_cache_index.json")))
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir).expanduser()
    if not args.cache_dir or not cache_dir.exists():
        print(json.dumps({"success": False, "error": "eo_cache_missing", "cache_dir": str(cache_dir)}, ensure_ascii=False, indent=2))
        return 0

    effective_dry_run = True
    if args.write:
        effective_dry_run = False
    elif args.dry_run:
        effective_dry_run = True

    gee_log_entries = _normalize_gee_log_entries(_load_jsonish(Path(args.from_gee_log))) if args.from_gee_log else None
    index_entries = _normalize_reference_entries(_load_jsonish(Path(args.from_index))) if args.from_index else None
    interactive_entries = _normalize_reference_entries(_load_jsonish(Path(args.interactive_map_file))) if args.interactive_map_file else None
    if interactive_entries:
        index_entries = {**(index_entries or {}), **interactive_entries}

    payload = backfill_sidecars(
        cache_dir=cache_dir,
        overwrite=args.overwrite,
        dry_run=effective_dry_run,
        pattern=args.pattern,
        aoi=_normalize_aoi(args.aoi),
        workflow_hint=args.workflow_hint,
        case_id=args.case_id,
        gee_log_entries=gee_log_entries,
        index_entries=index_entries,
    )
    payload["reference_sources"] = {
        "from_gee_log": args.from_gee_log,
        "from_index": args.from_index,
        "interactive_map_file": args.interactive_map_file,
    }
    if not effective_dry_run:
        from scripts.index_geo_expert_eo_cache import build_eo_cache_index

        index_payload = build_eo_cache_index(cache_dir=str(cache_dir), output_path=args.output_index, write_output=True)
        payload["index"] = {
            "image_count": index_payload.get("image_count"),
            "index_path": index_payload.get("index_path"),
        }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
