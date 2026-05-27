from __future__ import annotations

from typing import Any

from ..adapters.satellite_tools import acquire_satellite_preview
from ..user_data.user_data_rag import answer_user_data_question, search_user_data
from .pack_registry import load_pack
from .report_templates import build_pack_report


PACK_ANALYSIS_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "real_estate_insight": {
        "observations": [
            "周邊環境摘要：本包會先以衛星預覽確認基地與周邊空間紋理。",
            "綠地 / 開放空間觀察：優先檢查是否鄰近綠地、水體或可辨識開放空間。",
            "道路 / 可達性觀察：以可視道路與出入口紋理作為初步可達性提示。",
            "買方風險提醒：若影像來源不精準或資料不足，需保留買方盡職調查空間。",
            "銷售亮點建議：若周邊空間整體開闊，可作為生活環境敘事的初步素材。",
        ],
        "risks": [
            "本分析不是正式估價或法定產權意見。",
            "若 AOI 僅為 fallback cache 命中，周邊判讀只可視為弱訊號。",
        ],
        "opportunities": [
            "可結合使用者提供的物件說明、區位筆記與現勘紀錄做更具體描述。",
        ],
        "next_actions": [
            "補充物件現勘照片或銷售筆記。",
            "交叉比對地籍、法規與現地交通條件。",
        ],
    },
    "geo_classroom": {
        "observations": [
            "教學目標：用單一案例讓學生學會從衛星圖辨識地表差異。",
            "衛星圖觀察問題：可引導學生比較建成區、綠地與水體紋理。",
            "學生學習單題目：請學生描述影像中最明顯的空間特徵。",
            "教師講解重點：提醒影像是時間切片，不代表長期穩定狀態。",
            "延伸活動：可要求學生比對地圖、新聞或課堂資料進行補證。",
        ],
        "risks": [
            "教材用途不應被誤解為正式測量或遙測成果。",
            "缺少學生自備資料時，討論深度會受限。",
        ],
        "opportunities": [
            "可納入教師提供的地方史、新聞或課堂講義作為使用者資料。",
        ],
        "next_actions": [
            "匯入教師講義或學習單作為 user data。",
            "讓學生對照不同比例尺底圖進行討論。",
        ],
    },
    "public_inspection": {
        "observations": [
            "疑似異常指標：先標出與周邊紋理不一致的可疑空間。",
            "稽查優先順序：優先處理影像可見變動較大或來源資料較完整者。",
            "現勘 checklist：準備現場拍照、定位、周邊界址與時間戳記。",
            "需補證據：若缺 user data，僅能先列出待補佐證清單。",
            "限制聲明：衛星圖僅供稽查前置排序，不能直接替代認定。",
        ],
        "risks": [
            "沒有現勘與法源對照，不可直接形成處分結論。",
        ],
        "opportunities": [
            "可結合陳情資料、巡查筆記、案件照片提高前置判讀效率。",
        ],
        "next_actions": [
            "安排現場複核與拍照。",
            "比對陳情或歷次巡查紀錄。",
        ],
    },
    "agriculture_monitor": {
        "observations": [
            "植被 / 土地使用觀察：先辨識是否存在明顯綠色覆蓋與田區紋理。",
            "裸露地 / 田區變化：若可見大面積裸露或翻動，列為後續追蹤重點。",
            "作物壓力提示：本包只能提供視覺線索，不做作物生理診斷。",
            "監測頻率建議：建議以固定間隔重新檢視同區衛星預覽。",
            "農民 / 機關下一步：可結合農務紀錄或巡查紀錄補齊背景。",
        ],
        "risks": [
            "未使用光譜分析，不足以判定作物健康。",
        ],
        "opportunities": [
            "適合作為農務巡查、田區變化筆記的彙整入口。",
        ],
        "next_actions": [
            "匯入田區紀錄或巡查照片。",
            "安排週期性人工複核。",
        ],
    },
    "disaster_rapid_scan": {
        "observations": [
            "疑似受影響區：先標記影像中需要優先留意的空間區塊。",
            "道路 / 可達性疑慮：若周邊道路稀少，應提高抵達風險意識。",
            "淹水 / 崩塌提示：本包只提供地表線索，不做正式災損認定。",
            "優先巡查區：先巡查影像最不清楚或變化最可疑的區域。",
            "災後應變 checklist：包含道路狀況、聯外動線、次生災害觀察。",
        ],
        "risks": [
            "快速掃描不等於官方災情通報。",
        ],
        "opportunities": [
            "可結合災情回報、照片與地方單位紀錄快速整理情資。",
        ],
        "next_actions": [
            "匯入災情照片或通報文字。",
            "安排現地巡查或交由應變單位確認。",
        ],
    },
    "esg_environment": {
        "observations": [
            "周邊環境概況：先描述基地與周邊空間組成。",
            "土地變化觀察：若使用者提供歷史資料，可納入變化敘述。",
            "綠地 / 水體 / 開放空間：作為 ESG 情境說明的初步素材。",
            "ESG 揭露提示：可列出需補足的環境佐證與揭露項目。",
            "風險 caveat：此結果僅支援揭露前整理，不代表 ESG 查核結果。",
        ],
        "risks": [
            "不能替代正式 ESG 盤查或永續報告查證。",
        ],
        "opportunities": [
            "可將企業場址紀錄、CSR 筆記或環評摘要納入 user data。",
        ],
        "next_actions": [
            "補充場址環境資料。",
            "交由 ESG / 永續團隊做正式揭露審查。",
        ],
    },
    "outdoor_safety": {
        "observations": [
            "地形環境：先判讀是否屬開闊、坡地或水體鄰近空間。",
            "水體 / 坡地鄰近性：若鄰近水域或高差，需提高風險意識。",
            "路線可達性：僅能從影像可視紋理做初步推估。",
            "戶外風險提示：本包用於活動前提醒，不做救援保證。",
            "安全聲明：仍需現地踏勘與天候評估。",
        ],
        "risks": [
            "沒有現地資料時，戶外風險只能做保守提醒。",
        ],
        "opportunities": [
            "適合整合活動計畫、路線筆記與現場照片。",
        ],
        "next_actions": [
            "補充路線圖與現地照片。",
            "確認天候與緊急應變計畫。",
        ],
    },
    "media_investigation": {
        "observations": [
            "衛星圖觀察：先整理影像可見的空間特徵與異常線索。",
            "時間線提示：若有使用者提供時序資料，可作為敘事補充。",
            "佐證資料 checklist：列出需要交叉驗證的文件、照片、訪談或地圖資料。",
            "待查問題：把尚未證實的敘述轉成待查清單，而非直接定論。",
            "來源限制聲明：影像與 user data 都需要新聞編輯流程複核。",
        ],
        "risks": [
            "不得把初步衛星觀察直接當作已證實事實。",
        ],
        "opportunities": [
            "適合彙整記者筆記、訪談重點與公開資料來源。",
        ],
        "next_actions": [
            "補足公開文件、採訪紀錄或時間線資料。",
            "交由編輯與查核流程複核。",
        ],
    },
    "urban_planning": {
        "observations": [
            "現況土地使用觀察：先描述基地與周邊的可見空間型態。",
            "開發機會：若周邊開放空間或道路條件良好，可列入機會項。",
            "交通 / 開放空間：以衛星圖紋理作初步空間支持觀察。",
            "限制條件提示：若缺法規或分區資料，需明確標註限制。",
            "規劃下一步：建議後續串接都市計畫與地籍資料複核。",
        ],
        "risks": [
            "本包不是正式都市計畫審查結果。",
        ],
        "opportunities": [
            "可納入基地評估筆記、規劃草圖與訪談紀錄。",
        ],
        "next_actions": [
            "匯入規劃說明與基地資料。",
            "比對法規、分區與地籍結果。",
        ],
    },
    "climate_land_change": {
        "observations": [
            "變遷觀察：先記錄目前影像中值得追蹤的土地紋理。",
            "土地覆蓋提示：若使用者提供歷史資料，可輔助比較覆蓋型態。",
            "環境指標：僅提供研究線索，不輸出正式監測指標。",
            "研究問題：將影像線索轉成可驗證的研究提問。",
            "監測建議：建議以固定時間點重複檢視或補充其他資料來源。",
        ],
        "risks": [
            "本包不是正式氣候或土地覆蓋分類模型輸出。",
        ],
        "opportunities": [
            "可結合研究筆記、外部觀測資料與地面調查紀錄。",
        ],
        "next_actions": [
            "匯入研究筆記與歷史資料。",
            "規劃後續監測時間點與驗證方法。",
        ],
    },
}


def _satellite_status(satellite_evidence: dict[str, Any]) -> str:
    return str(
        satellite_evidence.get("status")
        or satellite_evidence.get("match_strategy")
        or "satellite_context_unavailable"
    )


def _build_analysis(
    pack: dict[str, Any],
    satellite_evidence: dict[str, Any],
    user_rag: dict[str, Any],
) -> dict[str, Any]:
    template = PACK_ANALYSIS_TEMPLATES.get(pack.get("pack_id"), {})
    observations = list(template.get("observations") or [])
    risks = list(template.get("risks") or [])
    opportunities = list(template.get("opportunities") or [])
    next_actions = list(template.get("next_actions") or [])

    observations.append(f"衛星資料狀態：{_satellite_status(satellite_evidence)}。")
    if user_rag.get("status") == "ok":
        observations.append(
            f"使用者資料整合：已納入 {len(user_rag.get('hits') or [])} 筆 user-data 命中作為輔助線索。"
        )
    else:
        risks.append("目前未提供使用者資料，因此使用者資料段落僅能回報缺件狀態。")
        next_actions.append("若需提升情境判讀，可匯入與本 pack 相關的文字、表格或紀錄資料。")

    return {
        "observations": observations[:8],
        "risks": risks,
        "opportunities": opportunities,
        "next_actions": list(dict.fromkeys(next_actions)),
    }


def run_pack(pack_id: str, user_request: str, inputs: dict[str, Any] | None = None, mode: str = "safe_run") -> dict[str, Any]:
    inputs = dict(inputs or {})
    loaded = load_pack(pack_id)
    if not loaded.get("success"):
        return loaded
    pack = dict(loaded["pack"])

    satellite_evidence = acquire_satellite_preview(
        aoi=inputs.get("aoi") or inputs.get("bbox"),
        bbox=inputs.get("bbox"),
        case_id=str(inputs.get("case_id") or ""),
        workflow_id=str(inputs.get("workflow_id") or pack_id),
        mode="prepare_only" if mode == "dry_run" else "cache_only",
    )

    dataset_ids = [str(item) for item in list(inputs.get("dataset_ids") or []) if str(item).strip()]
    user_rag = search_user_data(
        pack["pack_id"],
        user_request,
        dataset_ids=dataset_ids,
        top_k=5,
        collection_name=str(pack.get("user_data_collection") or ""),
    )
    rag_answer = answer_user_data_question(
        pack["pack_id"],
        user_request,
        dataset_ids=dataset_ids,
        top_k=3,
        collection_name=str(pack.get("user_data_collection") or ""),
    )
    analysis = _build_analysis(pack, satellite_evidence, user_rag)
    report = build_pack_report(pack, user_request, inputs, satellite_evidence, user_rag, analysis)

    degraded_reasons: list[str] = []
    if satellite_evidence.get("status") == "degraded":
        degraded_reasons.append("satellite_evidence_degraded")
    if user_rag.get("status") != "ok":
        degraded_reasons.append(str(user_rag.get("status") or "user_rag_degraded"))

    warnings = list(
        dict.fromkeys(
            [
                *(satellite_evidence.get("warnings") or []),
                *(user_rag.get("warnings") or []),
                *(rag_answer.get("warnings") or []),
            ]
        )
    )
    limitations = list(
        dict.fromkeys(
            [
                *(satellite_evidence.get("limitations") or []),
                *(user_rag.get("limitations") or []),
                "Deterministic domain template only.",
                "Not a formal satellite analysis.",
                "No formal legal conclusion.",
            ]
        )
    )
    next_actions = list(dict.fromkeys(analysis.get("next_actions") or []))

    return {
        "success": True,
        "pack_id": pack["pack_id"],
        "title": pack.get("title"),
        "title_zh": pack.get("title_zh"),
        "status": "degraded" if degraded_reasons else "success",
        "mode": mode,
        "satellite_evidence": satellite_evidence,
        "user_rag": user_rag,
        "analysis": analysis,
        "report": report,
        "rag_answer": rag_answer,
        "warnings": warnings,
        "limitations": limitations,
        "next_actions": next_actions,
    }
