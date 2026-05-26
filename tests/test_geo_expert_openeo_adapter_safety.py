from __future__ import annotations

import json

from plugins.geo_expert.tools import eo_openeo_prepare_handler, eo_openeo_status_handler


def test_geo_expert_openeo_adapter_safety(monkeypatch) -> None:
    for key in ("OPENEO_URL", "OPENEO_USER", "OPENEO_PASSWORD"):
        monkeypatch.delenv(key, raising=False)

    raw_status = eo_openeo_status_handler({})
    status_payload = json.loads(raw_status)
    assert status_payload["success"] is False
    assert status_payload["dependency"] == "openeo"

    raw_prepare = eo_openeo_prepare_handler({"operation": "ndvi", "parameters": {"date": "2026-05-01"}})
    prepare_payload = json.loads(raw_prepare)
    assert prepare_payload["success"] is False or prepare_payload.get("approval_required") is True
    assert "download_performed" not in prepare_payload or prepare_payload["download_performed"] is False
    assert "submit_performed" not in prepare_payload or prepare_payload["submit_performed"] is False

