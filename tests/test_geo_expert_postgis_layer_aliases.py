from __future__ import annotations

import json
from pathlib import Path

from plugins.geo_expert.adapters.spatial_tools import _resolve_layer_name


def test_geo_expert_postgis_layer_aliases() -> None:
    path = Path("C:/Users/34620/OneDrive/Desktop/final/plugins/geo_expert/data/spatial/layer_aliases.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload["cadastral_layer"], dict)
    assert payload["cadastral_layer"]["table"] == "public.cadastral_parcels"
    assert payload["cadastral_layer"]["status"] == "resolved"
    assert payload["river_zone"]["status"] == "missing_data_required"


def test_object_alias_is_backward_compatible() -> None:
    resolved = _resolve_layer_name("cadastral_layer")
    assert resolved["table"] == "public.cadastral_parcels"
    assert resolved["status"] == "resolved"


def test_missing_data_required_is_not_resolved() -> None:
    resolved = _resolve_layer_name("river_zone")
    assert resolved["status"] == "missing_data_required"
