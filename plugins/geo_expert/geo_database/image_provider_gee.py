"""Temporary Google Earth Engine small-AOI thumbnail adapter."""

from __future__ import annotations

import os
import importlib
from math import cos, pi
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .image_provider_contracts import ImageProviderRequest, ImageProviderResponse


GEE_COLLECTION_CATALOG = {
    "Sentinel-2": {
        "collection_id": "COPERNICUS/S2_SR_HARMONIZED",
        "bands": ["B2", "B3", "B4", "B8", "B11", "SCL"],
    },
    "Landsat-8": {
        "collection_id": "LANDSAT/LC08/C02/T1_L2",
        "bands": ["SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6"],
    },
}

DEFAULT_GEE_MAX_AOI_KM2 = 25.0
THUMBNAIL_OUTPUT_MODES = {"thumbnail", "metadata"}
EXPORT_OUTPUT_MODES = {"export", "geotiff", "drive_export", "cloud_storage_export", "export_preview"}


def _truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class GEECredentials:
    project: str | None = None
    auth_mode: str = "oauth"
    service_account: str | None = None
    service_account_key_path: str | None = None
    allow_real_network: bool = False
    enable_export: bool = False
    enable_thumbnail: bool = True
    allow_thumbnail_download: bool = True
    thumbnail_max_bytes: int = 2000000
    max_aoi_km2: float = DEFAULT_GEE_MAX_AOI_KM2
    warnings: list[str] = field(default_factory=list)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.auth_mode == "service_account":
            if not self.service_account:
                errors.append("gee_service_account_required")
            if not self.service_account_key_path:
                errors.append("gee_service_account_key_path_required")
        elif self.auth_mode == "oauth":
            if not self.project:
                errors.append("gee_project_required_for_oauth")
        return errors

    def masked_summary(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "auth_mode": self.auth_mode,
            "service_account": self.service_account,
            "service_account_key_path": self.service_account_key_path,
            "allow_real_network": self.allow_real_network,
            "enable_export": self.enable_export,
            "enable_thumbnail": self.enable_thumbnail,
            "allow_thumbnail_download": self.allow_thumbnail_download,
            "thumbnail_max_bytes": self.thumbnail_max_bytes,
            "max_aoi_km2": self.max_aoi_km2,
            "warnings": list(self.warnings),
            "validation_errors": self.validate(),
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_gee_credentials_from_env(env: dict[str, str] | None = None) -> GEECredentials:
    env_map = env if env is not None else os.environ
    return GEECredentials(
        project=env_map.get("GEE_PROJECT"),
        auth_mode=env_map.get("GEE_AUTH_MODE", "oauth"),
        service_account=env_map.get("GEE_SERVICE_ACCOUNT"),
        service_account_key_path=env_map.get("GEE_SERVICE_ACCOUNT_KEY_PATH"),
        allow_real_network=_truthy(env_map.get("GEE_ALLOW_REAL_NETWORK"), False),
        enable_export=_truthy(env_map.get("GEE_ENABLE_EXPORT"), False),
        enable_thumbnail=_truthy(env_map.get("GEE_ENABLE_THUMBNAIL"), True),
        allow_thumbnail_download=_truthy(env_map.get("GEE_ALLOW_THUMBNAIL_DOWNLOAD"), True),
        thumbnail_max_bytes=_read_thumbnail_max_bytes(env_map.get("GEE_THUMBNAIL_MAX_BYTES")),
        max_aoi_km2=_read_max_aoi_km2(env_map.get("GEE_MAX_AOI_KM2")),
    )


def _read_thumbnail_max_bytes(value: str | None) -> int:
    try:
        parsed = int(value) if value is not None else 2000000
    except (TypeError, ValueError):
        return 2000000
    if parsed <= 0:
        return 2000000
    return parsed


def _read_max_aoi_km2(value: str | None) -> float:
    try:
        parsed = float(value) if value is not None else DEFAULT_GEE_MAX_AOI_KM2
    except (TypeError, ValueError):
        return DEFAULT_GEE_MAX_AOI_KM2
    if parsed <= 0:
        return DEFAULT_GEE_MAX_AOI_KM2
    return parsed


def _resolve_collection(request: ImageProviderRequest) -> dict[str, Any]:
    if request.collection:
        for item in GEE_COLLECTION_CATALOG.values():
            if item["collection_id"] == request.collection:
                return item
        return {"collection_id": request.collection, "bands": request.bands or []}
    return GEE_COLLECTION_CATALOG.get(
        request.collection_hint or "Sentinel-2",
        GEE_COLLECTION_CATALOG["Sentinel-2"],
    )


def validate_aoi(aoi: dict[str, Any]) -> dict[str, float]:
    if not isinstance(aoi, dict):
        raise ValueError("gee_invalid_aoi")
    try:
        west = float(aoi["west"])
        south = float(aoi["south"])
        east = float(aoi["east"])
        north = float(aoi["north"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("gee_invalid_aoi") from None
    crs = str(aoi.get("crs", "EPSG:4326")).upper()
    if crs != "EPSG:4326":
        raise ValueError("gee_invalid_aoi_crs")
    if west >= east or south >= north:
        raise ValueError("gee_invalid_aoi")
    if west < -180 or east > 180 or south < -90 or north > 90:
        raise ValueError("gee_invalid_aoi")
    return {"west": west, "south": south, "east": east, "north": north}


def estimate_aoi_area_km2(aoi: dict[str, Any]) -> float:
    bbox = validate_aoi(aoi)
    mean_lat = (bbox["south"] + bbox["north"]) / 2.0
    lat_km = 111.32 * (bbox["north"] - bbox["south"])
    lon_km = 111.32 * cos(mean_lat * pi / 180.0) * (bbox["east"] - bbox["west"])
    area = abs(lat_km * lon_km)
    if area <= 0:
        raise ValueError("gee_invalid_aoi")
    return area


def _build_common_limitations() -> list[str]:
    return [
        "Temporary imagery provider only; does not replace OpenEO workflow.",
        "Thumbnail or metadata preview only; no formal analysis result is implied.",
        "No GeoTIFF export, Drive export, or Cloud Storage export in this phase.",
    ]


def _reject(error: str, *, mode: str, source: str = "mock", warnings: list[str] | None = None, limitations: list[str] | None = None) -> dict:
    return {
        "success": False,
        "provider": "gee",
        "mode": mode,
        "source": source,
        "not_replacing_workflow": True,
        "error": error,
        "warnings": warnings or [],
        "limitations": limitations or _build_common_limitations(),
    }


def _import_ee():
    try:
        return importlib.import_module("ee")
    except ImportError:
        return None


def _initialize_ee(credentials: GEECredentials):
    ee = _import_ee()
    if ee is None:
        raise RuntimeError("gee_ee_package_not_installed")
    if credentials.auth_mode not in {"oauth", "adc", "service_account"}:
        raise RuntimeError("unsupported_gee_auth_mode")
    if credentials.auth_mode == "service_account":
        if not credentials.service_account or not credentials.service_account_key_path:
            raise RuntimeError("gee_service_account_credentials_required")
        service_credentials = ee.ServiceAccountCredentials(
            credentials.service_account,
            credentials.service_account_key_path,
        )
        ee.Initialize(service_credentials, project=credentials.project)
    else:
        ee.Initialize(project=credentials.project)
    return ee


def _check_thumbnail_request(request: ImageProviderRequest, credentials: GEECredentials) -> tuple[dict[str, float], float] | dict:
    if request.output_mode in EXPORT_OUTPUT_MODES or "export" in (request.output_mode or "").lower():
        return _reject(
            "gee_export_not_allowed",
            mode=request.output_mode,
            warnings=["Export is disabled in this phase even if GEE credentials are present."],
        )
    if request.output_mode not in THUMBNAIL_OUTPUT_MODES:
        return _reject(
            "gee_thumbnail_mode_required",
            mode=request.output_mode or "metadata",
            warnings=["Only metadata and thumbnail preview modes are supported."],
        )
    if not credentials.enable_thumbnail:
        return _reject(
            "gee_thumbnail_disabled",
            mode=request.output_mode,
            warnings=["Set GEE_ENABLE_THUMBNAIL=true to allow small-AOI thumbnail preview."],
        )
    try:
        bbox = validate_aoi(request.aoi)
        area_km2 = estimate_aoi_area_km2(request.aoi)
    except ValueError as exc:
        return _reject(str(exc), mode=request.output_mode, warnings=["AOI must be a valid EPSG:4326 bounding box."])
    if area_km2 > credentials.max_aoi_km2:
        return _reject(
            "gee_preview_large_aoi_rejected",
            mode=request.output_mode,
            warnings=[f"AOI area {area_km2:.3f} km2 exceeds GEE_MAX_AOI_KM2={credentials.max_aoi_km2:g}."],
            limitations=_build_common_limitations() + [f"AOI must be <= {credentials.max_aoi_km2:g} km2."],
        )
    return bbox, area_km2


def gee_login_check(credentials: GEECredentials | None = None) -> dict:
    creds = credentials or load_gee_credentials_from_env()
    if not creds.allow_real_network:
        return _reject(
            "gee_real_network_disabled",
            mode="metadata",
            warnings=["GEE_ALLOW_REAL_NETWORK=true is required before any real Earth Engine call."],
        ) | {"requires_opt_in": True}
    errors = creds.validate()
    if errors:
        return _reject(errors[0], mode="metadata") | {"masked_credentials": creds.masked_summary()}
    try:
        _initialize_ee(creds)
    except RuntimeError as exc:
        return _reject(str(exc), mode="metadata") | {"masked_credentials": creds.masked_summary()}
    except Exception:
        return _reject("gee_authenticate_required", mode="metadata") | {"masked_credentials": creds.masked_summary()}
    if creds.auth_mode == "oauth":
        return {
            "success": True,
            "provider": "gee",
            "mode": "metadata",
            "source": "real",
            "not_replacing_workflow": True,
            "data": {
                "project": creds.project,
                "auth_mode": creds.auth_mode,
            },
            "warnings": ["ensure local ee.Authenticate() has been completed before live Earth Engine use"],
            "limitations": _build_common_limitations() + ["Login check is auth validation only; no export or download is performed."],
        }
    if creds.auth_mode == "service_account":
        key_path = Path(creds.service_account_key_path or "")
        if not key_path.exists():
            return _reject("gee_service_account_key_path_not_found", mode="metadata")
        return {
            "success": True,
            "provider": "gee",
            "mode": "metadata",
            "source": "real",
            "not_replacing_workflow": True,
            "data": {
                "project": creds.project,
                "auth_mode": creds.auth_mode,
                "service_account": creds.service_account,
                "service_account_key_path": str(key_path),
            },
            "warnings": [],
            "limitations": _build_common_limitations() + ["Service account key content is never read or returned by Hermes."],
        }
    return _reject("unsupported_gee_auth_mode", mode="metadata")


def gee_collection_metadata(request: ImageProviderRequest, credentials: GEECredentials | None = None) -> dict:
    creds = credentials or load_gee_credentials_from_env()
    if not creds.allow_real_network:
        return _reject("gee_real_network_disabled", mode="metadata") | {"requires_opt_in": True}
    if not creds.project and creds.auth_mode == "oauth":
        return _reject("gee_project_required_for_oauth", mode="metadata")
    try:
        _initialize_ee(creds)
    except RuntimeError as exc:
        return _reject(str(exc), mode="metadata")
    except Exception:
        return _reject("gee_authenticate_required", mode="metadata")
    catalog = _resolve_collection(request)
    response = ImageProviderResponse(
        success=True,
        provider="gee",
        mode="metadata",
        source="real",
        data={
            "project": creds.project,
            "auth_mode": creds.auth_mode,
            "collection": catalog,
            "requested_bands": request.bands,
            "requested_indices": request.indices,
        },
        warnings=["temporary imagery provider only; this does not replace OpenEO workflow execution"],
        limitations=_build_common_limitations() + ["Metadata response only; no large imagery transfer."],
    )
    return response.to_dict()


def gee_build_fetch_plan(request: ImageProviderRequest) -> dict:
    creds = load_gee_credentials_from_env()
    checked = _check_thumbnail_request(request, creds)
    if isinstance(checked, dict):
        return checked
    _, area_km2 = checked
    catalog = _resolve_collection(request)
    response = ImageProviderResponse(
        success=True,
        provider="gee",
        mode=request.output_mode,
        source="mock",
        data={
            "collection": catalog["collection_id"],
            "aoi_area_km2": area_km2,
            "time_range": request.time_range,
            "bands": request.bands or catalog["bands"][:3],
            "vis_params": request.vis_params,
            "output_mode": request.output_mode,
        },
        warnings=["Preview planning only. Real calls still require GEE_ALLOW_REAL_NETWORK=true."],
        limitations=_build_common_limitations(),
    )
    return response.to_dict()


def gee_fetch_thumbnail_preview_with_fallback(
    request: ImageProviderRequest,
    credentials: GEECredentials | None = None,
) -> dict[str, Any]:
    """
    Fetch GEE thumbnail with multi-dataset and date range fallback.
    
    Tries multiple Earth Engine datasets and date ranges to find imagery.
    
    Returns:
        dict with success, thumbnail_url, selected dataset info, and attempts log
    """
    creds = credentials or load_gee_credentials_from_env()
    checked = _check_thumbnail_request(request, creds)
    if isinstance(checked, dict):
        return checked
    _, area_km2 = checked
    
    if not creds.allow_real_network:
        return _reject(
            "gee_real_network_disabled",
            mode=request.output_mode,
            warnings=["set GEE_ALLOW_REAL_NETWORK=true for opt-in live preview requests"],
        )
    
    try:
        ee = _initialize_ee(creds)
    except Exception as exc:
        return _reject(f"gee_initialize_failed: {exc}", mode="thumbnail", source="real")
    
    # Dataset candidates with fallback order
    dataset_candidates = [
        {
            "name": "Sentinel-2 SR Harmonized",
            "collection_id": "COPERNICUS/S2_SR_HARMONIZED",
            "bands": ["B4", "B3", "B2"],
            "rgb_bands": ["B4", "B3", "B2"],
            "vis": {"min": 0, "max": 3000, "gamma": 1.2},
            "cloud_field": "CLOUDY_PIXEL_PERCENTAGE",
        },
        {
            "name": "Sentinel-2 TOA Harmonized",
            "collection_id": "COPERNICUS/S2_HARMONIZED",
            "bands": ["B4", "B3", "B2"],
            "rgb_bands": ["B4", "B3", "B2"],
            "vis": {"min": 0, "max": 3000, "gamma": 1.2},
            "cloud_field": "CLOUDY_PIXEL_PERCENTAGE",
        },
        {
            "name": "Landsat 8 Collection 2 TOA",
            "collection_id": "LANDSAT/LC08/C02/T1_TOA",
            "bands": ["B4", "B3", "B2"],
            "rgb_bands": ["B4", "B3", "B2"],
            "vis": {"min": 0.02, "max": 0.3, "gamma": 1.2},
            "cloud_field": "CLOUD_COVER",
        },
    ]
    
    # Date range candidates
    user_date_range = request.time_range if len(request.time_range) >= 2 else None
    date_range_candidates = []
    if user_date_range:
        date_range_candidates.append(user_date_range)
    date_range_candidates.extend([
        ["2025-01-01", "2025-12-31"],
        ["2024-01-01", "2024-12-31"],
        ["2023-01-01", "2023-12-31"],
        ["2022-01-01", "2022-12-31"],
    ])
    
    bbox = validate_aoi(request.aoi)
    geometry = ee.Geometry.Rectangle(
        [bbox["west"], bbox["south"], bbox["east"], bbox["north"]],
        proj="EPSG:4326",
        geodesic=False,
    )
    
    attempts = []
    
    # Try each dataset
    for dataset in dataset_candidates:
        for date_range in date_range_candidates:
            for cloud_filter in [True, False]:
                attempt: dict[str, Any] = {
                    "dataset": dataset["name"],
                    "collection_id": dataset["collection_id"],
                    "date_range": date_range,
                    "cloud_filter": cloud_filter,
                    "collection_size": 0,
                    "thumb_url_created": False,
                    "error": None,
                }
                
                try:
                    collection = ee.ImageCollection(dataset["collection_id"]).filterBounds(geometry)
                    collection = collection.filterDate(date_range[0], date_range[1])
                    
                    # Apply cloud filter if enabled
                    if cloud_filter and dataset.get("cloud_field"):
                        collection = collection.filter(
                            ee.Filter.lt(dataset["cloud_field"], 80)
                        )
                    
                    collection_size = int(collection.size().getInfo())
                    attempt["collection_size"] = collection_size
                    
                    if collection_size <= 0:
                        attempt["error"] = "no_images"
                        attempts.append(attempt)
                        continue
                    
                    # Select image: prefer median, or first by cloud cover
                    if cloud_filter and dataset.get("cloud_field"):
                        image = collection.sort(dataset["cloud_field"]).first()
                    else:
                        image = collection.median()
                    
                    # Select bands and visualize
                    selected_bands = request.bands or dataset["rgb_bands"]
                    image_viz = image.select(selected_bands).visualize(**dataset["vis"])
                    
                    # Get thumbnail URL
                    thumbnail_url = image_viz.getThumbURL({
                        "region": request.aoi,
                        "dimensions": 768,
                        "format": "png",
                    })
                    
                    if not thumbnail_url:
                        attempt["error"] = "no_url"
                        attempts.append(attempt)
                        continue
                    
                    attempt["thumb_url_created"] = True
                    attempts.append(attempt)
                    
                    # Success! Return with full attempts log
                    return {
                        "success": True,
                        "provider": "gee",
                        "mode": "thumbnail",
                        "source": "real",
                        "not_replacing_workflow": True,
                        "thumbnail_url": thumbnail_url,
                        "metadata": {
                            "collection": dataset["collection_id"],
                            "collection_name": dataset["name"],
                            "time_range": date_range,
                            "aoi_area_km2": round(area_km2, 6),
                            "selected_image_count": collection_size,
                            "bands": selected_bands,
                            "vis_params": dataset["vis"],
                            "cloud_filter_applied": cloud_filter,
                        },
                        "attempts": attempts,
                        "warnings": [
                            "Temporary imagery provider only; no formal analysis result is implied.",
                            "Thumbnail preview only; no download, GeoTIFF export, Drive export, or Cloud Storage export was performed.",
                        ],
                        "limitations": _build_common_limitations(),
                    }
                
                except Exception as exc:
                    attempt["error"] = str(exc)
                    attempts.append(attempt)
                    continue
    
    # All attempts failed
    return {
        "success": False,
        "provider": "gee",
        "mode": "thumbnail",
        "source": "real",
        "error": "no_dataset_produced_thumbnail",
        "attempts": attempts,
        "warnings": [
            f"Could not retrieve thumbnail from any dataset after {len(attempts)} attempts.",
            "Please check GEE project access and AOI coverage.",
        ],
        "limitations": _build_common_limitations(),
    }


# Backward compatibility wrapper
def gee_fetch_thumbnail_preview(request: ImageProviderRequest, credentials: GEECredentials | None = None) -> dict:
    """Backward compatibility wrapper; use gee_fetch_thumbnail_preview_with_fallback instead."""
    return gee_fetch_thumbnail_preview_with_fallback(request, credentials)
