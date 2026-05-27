from __future__ import annotations

from plugins.geo_expert.production import approval_gate_for_action


def test_approval_gate_requires_confirmation_for_openeo() -> None:
    gate = approval_gate_for_action("openeo_submit", estimated_outputs=["GeoTIFF"])
    assert gate["approval_required"] is True
    assert gate["requires_user_confirmation"] is True
    assert gate["risk"] == "external_job_and_large_download"
