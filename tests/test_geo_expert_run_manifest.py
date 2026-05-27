from __future__ import annotations

from plugins.geo_expert.production import create_run_manifest


def test_run_manifest_contains_required_fields() -> None:
    manifest = create_run_manifest(
        {
            "workflow_id": "WF-001",
            "mode": "safe_run",
            "inputs": {"aoi": {"west": 1, "south": 2, "east": 3, "north": 4}},
            "warnings": ["sample_warning"],
            "limitations": ["sample_limit"],
            "steps": [{"adapter": "rag", "used_real_service": True, "evidence": {"selected_collection": "urban_regulations"}}],
            "satellite_evidence": {},
        }
    )
    assert manifest["run_id"]
    assert manifest["services_used"]["chromadb"] is True
    assert "warnings" in manifest
    assert "artifacts" in manifest
