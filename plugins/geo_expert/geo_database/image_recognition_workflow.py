"""SOP-to-image-recognition planning helpers."""

from __future__ import annotations

from typing import Any

_SUPPORTED_WORKFLOWS = {"WF-001", "WF-004", "WF-005", "WF-009", "WF-010"}


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def supports_image_recognition(workflow_id: str) -> bool:
    return str(workflow_id or "").strip() in _SUPPORTED_WORKFLOWS


def build_image_recognition_plan_from_sop(
    selected_sop: dict[str, Any],
    compiled_plan: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sop = _as_dict(selected_sop)
    plan = _as_dict(compiled_plan)
    ctx = _as_dict(context)
    workflow_id = str(sop.get("workflow_id") or plan.get("workflow_id") or "").strip()
    if not workflow_id:
        return {"success": False, "error": "image_recognition_missing_workflow_id"}

    legal_building_available = bool(
        ctx.get("legal_building_layer_available")
        or _as_dict(ctx.get("landuse_context")).get("legal_building_layer_available")
    )

    target_classes_by_workflow = {
        "WF-001": ["building", "concrete_surface", "non_vegetation_surface"],
        "WF-004": ["waste_pile", "disturbed_surface", "bare_soil"],
        "WF-005": ["solar_panel", "building", "non_vegetation_surface"],
        "WF-009": ["landslide_scars", "bare_soil", "debris"],
        "WF-010": ["forest_edge_change", "clearing", "disturbed_surface"],
    }
    required_layers_by_workflow = {
        "WF-001": ["agricultural_zone", "legal_building_layer", "cadastral_layer"],
        "WF-004": ["river_zone", "waste_site_reference", "cadastral_layer"],
        "WF-005": ["agricultural_zone", "solar_permit_layer", "cadastral_layer"],
        "WF-009": ["hazard_zone", "slope_layer", "rainfall_context"],
        "WF-010": ["ecological_network_layer", "sensitive_habitat_layer", "cadastral_layer"],
    }
    legal_keywords_by_workflow = {
        "WF-001": [
            "農業發展條例 違法使用 裁罰",
            "區域計畫法 國土計畫法 違規使用 罰鍰",
            "非都市土地使用管制",
        ],
        "WF-004": ["河川管理 水利法 廢棄物清理法", "行水區 違法傾倒 裁罰"],
        "WF-005": ["農地種電 光電合法性 農業發展條例", "農地光電 合法性 稽查"],
        "WF-009": ["水土保持法 崩塌地 防災潛勢", "豪雨 災害敏感區 管理"],
        "WF-010": ["國土綠網 生態敏感區 開發干擾", "保育廊道 棲地干擾"],
    }

    detection_logic = [
        "identify target polygons from preview imagery using a preliminary detector",
        "intersect detections with the workflow target zone",
    ]
    if workflow_id == "WF-001":
        detection_logic = [
            "identify building/concrete polygons",
            "intersect with agricultural zone",
            "subtract legal building layer if available",
            "mark remaining polygons as preliminary suspected areas",
        ]

    limitations = [
        "Preliminary detection only.",
        "Needs verification.",
        "Not a formal legal conclusion.",
        "No GeoTIFF/export/download performed.",
    ]
    warnings: list[str] = []
    if workflow_id == "WF-001" and not legal_building_available:
        warnings.append("Legal building layer is missing; suspected areas cannot be treated as legal conclusions.")
        limitations.append("尚未扣除合法建地或建照資料，因此僅能標記為疑似區塊。")

    recognition_plan = {
        "workflow_id": workflow_id,
        "title": str(sop.get("title") or workflow_id),
        "task": "illegal_factory_check" if workflow_id == "WF-001" else "preliminary_image_recognition",
        "target_classes": target_classes_by_workflow.get(workflow_id, ["building"]),
        "required_layers": required_layers_by_workflow.get(workflow_id, ["cadastral_layer"]),
        "detection_logic": detection_logic,
        "legal_rag_keywords": legal_keywords_by_workflow.get(workflow_id, ["preliminary legal review"]),
        "output": ["GeoJSON overlay", "preliminary case report", "missing data list"],
        "landuse_context": {
            "zone_type": "agricultural" if workflow_id in {"WF-001", "WF-005"} else "workflow_target_zone",
            "legal_building_layer_available": legal_building_available,
        },
        "warnings": warnings,
        "limitations": limitations,
        "not_formal_analysis": True,
        "requires_verification": True,
    }
    return {"success": True, "recognition_plan": recognition_plan}


__all__ = ["build_image_recognition_plan_from_sop", "supports_image_recognition"]
