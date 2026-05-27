from __future__ import annotations

from plugins.geo_expert.adapters.spatial_tools import spatial_capability_profile


def test_spatial_capability_cadastral_available() -> None:
    payload = spatial_capability_profile()
    assert payload["success"] is True
    assert payload["capability_profile"]["cadastral"] == "available"


def test_missing_layers_not_marked_resolved() -> None:
    payload = spatial_capability_profile()
    assert payload["capability_profile"]["building"] == "missing_data_required"
    assert payload["capability_profile"]["river"] == "missing_data_required"
    assert payload["workflow_layer_requirements"]["WF-004"] == ["river_zone"]
