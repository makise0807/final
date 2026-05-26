"""Routing layer for temporary imagery providers."""

from __future__ import annotations

from .image_provider_contracts import ImageProviderRequest, ImageProviderResponse


def route_image_provider_request(request: ImageProviderRequest, *, openeo_available: bool = True) -> dict:
    task_lower = (request.task or "").lower()
    provider = request.provider.lower()

    if provider == "mock":
        chosen = "mock"
    elif any(token in task_lower for token in ("earth engine", "gee", "temporary image", "fallback")):
        chosen = "gee"
    elif not openeo_available:
        chosen = "gee"
    elif provider == "gee":
        chosen = "gee"
    elif provider == "openeo":
        chosen = "openeo"
    else:
        chosen = "openeo"

    warnings: list[str] = []
    limitations: list[str] = []
    if chosen == "gee":
        warnings.append("GEE is being used only as a temporary imagery provider or fallback.")
        limitations.append("does not replace OpenEO workflow contracts, preview, validation, or planner logic")
        limitations.append("GEE path is limited to small AOI thumbnail or metadata preview only.")
    if chosen == "openeo":
        limitations.append("OpenEO remains the primary workflow provider for formal EO workflow execution.")

    response = ImageProviderResponse(
        success=True,
        provider=chosen,
        mode="metadata",
        source="mock",
        data={
            "requested_provider": provider,
            "selected_provider": chosen,
            "collection_hint": request.collection_hint,
            "output_mode": request.output_mode,
            "openeo_available": openeo_available,
        },
        warnings=warnings,
        limitations=limitations,
    )
    return response.to_dict()
