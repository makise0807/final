from __future__ import annotations

from plugins.geo_expert.legal_grounding.legal_citation_parser import parse_legal_citation


def test_parse_chinese_article_and_penalty() -> None:
    text = "依區域計畫法第十五條第三項規定，處新臺幣六萬元以上三十萬元以下罰鍰，並得限期變更使用。"
    parsed = parse_legal_citation(text)
    assert parsed["law_name"] == "區域計畫法"
    assert parsed["article_no"] == "十五"
    assert parsed["paragraph_no"] == "三"
    assert "新臺幣六萬元以上三十萬元以下罰鍰" == parsed["penalty_text"]
    assert "限期變更使用" in parsed["actions"]


def test_parse_numeric_article() -> None:
    text = "非都市土地使用管制規則第15條第1項第2款"
    parsed = parse_legal_citation(text)
    assert parsed["law_name"] == "非都市土地使用管制規則"
    assert parsed["article_no"] == "15"
    assert parsed["paragraph_no"] == "1"
    assert parsed["item_no"] == "2"
