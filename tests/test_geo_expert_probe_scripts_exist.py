from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_geo_expert_probe_scripts_exist() -> None:
    root = Path("C:/Users/34620/OneDrive/Desktop/final/scripts")
    postgis = root / "probe_geo_expert_postgis.py"
    chromadb = root / "probe_geo_expert_chromadb.py"
    eo_cache = root / "probe_geo_expert_eo_cache.py"
    detector = root / "probe_geo_expert_detector.py"
    assert postgis.exists()
    assert chromadb.exists()
    assert eo_cache.exists()
    assert detector.exists()
    assert hasattr(_load_module(postgis), "main")
    assert hasattr(_load_module(chromadb), "main")
    assert hasattr(_load_module(eo_cache), "main")
    assert hasattr(_load_module(detector), "main")
