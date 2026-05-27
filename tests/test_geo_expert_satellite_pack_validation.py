from __future__ import annotations

from scripts.validate_geo_expert_satellite_packs import validate_packs


def test_satellite_pack_validation_success() -> None:
    payload = validate_packs()
    assert payload["success"] is True
    assert payload["pack_count"] == 10
    assert not payload["errors"]
