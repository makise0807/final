from __future__ import annotations

import re
from typing import Any


LAW_NAME_RE = re.compile(r"(?P<law>[一-龥A-Za-z0-9（）()、\-\s]{2,40}(?:法|條例|辦法|規則|自治條例))")
ARTICLE_RE = re.compile(r"第\s*(?P<article>[0-9一二三四五六七八九十百千零〇]+)\s*條")
PARAGRAPH_RE = re.compile(r"第\s*(?P<paragraph>[0-9一二三四五六七八九十百千零〇]+)\s*項")
ITEM_RE = re.compile(r"第\s*(?P<item>[0-9一二三四五六七八九十百千零〇]+)\s*款")
PENALTY_RE = re.compile(r"處\s*新臺幣(?P<penalty>[^。；，]{4,40}?罰鍰)")
ACTION_TERMS = [
    "限期變更使用",
    "停止使用",
    "拆除地上物恢復原狀",
    "恢復原狀",
    "限期改善",
    "裁處",
]
KEYWORD_TERMS = [
    "農業區",
    "違章工廠",
    "非都市土地",
    "使用管制",
    "農地種電",
    "河川行水區",
    "山坡地保育",
    "都市更新",
    "TOD",
    "生態敏感區",
]


def _find_all(pattern: re.Pattern[str], text: str, key: str) -> list[str]:
    values: list[str] = []
    for match in pattern.finditer(text):
        value = str(match.group(key) or "").strip()
        if value:
            values.append(value)
    return values


def parse_legal_citation(text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    content = str(text or "")
    metadata = dict(metadata or {})
    law_names = _find_all(LAW_NAME_RE, content, "law")
    law_name = str(metadata.get("law_name") or (law_names[0] if law_names else "")).strip() or None
    if law_name and law_name.startswith("依"):
        law_name = law_name[1:]
    article_no = str(metadata.get("article_no") or (_find_all(ARTICLE_RE, content, "article")[0] if _find_all(ARTICLE_RE, content, "article") else "")).strip() or None
    paragraph_no = str(metadata.get("paragraph_no") or (_find_all(PARAGRAPH_RE, content, "paragraph")[0] if _find_all(PARAGRAPH_RE, content, "paragraph") else "")).strip() or None
    item_no = str(metadata.get("item_no") or (_find_all(ITEM_RE, content, "item")[0] if _find_all(ITEM_RE, content, "item") else "")).strip() or None
    penalty_text = None
    penalty_match = PENALTY_RE.search(content)
    if penalty_match:
        penalty_text = f"新臺幣{penalty_match.group('penalty')}"

    key_terms = [term for term in KEYWORD_TERMS if term in content]
    actions = [term for term in ACTION_TERMS if term in content]
    citation_key_parts = [part for part in [law_name, f"第{article_no}條" if article_no else None, f"第{paragraph_no}項" if paragraph_no else None, f"第{item_no}款" if item_no else None] if part]

    return {
        "law_name": law_name,
        "article_no": article_no,
        "paragraph_no": paragraph_no,
        "item_no": item_no,
        "penalty_text": penalty_text,
        "actions": actions,
        "key_terms": key_terms,
        "citation_key": " ".join(citation_key_parts).strip() or None,
        "raw_text": content,
    }
