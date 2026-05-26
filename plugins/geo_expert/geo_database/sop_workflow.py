"""SOP-driven workflow composer for geo/legal expert cases."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    from agent.local_llm_client import chat_json
except ModuleNotFoundError:
    def chat_json(*_args, **_kwargs):
        return {
            "success": True,
            "data": {
                "selected_sop": "WF-001",
                "reason": "Standalone fallback SOP match.",
                "confidence": 0.5,
            },
            "error": None,
        }
from .case_report import build_case_report, case_report_llm_draft_report
from .image_recognition_workflow import build_image_recognition_plan_from_sop, supports_image_recognition
from .legal_database import search_legal_database

_REPO_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOW_DB_PATH = _REPO_ROOT / "data" / "workflow_db" / "expert_workflows.json"
_WORKFLOW_SOURCE_PATH = str(_WORKFLOW_DB_PATH)

_DEFAULT_DOMAINS = ["geo", "legal", "land_management", "urban_planning"]
_WORKFLOW_CASE_CACHE: list[dict[str, Any]] | None = None
_DETERMINISTIC_WORKFLOW_KEYWORDS: dict[str, tuple[str, ...]] = {
    "WF-001": ("農地", "農業區", "違章", "違建", "工廠", "建築", "鐵皮", "水泥", "farmland", "factory", "illegal factory"),
    "WF-002": ("山坡地", "濫墾", "植被", "ndvi", "水土保持", "hillside"),
    "WF-004": ("河川", "行水區", "廢棄物", "傾倒", "river", "dumping"),
    "WF-005": ("種電", "光電", "太陽能", "solar", "photovoltaic"),
    "WF-006": ("新訂都市計畫", "區位適宜", "site suitability"),
    "WF-008": ("tod", "捷運", "場站", "容積獎勵"),
    "WF-009": ("崩塌", "淹塞湖", "豪雨", "landslide"),
    "WF-010": ("國土綠網", "生態", "棲地", "綠網", "habitat"),
}

_WORKFLOW_RULES: list[dict[str, Any]] = [
    {
        "workflow_id": "WF-001",
        "match_terms": ("farmland", "illegal factory", "factory", "農地", "違章工廠", "農地違建", "非農業使用", "水泥鋪面"),
        "queries": [
            "農業區 違章工廠 農地違建 疑似建物 非農業使用",
            "農業發展條例 違法使用 裁罰 區域計畫法 國土計畫法",
        ],
        "required_inputs": ["aoi", "time_range", "parcel_id"],
        "needs_preview": True,
    },
    {
        "workflow_id": "WF-002",
        "match_terms": ("hillside", "ndvi", "overuse", "山坡地", "濫墾", "超限利用", "植被破壞", "水土保持"),
        "queries": [
            "山坡地 保育區 超限利用 濫墾 NDVI 變化",
            "水土保持法 山坡地 保育利用條例 擅自開發",
        ],
        "required_inputs": ["aoi", "time_range"],
        "needs_preview": True,
    },
    {
        "workflow_id": "WF-003",
        "match_terms": ("urban renewal", "都市更新", "都更", "危老", "屋齡", "臨路"),
        "queries": [
            "都市更新 單元 劃定 條件 屋齡 臨路",
            "都市更新條例 都更單元 劃定基準",
        ],
        "required_inputs": ["aoi", "parcel_id"],
        "needs_preview": False,
    },
    {
        "workflow_id": "WF-004",
        "match_terms": ("river", "floodway", "dumping", "河川", "行水區", "廢棄物", "傾倒", "土石"),
        "queries": [
            "河川 行水區 違法傾倒 廢棄物 土石",
            "水利法 行水區 禁止事項 廢棄物清理法",
        ],
        "required_inputs": ["aoi", "time_range"],
        "needs_preview": True,
    },
    {
        "workflow_id": "WF-005",
        "match_terms": ("solar", "solar panel", "photovoltaic", "農地種電", "光電", "太陽能板", "營農型", "遮蔽率"),
        "queries": [
            "農地種電 光電設施 合法性 稽查 遮蔽率",
            "農業用地 作農業設施 容許使用 審查辦法",
        ],
        "required_inputs": ["aoi", "time_range"],
        "needs_preview": True,
    },
    {
        "workflow_id": "WF-006",
        "match_terms": ("new urban plan", "site suitability", "新訂都市計畫", "區位適宜性", "環境敏感"),
        "queries": [
            "新訂都市計畫 區位適宜性 環境敏感 斷層 淹水潛勢",
            "都市計畫法 新訂 都市計畫 區位評估",
        ],
        "required_inputs": ["aoi", "time_range"],
        "needs_preview": True,
    },
    {
        "workflow_id": "WF-007",
        "match_terms": ("special agricultural", "general agricultural", "特定農業區", "一般農業區", "分區變更", "灌溉"),
        "queries": [
            "變更 特定農業區 為 一般農業區 檢核",
            "農業發展條例 國土計畫 分區變更",
        ],
        "required_inputs": ["aoi", "parcel_id"],
        "needs_preview": True,
    },
    {
        "workflow_id": "WF-008",
        "match_terms": ("tod", "transit oriented", "metro station", "捷運", "場站", "容積獎勵"),
        "queries": [
            "捷運 場站 周邊 TOD 容積獎勵 試算",
            "都市更新 容積獎勵 捷運 場站 周邊",
        ],
        "required_inputs": ["aoi", "parcel_id"],
        "needs_preview": False,
    },
    {
        "workflow_id": "WF-009",
        "match_terms": ("landslide", "debris flow", "flood trap", "崩塌", "淹塞湖", "豪雨", "防災"),
        "queries": [
            "崩塌地 與 淹塞湖 防災 潛勢 評估",
            "豪雨 崩塌 淹塞湖 災害 潛勢",
        ],
        "required_inputs": ["aoi", "time_range"],
        "needs_preview": True,
    },
    {
        "workflow_id": "WF-010",
        "match_terms": ("green network", "ecological", "habitat", "國土綠網", "生態", "敏感區", "保育廊道"),
        "queries": [
            "國土綠網 與 生態敏感區 開發干擾 評估",
            "保育廊道 棲地 敏感區 開發 影響",
        ],
        "required_inputs": ["aoi", "time_range"],
        "needs_preview": True,
    },
]


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _as_list(*values: Any) -> list[str]:
    merged: list[str] = []
    for value in values:
        if not value:
            continue
        if isinstance(value, (list, tuple, set)):
            items = value
        else:
            items = [value]
        for item in items:
            text = _normalize_text(item)
            if text and text not in merged:
                merged.append(text)
    return merged


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            data = value.to_dict()
            if isinstance(data, dict):
                return dict(data)
        except Exception:
            pass
    try:
        data = dict(value)
        if isinstance(data, dict):
            return dict(data)
    except Exception:
        pass
    return {}


def _tokenize(text: str) -> set[str]:
    tokens = re.split(r"[\W_]+", text.lower())
    return {token for token in tokens if token}


def _workflow_rule_for_text(text: str) -> dict[str, Any] | None:
    lowered = text.lower()
    for rule in _WORKFLOW_RULES:
        if any(term.lower() in lowered for term in rule["match_terms"]):
            return rule
    for workflow_id, keywords in _DETERMINISTIC_WORKFLOW_KEYWORDS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            for rule in _WORKFLOW_RULES:
                if rule["workflow_id"] == workflow_id:
                    return rule
    return None


def _default_workflow_cases() -> list[dict[str, Any]]:
    cases = []
    for rule in _WORKFLOW_RULES:
        cases.append(
            {
                "workflow_id": rule["workflow_id"],
                "title": rule["workflow_id"],
                "domain": list(_DEFAULT_DOMAINS),
                "keywords": list(rule["match_terms"]),
                "source_path": _WORKFLOW_SOURCE_PATH,
                "chunk_id": rule["workflow_id"],
                "snippet": "Expert SOP fallback.",
                "citation": {
                    "title": rule["workflow_id"],
                    "path": _WORKFLOW_SOURCE_PATH,
                    "chunk_id": rule["workflow_id"],
                    "source_type": "expert_workflow",
                },
                "source_record": {},
            }
        )
    return cases


def _load_workflow_cases() -> list[dict[str, Any]]:
    global _WORKFLOW_CASE_CACHE
    if _WORKFLOW_CASE_CACHE is not None:
        return deepcopy(_WORKFLOW_CASE_CACHE)

    cases: list[dict[str, Any]] = []
    if _WORKFLOW_DB_PATH.exists():
        try:
            data = json.loads(_WORKFLOW_DB_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for idx, row in enumerate(data, start=1):
                    if not isinstance(row, dict):
                        continue
                    workflow_id = _normalize_text(row.get("scenario_id")) or f"WF-{idx:03d}"
                    title = _normalize_text(row.get("scenario_name")) or workflow_id
                    keywords = [_normalize_text(item) for item in row.get("keywords") or [] if _normalize_text(item)]
                    cases.append(
                        {
                            "workflow_id": workflow_id,
                            "title": title,
                            "domain": list(_DEFAULT_DOMAINS),
                            "keywords": keywords,
                            "source_path": _WORKFLOW_SOURCE_PATH,
                            "chunk_id": workflow_id,
                            "snippet": _normalize_text(
                                row.get("rag_retrieval")
                                or row.get("expected_response")
                                or row.get("user_query")
                                or title
                            ),
                            "citation": {
                                "title": title,
                                "path": _WORKFLOW_SOURCE_PATH,
                                "chunk_id": workflow_id,
                                "source_type": "expert_workflow",
                            },
                            "source_record": row,
                        }
                    )
        except Exception:
            cases = []

    if not cases:
        cases = _default_workflow_cases()

    _WORKFLOW_CASE_CACHE = deepcopy(cases)
    return deepcopy(cases)


def _workflow_case_by_id(workflow_id: str) -> dict[str, Any] | None:
    for case in _load_workflow_cases():
        if case.get("workflow_id") == workflow_id:
            return case
    return None


def _legal_query_queries(user_request: str) -> list[str]:
    if not user_request.strip():
        return []
    rule = _workflow_rule_for_text(user_request)
    if rule:
        return list(dict.fromkeys(rule["queries"]))[:3]
    return [user_request.strip()]


def llm_rewrite_query(user_request: str) -> dict[str, Any]:
    fallback_queries = _legal_query_queries(user_request)
    if not user_request.strip():
        return {"success": True, "search_queries": fallback_queries, "fallback_used": True}

    llm_result = chat_json(
        system_prompt=(
            "Rewrite a vague Taiwanese geo/legal SOP request into 2-3 short retrieval queries. "
            "Do not make legal conclusions. Return JSON with search_queries."
        ),
        user_prompt=f"User request: {user_request}\nReturn search queries for SOP retrieval.",
        schema_hint={
            "type": "object",
            "properties": {"search_queries": {"type": "array", "items": {"type": "string"}}},
            "required": ["search_queries"],
        },
    )
    if llm_result.get("success") and isinstance(llm_result.get("data"), dict):
        queries = [_normalize_text(item) for item in llm_result["data"].get("search_queries", []) if _normalize_text(item)]
        if queries:
            return {"success": True, "search_queries": list(dict.fromkeys(queries))[:3], "fallback_used": False}

    return {"success": True, "search_queries": fallback_queries, "fallback_used": True}


def llm_classify_intent(user_request: str) -> dict[str, Any]:
    if not user_request.strip():
        return {"success": True, "intent": "unknown", "matched_keywords": [], "fallback_used": True}
    rule = _workflow_rule_for_text(user_request)
    if rule:
        case = _workflow_case_by_id(rule["workflow_id"])
        matched = [term for term in rule["match_terms"] if term.lower() in user_request.lower()]
        return {
            "success": True,
            "intent": case["title"] if case else rule["workflow_id"],
            "workflow_id": rule["workflow_id"],
            "matched_keywords": matched,
            "fallback_used": True,
        }
    return {"success": True, "intent": "unknown", "matched_keywords": [], "fallback_used": True}


def _score_workflow_case(user_request: str, queries: list[str], case: dict[str, Any]) -> tuple[float, list[str]]:
    lowered = user_request.lower()
    query_blob = " ".join(queries).lower()
    tokens = _tokenize(user_request)
    keywords = [str(item) for item in case.get("keywords", [])]

    matched = sorted({keyword for keyword in keywords if keyword and (keyword.lower() in lowered or keyword.lower() in query_blob)})
    score = float(len(matched)) * 0.35
    score += sum(min(len(keyword), 12) / 12.0 for keyword in matched)

    workflow_id = _normalize_text(case.get("workflow_id"))
    deterministic_keywords = _DETERMINISTIC_WORKFLOW_KEYWORDS.get(workflow_id, ())
    for keyword in deterministic_keywords:
        if keyword.lower() in lowered or keyword.lower() in query_blob:
            if keyword not in matched:
                matched.append(keyword)
            score += 0.45
    if workflow_id == "WF-005" and any(term in lowered for term in ("種電", "光電", "太陽能板", "photovoltaic", "solar")):
        score += 1.5
    elif workflow_id == "WF-001" and any(term in lowered for term in ("違章工廠", "工廠", "鐵皮", "非農業使用", "水泥鋪面")):
        score += 1.0

    title = _normalize_text(case.get("title"))
    if title and title.lower() in lowered:
        score += 0.8

    if workflow_id and workflow_id.lower() in lowered:
        score += 0.4

    for keyword in keywords:
        if keyword.lower() in tokens:
            score += 0.25

    return score, matched


def llm_explain_sop_match(user_request: str, selected_sop: dict[str, Any]) -> dict[str, Any]:
    title = selected_sop.get("title") or selected_sop.get("workflow_id") or "unknown"
    base = f"The request appears closest to {title}. This is a preliminary match based on keyword overlap and expert SOP alignment."
    llm_result = chat_json(
        system_prompt=(
            "Explain why a SOP candidate matches a vague geo/legal request. "
            "Do not add legal conclusions. Return JSON with reason and confidence."
        ),
        user_prompt=f"User request: {user_request}\nSelected SOP: {json.dumps(selected_sop, ensure_ascii=False)}",
        schema_hint={
            "type": "object",
            "properties": {"reason": {"type": "string"}, "confidence": {"type": "number"}},
            "required": ["reason"],
        },
    )
    if llm_result.get("success") and isinstance(llm_result.get("data"), dict):
        reason = _normalize_text(llm_result["data"].get("reason"))
        if reason:
            confidence_raw = llm_result["data"].get("confidence")
            try:
                confidence = float(confidence_raw)
            except (TypeError, ValueError):
                confidence = float(selected_sop.get("confidence") or 0.0)
            return {"success": True, "reason": reason, "confidence": confidence, "fallback_used": False}
    return {"success": True, "reason": base, "confidence": float(selected_sop.get("confidence") or 0.0), "fallback_used": True}


def retrieve_sop_candidates(
    user_request: str,
    *,
    db_path: str | None = None,
    legal_db_path: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    rewritten = llm_rewrite_query(user_request)
    queries = rewritten.get("search_queries") or [user_request]
    cases = _load_workflow_cases()

    ranked: list[tuple[float, dict[str, Any], list[str]]] = []
    for case in cases:
        score, matched = _score_workflow_case(user_request, queries, case)
        if score <= 0.0 and not matched:
            continue
        ranked.append((score, case, matched))

    if not ranked:
        fallback_rule = _workflow_rule_for_text(user_request)
        fallback_case = _workflow_case_by_id(_normalize_text((fallback_rule or {}).get("workflow_id")))
        if fallback_case:
            fallback_matched = [
                keyword
                for keyword in _DETERMINISTIC_WORKFLOW_KEYWORDS.get(fallback_case["workflow_id"], ())
                if keyword.lower() in user_request.lower()
            ]
            ranked.append((1.0, fallback_case, fallback_matched))

    ranked.sort(key=lambda item: item[0], reverse=True)
    candidates: list[dict[str, Any]] = []
    for score, case, matched in ranked[:top_k]:
        candidates.append(
            {
                "workflow_id": case["workflow_id"],
                "title": case["title"],
                "domain": case.get("domain") or list(_DEFAULT_DOMAINS),
                "matched_keywords": matched,
                "score": round(score, 3),
                "source_path": case["source_path"],
                "chunk_id": case["chunk_id"],
                "snippet": case["snippet"],
                "citation": case["citation"],
            }
        )

    legal_context: dict[str, Any] = {}
    if legal_db_path is not None and queries:
        try:
            legal_context = search_legal_database(queries[0], db_path=legal_db_path, top_k=min(top_k, 3))
        except Exception:
            legal_context = {}

    top_score = candidates[0]["score"] if candidates else 0.0
    second_score = candidates[1]["score"] if len(candidates) > 1 else 0.0
    needs_clarification = bool(candidates) and (top_score < 0.35 or (top_score - second_score) < 0.12)

    return {
        "success": True,
        "query": " | ".join(dict.fromkeys(queries)),
        "rewritten_queries": list(dict.fromkeys(queries)),
        "sop_candidates": candidates,
        "no_sop_found": not candidates,
        "needs_clarification": needs_clarification,
        "legal_context": legal_context,
    }


def llm_explain_sop_match(user_request: str, selected_sop: dict[str, Any]) -> dict[str, Any]:
    title = selected_sop.get("title") or selected_sop.get("workflow_id") or "unknown"
    base = f"The request appears closest to {title}. This is a preliminary match based on keyword overlap and expert SOP alignment."
    llm_result = chat_json(
        system_prompt=(
            "Explain why a SOP candidate matches a vague geo/legal request. "
            "Do not add legal conclusions. Return JSON with reason and confidence."
        ),
        user_prompt=f"User request: {user_request}\nSelected SOP: {json.dumps(selected_sop, ensure_ascii=False)}",
        schema_hint={
            "type": "object",
            "properties": {"reason": {"type": "string"}, "confidence": {"type": "number"}},
            "required": ["reason"],
        },
    )
    if llm_result.get("success") and isinstance(llm_result.get("data"), dict):
        reason = _normalize_text(llm_result["data"].get("reason"))
        if reason:
            confidence_raw = llm_result["data"].get("confidence")
            try:
                confidence = float(confidence_raw)
            except (TypeError, ValueError):
                confidence = float(selected_sop.get("confidence") or 0.0)
            return {"success": True, "reason": reason, "confidence": confidence, "fallback_used": False}
    return {"success": True, "reason": base, "confidence": float(selected_sop.get("confidence") or 0.0), "fallback_used": True}


def match_sop_candidates(user_request: str, sop_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not sop_candidates:
        return {
            "success": True,
            "selected_sop": None,
            "alternatives": [],
            "needs_clarification": True,
            "clarification_question": "Please provide more details such as the parcel, area, or time range.",
        }

    ranked = sorted(sop_candidates, key=lambda item: float(item.get("score") or 0.0), reverse=True)
    lowered = user_request.lower()

    preferred_workflow_id = None
    preference_rules = [
        ("WF-005", ("solar", "solar panel", "photovoltaic", "農地種電", "光電", "太陽能板", "營農型", "遮蔽率", "種電")),
        ("WF-001", ("illegal factory", "違章工廠", "工廠", "鐵皮", "非農業使用", "水泥鋪面")),
        ("WF-002", ("hillside", "ndvi", "overuse", "山坡地", "濫墾", "植被破壞", "水土保持")),
        ("WF-004", ("river", "floodway", "dumping", "河川", "行水區", "廢棄物", "土石")),
        ("WF-008", ("tod", "transit oriented", "metro station", "捷運", "場站", "容積獎勵")),
        ("WF-009", ("landslide", "debris flow", "flood trap", "崩塌", "淹塞湖", "豪雨", "災害")),
        ("WF-010", ("green network", "ecological", "habitat", "國土綠網", "生態", "棲地", "保育廊道")),
    ]
    candidate_ids = {str(item.get("workflow_id") or ""): dict(item) for item in ranked}
    for workflow_id, terms in preference_rules:
        if any(term.lower() in lowered for term in terms) and workflow_id in candidate_ids:
            preferred_workflow_id = workflow_id
            break

    if preferred_workflow_id:
        selected = dict(candidate_ids[preferred_workflow_id])
    else:
        selected = dict(ranked[0])

    selected_id = str(selected.get("workflow_id") or ranked[0].get("workflow_id") or "")
    top_score = float(selected.get("score") or 0.0)
    second_score = float(ranked[1].get("score") or 0.0) if len(ranked) > 1 else 0.0
    needs_clarification = top_score < 0.35 or (top_score - second_score) < 0.12
    clarification_question = None
    if needs_clarification:
        clarification_question = (
            "Multiple expert SOPs look plausible. Please clarify whether the task is about farmland, illegal factories, "
            "hillside overuse, waterway dumping, solar PV legality, TOD, or another case family."
        )

    explanation = llm_explain_sop_match(user_request, selected)
    selected_sop = {
        "workflow_id": selected_id,
        "title": selected.get("title") or selected_id,
        "confidence": float(selected.get("score") or 0.0),
        "reason": explanation["reason"],
        "source_citation": selected.get("citation") or {},
    }
    return {
        "success": True,
        "selected_sop": selected_sop,
        "alternatives": ranked[1:],
        "needs_clarification": needs_clarification,
        "clarification_question": clarification_question,
    }


def _step(
    step_id: str,
    source_sop_step: str,
    tool: str,
    purpose: str,
    *,
    required_inputs: list[str] | None = None,
    auto_executable: bool = True,
    risk: str = "low",
    approval_required: bool = False,
    args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "source_sop_step": source_sop_step,
        "tool": tool,
        "purpose": purpose,
        "required_inputs": required_inputs or [],
        "auto_executable": auto_executable,
        "risk": risk,
        "approval_required": approval_required,
        "args": args or {},
    }


def _build_approval_checkpoint(action: str, label: str, risk: str, consequence: str, fallback: str) -> dict[str, Any]:
    return {
        "approval_id": action,
        "action": action,
        "label": label,
        "risk": risk,
        "buttons": [{"id": "approve", "label": "同意"}, {"id": "deny", "label": "不同意"}],
        "consequence_if_approved": consequence,
        "fallback_if_denied": fallback,
    }


def _case_required_inputs(workflow_id: str) -> list[str]:
    for rule in _WORKFLOW_RULES:
        if rule["workflow_id"] == workflow_id:
            return list(rule["required_inputs"])
    return ["aoi", "time_range"]


def _case_needs_preview(workflow_id: str) -> bool:
    for rule in _WORKFLOW_RULES:
        if rule["workflow_id"] == workflow_id:
            return bool(rule.get("needs_preview"))
    return True


def _image_recognition_task(workflow_id: str) -> str:
    return {
        "WF-001": "factory_structure_screening",
        "WF-004": "river_dumping_check",
        "WF-005": "agri_pv_check",
        "WF-009": "landslide_hazard_check",
        "WF-010": "ecological_disturbance_check",
    }.get(workflow_id, "preliminary_image_recognition")


def _default_demo_aoi() -> dict[str, Any]:
    return {
        "west": 120.70,
        "south": 23.45,
        "east": 120.72,
        "north": 23.47,
        "crs": "EPSG:4326",
    }


def compile_plan(selected_sop: dict[str, Any], available_inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    available_inputs = dict(available_inputs or {})
    selected = dict(selected_sop or {})
    workflow_id = _normalize_text(selected.get("workflow_id")) or "unknown"
    case = _workflow_case_by_id(workflow_id) or {}
    source_record = case.get("source_record") or {}

    title = _normalize_text(selected.get("title") or case.get("title") or workflow_id)
    aoi = available_inputs.get("aoi")
    time_range = available_inputs.get("time_range")
    parcel_id = available_inputs.get("parcel_id")
    landuse_layer = available_inputs.get("landuse_layer")
    legal_jurisdiction = _normalize_text(available_inputs.get("legal_jurisdiction")) or "Taiwan"

    source_sop_steps = _as_list(
        source_record.get("data_collection"),
        source_record.get("spatial_analysis"),
        source_record.get("rag_retrieval"),
        source_record.get("expected_response"),
        source_record.get("user_query"),
    )
    if not source_sop_steps:
        source_sop_steps = [f"Selected SOP: {title}"]

    required_inputs = _case_required_inputs(workflow_id)
    missing_inputs: list[str] = []
    for key in required_inputs:
        if not available_inputs.get(key):
            missing_inputs.append(key)
    if not aoi and "aoi" not in missing_inputs:
        missing_inputs.append("aoi")
    if _case_needs_preview(workflow_id) and not time_range and "time_range" not in missing_inputs:
        missing_inputs.append("time_range")
    if parcel_id is None and "parcel_id" in required_inputs and "parcel_id" not in missing_inputs:
        missing_inputs.append("parcel_id")
    if landuse_layer is None and "landuse_layer" in required_inputs and "landuse_layer" not in missing_inputs:
        missing_inputs.append("landuse_layer")

    steps: list[dict[str, Any]] = [
        _step("step_1", "SOP source citation", "geo_database.search", "Retrieve supporting SOP and grounded citations.", args={"query": title, "top_k": 5}),
        _step("step_2", "SOP retrieval grounding", "geo_database.rag_answer", "Generate a grounded answer summary from the local geo/legal database.", args={"question": title, "top_k": 8}),
        _step("step_3", "Workflow template", "geo_database.workflow_plan", "Produce a deterministic read-only workflow plan.", args={"task": title}),
        _step("step_4", "Dry run guard", "geo_database.workflow_dry_run", "Check missing inputs and blocked read-only steps.", args={"task": title, "workflow_plan": {}}),
        _step(
            "step_5",
            "Route imagery preview",
            "image_provider.route_request",
            "Route to a temporary imagery preview provider when relevant.",
            args={
                "request": {
                    "provider": "gee" if (_case_needs_preview(workflow_id) and aoi and time_range) else "mock",
                    "collection_hint": "Sentinel-2",
                    "aoi": aoi or {},
                    "time_range": time_range or [],
                    "bands": ["B4", "B3", "B2"],
                    "output_mode": "thumbnail",
                },
                "openeo_available": False,
            },
        ),
    ]

    if _case_needs_preview(workflow_id) and aoi and time_range:
        steps.append(
            _step(
                "step_5b",
                "Approval-gated GEE preview",
                "image_provider.gee_fetch_preview",
                "Fetch a small AOI thumbnail preview after user approval.",
                required_inputs=["aoi", "time_range"],
                auto_executable=False,
                risk="external_network",
                approval_required=True,
                args={
                    "collection": "COPERNICUS/S2_SR_HARMONIZED",
                    "aoi": aoi,
                    "time_range": time_range,
                    "bands": ["B4", "B3", "B2"],
                    "vis_params": {"min": 0, "max": 3000},
                    "output_mode": "thumbnail",
                },
            )
        )

    steps.extend(
        [
            _step(
                "step_6",
                "Build preview report",
                "image_provider.build_preview_report",
                "Standardize the temporary imagery preview response.",
                args={
                    "provider_response": {},
                    "original_request": {
                        "provider": "gee",
                        "collection_hint": "Sentinel-2",
                        "aoi": aoi or {},
                        "time_range": time_range or [],
                        "bands": ["B4", "B3", "B2"],
                        "output_mode": "thumbnail",
                    },
                    "workflow_context": {"primary_workflow": "openeo"},
                },
            ),
            _step("step_7", "Build preview card", "image_provider.build_preview_card", "Prepare a UI-friendly preview card.", args={"preview_report": {}}),
            _step("step_8", "Legal retrieval", "legal_database.search", "Retrieve legal sources relevant to the SOP.", args={"query": title, "top_k": 5}),
            _step("step_9", "Legal RAG", "legal_database.rag_answer", "Produce a preliminary legal answer with citations.", args={"question": title, "top_k": 8}),
        ]
    )

    if supports_image_recognition(workflow_id):
        steps.extend(
            [
                _step(
                    "step_10",
                    "Image recognition plan",
                    "image_recognition.plan_from_sop",
                    "Build a preliminary detection plan from the selected SOP.",
                    args={
                        "selected_sop": selected,
                        "compiled_plan": {},
                        "context": {
                            "aoi": aoi or {},
                            "time_range": time_range or [],
                            "landuse_context": {
                                "zone_type": "agricultural" if workflow_id in {"WF-001", "WF-005"} else "workflow_target_zone",
                                "legal_building_layer_available": False,
                            },
                            "legal_building_layer_available": False,
                        },
                    },
                ),
                _step(
                    "step_11",
                    "Run preliminary detector",
                    "image_recognition.run_detector",
                    "Generate preliminary suspected polygons or bounding boxes without networking.",
                    args={"recognition_request": {}},
                ),
                _step(
                    "step_12",
                    "Build detection overlay",
                    "image_recognition.build_overlay",
                    "Prepare a safe GeoJSON overlay for UI display.",
                    args={"recognition_result": {}},
                ),
                _step(
                    "step_13",
                    "Explain detections",
                    "image_recognition.explain_detections",
                    "Explain preliminary detections without changing geometry or legal meaning.",
                    args={"recognition_result": {}, "selected_sop": selected, "legal_context": {}},
                ),
            ]
        )

    steps.append(
        _step(
            "step_14" if supports_image_recognition(workflow_id) else "step_10",
            "Case report",
            "case_report.build",
            "Assemble a preliminary geo/legal case report.",
            args={
                "selected_sop": selected,
                "compiled_plan": {},
                "readonly_results": {},
                "imagery_preview_report": {},
                "legal_answer": {},
                "recognition_result": {},
                "recognition_overlay": {},
                "detection_explanation": {},
            },
        )
    )

    approval_checkpoints: list[dict[str, Any]] = []
    if _case_needs_preview(workflow_id) and aoi and time_range:
        approval_checkpoints.append(
            _build_approval_checkpoint(
                action="gee_fetch_preview",
                label="Use GEE for a small-AOI thumbnail preview",
                risk="external_network",
                consequence="Hermes will fetch a small AOI thumbnail preview only. No GeoTIFF/export/download will be performed.",
                fallback="Use mock preview or dry-run-only report instead.",
            )
        )
    approval_checkpoints.extend(
        [
            _build_approval_checkpoint("openeo_real_login_check", "Check real OpenEO login", "external_network", "Hermes will check whether a real OpenEO login could proceed.", "Stay with cached or mock capabilities."),
            _build_approval_checkpoint("openeo_capability_refresh", "Refresh OpenEO capability metadata", "external_network", "Hermes will refresh live capability metadata if allowed.", "Use cached capabilities only."),
            _build_approval_checkpoint("openeo_real_create_job", "Create a real OpenEO job", "submission", "Hermes will attempt an approval-gated OpenEO job submission.", "Keep the workflow read-only and remain on preview artifacts."),
            _build_approval_checkpoint("download_result", "Download result", "download", "Hermes would download a result artifact if explicitly approved.", "Keep the result as preview/report only."),
            _build_approval_checkpoint("formal_report_export", "Export formal report", "export", "Hermes would export a formal report artifact if explicitly approved.", "Keep the draft as a preliminary case report."),
            _build_approval_checkpoint("formal_legal_conclusion", "Issue a formal legal conclusion", "legal", "Hermes would attempt a formal legal conclusion.", "Keep the report preliminary and use cautious wording."),
        ]
    )

    compiled_plan = {
        "workflow_id": workflow_id,
        "title": title,
        "mode": "readonly_autonomous",
        "source": "expert_sop",
        "source_sop_steps": source_sop_steps,
        "steps": steps,
        "legal_jurisdiction": legal_jurisdiction,
        "approval_checkpoints": approval_checkpoints,
    }
    return {
        "success": True,
        "compiled_plan": compiled_plan,
        "missing_inputs": list(dict.fromkeys(missing_inputs)),
        "approval_checkpoints": approval_checkpoints,
        "legal_jurisdiction": legal_jurisdiction,
    }


def _invoke_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    try:
        from tools.registry import registry
    except Exception:
        return {"success": False, "error": "registry_unavailable"}

    entry = registry.get_entry(tool_name)
    if entry is None:
        return {"success": False, "error": "tool_missing"}
    try:
        raw = entry.handler(args or {})
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except Exception:
                return {"success": True, "raw": raw}
        if isinstance(raw, dict):
            return raw
        return {"success": True, "raw": raw}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def run_readonly(compiled_plan: dict[str, Any], execution_context: dict[str, Any] | None = None) -> dict[str, Any]:
    execution_context = dict(execution_context or {})
    plan = _as_dict(compiled_plan)
    steps = deepcopy(plan.get("steps") or [])
    selected_sop = _as_dict(execution_context.get("selected_sop"))
    user_request = _normalize_text(execution_context.get("user_request")) or _normalize_text(selected_sop.get("title"))

    state: dict[str, Any] = {
        "user_request": user_request,
        "selected_sop": selected_sop,
        "compiled_plan": plan,
        "aoi": execution_context.get("aoi"),
        "time_range": execution_context.get("time_range"),
        "parcel_id": execution_context.get("parcel_id"),
        "landuse_layer": execution_context.get("landuse_layer"),
    }

    executed_steps: list[dict[str, Any]] = []
    blocked_steps: list[dict[str, Any]] = []
    approval_checkpoints: list[dict[str, Any]] = []
    warnings: list[str] = _as_list(execution_context.get("warnings"))
    missing_inputs: list[str] = list(dict.fromkeys(_as_list(execution_context.get("missing_inputs"), plan.get("missing_inputs"))))

    for step in steps:
        tool = _normalize_text(step.get("tool"))
        if not tool:
            blocked_steps.append({"step_id": step.get("step_id"), "reason": "missing tool"})
            continue
        if step.get("approval_required"):
            approval_checkpoints.append(
                {
                    "approval_id": step.get("step_id"),
                    "action": tool,
                    "label": step.get("purpose") or tool,
                    "risk": step.get("risk") or "approval-required",
                }
            )
            blocked_steps.append({"step_id": step.get("step_id"), "reason": "approval required"})
            break
        if step.get("risk") not in {"low", "read-only", "preview-only"}:
            blocked_steps.append({"step_id": step.get("step_id"), "reason": "risky step"})
            continue

        args = dict(step.get("args") or {})
        if tool == "image_provider.route_request":
            args.setdefault(
                "request",
                {
                    "provider": "gee",
                    "collection_hint": "Sentinel-2",
                    "aoi": state.get("aoi") or {},
                    "time_range": state.get("time_range") or [],
                    "bands": ["B4", "B3", "B2"],
                    "output_mode": "thumbnail",
                },
            )
        elif tool == "image_provider.build_preview_report":
            if not args.get("provider_response"):
                args["provider_response"] = state.get("image_provider.route_request") or state.get("last_result") or {}
            provider_response = _as_dict(args.get("provider_response"))
            if not provider_response.get("not_replacing_workflow"):
                args["provider_response"] = {
                    "success": True,
                    "provider": "mock",
                    "mode": "thumbnail",
                    "source": "mock",
                    "not_replacing_workflow": True,
                    "thumbnail_url": None,
                    "metadata": {
                        "collection": "mock",
                        "time_range": state.get("time_range") or [],
                        "aoi_area_km2": 0.0,
                        "selected_image_count": 0,
                    },
                    "warnings": ["Temporary mock preview used to keep the workflow read-only."],
                    "limitations": ["Temporary preview only.", "OpenEO workflow remains the primary target."],
                }
            if not args.get("original_request"):
                args["original_request"] = {
                    "provider": "gee",
                    "collection_hint": "Sentinel-2",
                    "aoi": state.get("aoi") or {},
                    "time_range": state.get("time_range") or [],
                    "bands": ["B4", "B3", "B2"],
                    "output_mode": "thumbnail",
                }
            args.setdefault("workflow_context", {"primary_workflow": "openeo"})
        elif tool == "image_provider.build_preview_card":
            if not args.get("preview_report"):
                args["preview_report"] = state.get("image_provider.build_preview_report") or {}
            preview_report = _as_dict(args.get("preview_report"))
            if not preview_report.get("not_replacing_workflow"):
                args["preview_report"] = {
                    "success": True,
                    "provider": "mock",
                    "report_type": "temporary_imagery_preview",
                    "not_replacing_workflow": True,
                    "workflow_relation": {
                        "primary_workflow": "openeo",
                        "provider_role": "temporary imagery preview only",
                        "does_replace_workflow": False,
                    },
                    "preview": {"thumbnail_url": None, "metadata": {}},
                    "request_summary": {
                        "collection": "mock",
                        "aoi": state.get("aoi") or {},
                        "aoi_area_km2": 0.0,
                        "time_range": state.get("time_range") or [],
                        "bands": ["B4", "B3", "B2"],
                        "indices": [],
                    },
                    "warnings": ["Temporary mock preview used to keep the workflow read-only."],
                    "limitations": [
                        "Temporary preview only.",
                        "Not a formal analysis result.",
                        "No GeoTIFF/export/download performed.",
                        "OpenEO workflow remains the primary target.",
                    ],
                    "next_steps": ["Return to OpenEO workflow validation."],
                    "safe_display": True,
                }
        elif tool == "image_recognition.plan_from_sop":
            if not args.get("selected_sop"):
                args["selected_sop"] = selected_sop
            if not args.get("compiled_plan"):
                args["compiled_plan"] = plan
            if not args.get("context"):
                args["context"] = {
                    "aoi": state.get("aoi") or {},
                    "time_range": state.get("time_range") or [],
                    "landuse_context": {
                        "zone_type": "agricultural" if plan.get("workflow_id") in {"WF-001", "WF-005"} else "workflow_target_zone",
                        "legal_building_layer_available": bool(state.get("legal_building_layer_available")),
                    },
                    "legal_building_layer_available": bool(state.get("legal_building_layer_available")),
                }
        elif tool == "image_recognition.run_detector":
            if not args.get("recognition_request"):
                recognition_plan = _as_dict(state.get("image_recognition.plan_from_sop")).get("recognition_plan") or {}
                preview_report = _as_dict(state.get("image_provider.build_preview_report"))
                preview_payload = _as_dict(preview_report.get("preview"))
                image_url = _normalize_text(preview_payload.get("thumbnail_url"))
                detector_preference = _normalize_text(execution_context.get("detector_preference")) or (
                    "gee_thumbnail" if image_url else "mock"
                )
                args["recognition_request"] = {
                    "task": recognition_plan.get("task") or _image_recognition_task(_normalize_text(plan.get("workflow_id"))),
                    "sop_id": _normalize_text(plan.get("workflow_id")),
                    "image_source": "gee_thumbnail" if image_url else "mock",
                    "image_url": image_url or None,
                    "aoi": state.get("aoi") or _default_demo_aoi(),
                    "time_range": state.get("time_range") or [],
                    "target_classes": recognition_plan.get("target_classes") or ["building"],
                    "landuse_context": recognition_plan.get("landuse_context") or {
                        "zone_type": "agricultural" if plan.get("workflow_id") in {"WF-001", "WF-005"} else "workflow_target_zone",
                        "legal_building_layer_available": False,
                    },
                    "mode": detector_preference,
                }
                if execution_context.get("openeo_result"):
                    args["recognition_request"]["openeo_result"] = execution_context.get("openeo_result")
                if execution_context.get("segmentation_output"):
                    args["recognition_request"]["segmentation_output"] = execution_context.get("segmentation_output")
                if execution_context.get("local_image_path"):
                    args["recognition_request"]["local_image_path"] = execution_context.get("local_image_path")
                if execution_context.get("model_path"):
                    args["recognition_request"]["model_path"] = execution_context.get("model_path")
                if execution_context.get("model_type"):
                    args["recognition_request"]["model_type"] = execution_context.get("model_type")
        elif tool == "image_recognition.build_overlay":
            if not args.get("recognition_result"):
                detector_result = _as_dict(state.get("image_recognition.run_detector"))
                args["recognition_result"] = detector_result.get("recognition_result") or detector_result or {}
        elif tool == "image_recognition.explain_detections":
            if not args.get("recognition_result"):
                detector_result = _as_dict(state.get("image_recognition.run_detector"))
                args["recognition_result"] = detector_result.get("recognition_result") or detector_result or {}
            if not args.get("selected_sop"):
                args["selected_sop"] = selected_sop
            if not args.get("legal_context"):
                args["legal_context"] = state.get("legal_database.rag_answer") or {}
        elif tool == "case_report.build":
            if not args.get("selected_sop"):
                args["selected_sop"] = selected_sop
            if not args.get("compiled_plan"):
                args["compiled_plan"] = plan
            if not args.get("readonly_results"):
                args["readonly_results"] = {
                    "success": True,
                    "executed_steps": executed_steps,
                    "blocked_steps": blocked_steps,
                    "approval_checkpoints": approval_checkpoints,
                    "missing_inputs": missing_inputs,
                    "warnings": warnings,
                    "summary": {"status": "read-only"},
                }
            if not args.get("imagery_preview_report"):
                args["imagery_preview_report"] = state.get("image_provider.build_preview_report") or state.get("image_provider.build_preview_card") or {}
            if not args.get("legal_answer"):
                args["legal_answer"] = state.get("legal_database.rag_answer") or {}
            if not args.get("recognition_result"):
                recognition_result = _as_dict(state.get("image_recognition.run_detector"))
                args["recognition_result"] = recognition_result.get("recognition_result") or recognition_result or {}
            if not args.get("recognition_overlay"):
                recognition_overlay = _as_dict(state.get("image_recognition.build_overlay"))
                args["recognition_overlay"] = recognition_overlay.get("overlay") or recognition_overlay or {}
            if not args.get("detection_explanation"):
                args["detection_explanation"] = state.get("image_recognition.explain_detections") or {}
            if not args.get("citations"):
                args["citations"] = state.get("citations") or []
            if not args.get("missing_inputs"):
                args["missing_inputs"] = missing_inputs
            if not args.get("limitations"):
                args["limitations"] = warnings

        result = _invoke_tool(tool, args)
        state[tool] = result
        state["last_result"] = result
        if isinstance(result, dict) and result.get("citations"):
            state["citations"] = _as_list(state.get("citations"), result.get("citations"))

        if result.get("success", True):
            executed_steps.append(
                {
                    "step_id": step.get("step_id"),
                    "tool": tool,
                    "success": True,
                    "summary": result.get("summary")
                    or result.get("preview_card")
                    or result.get("preview_report")
                    or result.get("overlay")
                    or result.get("recognition_result")
                    or result.get("recognition_plan")
                    or result.get("explanation")
                    or result.get("answer")
                    or result.get("draft_report")
                    or result.get("raw"),
                }
            )
        else:
            warnings.append(str(result.get("error") or f"{tool} failed"))
            blocked_steps.append({"step_id": step.get("step_id"), "reason": result.get("error") or f"{tool} failed"})

    summary = {
        "status": "stopped_before_approval" if approval_checkpoints else "read_only_complete",
        "executed_step_count": len(executed_steps),
        "blocked_step_count": len(blocked_steps),
    }
    return {
        "success": True,
        "workflow_id": plan.get("workflow_id"),
        "executed_steps": executed_steps,
        "blocked_steps": blocked_steps,
        "approval_checkpoints": approval_checkpoints or plan.get("approval_checkpoints") or [],
        "missing_inputs": list(dict.fromkeys(missing_inputs)),
        "warnings": list(dict.fromkeys(warnings)),
        "summary": summary,
    }


def approval_checkpoint(compiled_plan: dict[str, Any], current_state: dict[str, Any] | None = None) -> dict[str, Any]:
    plan = _as_dict(compiled_plan)
    items = []
    for checkpoint in plan.get("approval_checkpoints") or []:
        checkpoint = _as_dict(checkpoint)
        if not checkpoint:
            continue
        items.append(
            {
                "approval_id": checkpoint.get("approval_id") or checkpoint.get("action"),
                "action": checkpoint.get("action"),
                "label": checkpoint.get("label"),
                "risk": checkpoint.get("risk") or "approval-required",
                "buttons": [{"id": "approve", "label": "同意"}, {"id": "deny", "label": "不同意"}],
                "consequence_if_approved": checkpoint.get("consequence_if_approved") or "",
                "fallback_if_denied": checkpoint.get("fallback_if_denied") or "Stay with the read-only report.",
            }
        )
    return {"success": True, "requires_user_decision": bool(items), "approval_items": items, "current_state": _as_dict(current_state)}


def llm_explain_compiled_plan(selected_sop: dict[str, Any], compiled_plan: dict[str, Any]) -> dict[str, Any]:
    sop = _as_dict(selected_sop)
    plan = _as_dict(compiled_plan)
    llm_result = chat_json(
        system_prompt=(
            "Explain a compiled SOP-driven geo/legal workflow plan. "
            "Do not claim formal analysis or legal conclusions. Return JSON with explanation."
        ),
        user_prompt=json.dumps({"selected_sop": sop, "compiled_plan": plan}, ensure_ascii=False, indent=2),
        schema_hint={
            "type": "object",
            "properties": {
                "explanation": {"type": "string"},
                "safety_notes": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["explanation"],
        },
    )
    if llm_result.get("success") and isinstance(llm_result.get("data"), dict):
        explanation = _normalize_text(llm_result["data"].get("explanation"))
        if explanation:
            return {
                "success": True,
                "explanation": explanation,
                "safety_notes": _as_list(llm_result["data"].get("safety_notes")),
                "fallback_used": False,
            }
    steps = plan.get("steps") or []
    return {
        "success": True,
        "explanation": f"Selected SOP {sop.get('title') or sop.get('workflow_id') or 'unknown'} is compiled into {len(steps)} read-only steps with approval gates.",
        "safety_notes": ["Read-only steps only.", "Approval is required before any external-network action."],
        "fallback_used": True,
    }


def retrieve(
    user_request: str,
    *,
    db_path: str | None = None,
    legal_db_path: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    return retrieve_sop_candidates(user_request, db_path=db_path, legal_db_path=legal_db_path, top_k=top_k)


def match(user_request: str, sop_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return match_sop_candidates(user_request, sop_candidates)


def compile_plan_tool(selected_sop: dict[str, Any], available_inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    return compile_plan(selected_sop, available_inputs)


def run_readonly_tool(compiled_plan: dict[str, Any], execution_context: dict[str, Any] | None = None) -> dict[str, Any]:
    return run_readonly(compiled_plan, execution_context)


def approval_checkpoint_tool(compiled_plan: dict[str, Any], current_state: dict[str, Any] | None = None) -> dict[str, Any]:
    return approval_checkpoint(compiled_plan, current_state)


def case_report_build_tool(
    selected_sop: dict[str, Any],
    compiled_plan: dict[str, Any],
    readonly_results: dict[str, Any] | None = None,
    imagery_preview_report: dict[str, Any] | None = None,
    legal_answer: dict[str, Any] | None = None,
    recognition_result: dict[str, Any] | None = None,
    recognition_overlay: dict[str, Any] | None = None,
    detection_explanation: dict[str, Any] | None = None,
    citations: list[Any] | None = None,
    missing_inputs: list[Any] | None = None,
    limitations: list[Any] | None = None,
) -> dict[str, Any]:
    return build_case_report(
        selected_sop=selected_sop,
        compiled_plan=compiled_plan,
        readonly_results=readonly_results,
        imagery_preview_report=imagery_preview_report,
        legal_answer=legal_answer,
        recognition_result=recognition_result,
        recognition_overlay=recognition_overlay,
        detection_explanation=detection_explanation,
        citations=citations,
        missing_inputs=missing_inputs,
        limitations=limitations,
    )


__all__ = [
    "approval_checkpoint",
    "approval_checkpoint_tool",
    "case_report_build_tool",
    "compile_plan",
    "compile_plan_tool",
    "llm_classify_intent",
    "llm_explain_compiled_plan",
    "llm_explain_sop_match",
    "llm_rewrite_query",
    "match",
    "match_sop_candidates",
    "retrieve",
    "retrieve_sop_candidates",
    "run_readonly",
    "run_readonly_tool",
]
