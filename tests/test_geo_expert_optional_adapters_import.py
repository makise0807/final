from __future__ import annotations

import importlib


def test_geo_expert_optional_adapters_import() -> None:
    for module_name in (
        "plugins.geo_expert.adapters.eo_tools",
        "plugins.geo_expert.adapters.spatial_tools",
        "plugins.geo_expert.adapters.rag_tools",
    ):
        module = importlib.import_module(module_name)
        assert module is not None

