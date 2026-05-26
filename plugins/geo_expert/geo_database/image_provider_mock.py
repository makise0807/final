"""Offline mock image provider."""

from __future__ import annotations

from .image_provider_contracts import ImageProviderRequest, ImageProviderResponse


def mock_fetch(request: ImageProviderRequest) -> dict:
    response = ImageProviderResponse(
        success=True,
        provider="mock",
        mode="mock",
        source="mock",
        data={
            "task": request.task,
            "collection_hint": request.collection_hint,
            "aoi": request.aoi,
            "time_range": request.time_range,
            "bands": request.bands,
            "indices": request.indices,
            "preview_note": "Mock imagery provider response only. No real fetch was performed.",
        },
        warnings=["mock provider only; no network call was made"],
        limitations=[
            "temporary imagery provider response only",
            "does not replace OpenEO workflow planning or validation",
        ],
    )
    return response.to_dict()
