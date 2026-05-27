from __future__ import annotations

import json

from plugins.geo_expert.adapters.rag_tools import search_regulations
from plugins.geo_expert.legal_grounding.legal_citation_parser import parse_legal_citation


TOPICS = {
    "illegal_factory_agriculture": "農業區違章工廠",
    "non_urban_land_use_control": "非都市土地使用管制",
    "solar_on_farmland": "農地種電",
    "river_management_zone": "河川行水區",
    "hillside_conservation": "山坡地保育",
}


def audit_legal_rag() -> dict:
    coverage = {}
    laws: set[str] = set()
    legal_text_count = 0
    missing_topics: list[str] = []
    collection = None
    used_real = False
    for topic, query in TOPICS.items():
        result = search_regulations(query, top_k=5)
        used_real = used_real or bool(result.get("used_real_service"))
        collection = collection or result.get("collection") or result.get("selected_collection")
        entries = []
        for item in result.get("results") or []:
            parsed = parse_legal_citation(str(item.get("content") or ""), item.get("metadata") or {})
            if parsed.get("law_name"):
                laws.add(str(parsed["law_name"]))
            if (item.get("metadata") or {}).get("source_type") == "legal_text":
                legal_text_count += 1
            entries.append(
                {
                    "title": item.get("title"),
                    "citation_key": parsed.get("citation_key") or item.get("citation"),
                    "law_name": parsed.get("law_name"),
                    "article_no": parsed.get("article_no"),
                    "issue_tags": (item.get("metadata") or {}).get("issue_tags") or [],
                }
            )
        coverage[topic] = {
            "query": query,
            "hit_count": len(entries),
            "entries": entries,
            "used_real_service": bool(result.get("used_real_service")),
        }
        if not entries:
            missing_topics.append(topic)
    return {
        "success": True,
        "status": "success" if used_real and not missing_topics else "degraded",
        "collection": collection or "urban_regulations",
        "legal_text_count": legal_text_count,
        "laws": sorted(laws),
        "coverage": coverage,
        "missing_topics": missing_topics,
        "used_real_service": used_real,
    }


def main() -> int:
    print(json.dumps(audit_legal_rag(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
