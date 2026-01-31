from models import PanelItem

from structure_adapter import (
    aggregate_panel_items,
    parse_json_safely,
    to_panel_item,
)


def test_parse_json_safely_code_fence_and_trailing_commas() -> None:
    s = """```json
    { "role": "CTO", "score": 80, "findings": [{"id":"F-1","title":"x","severity":"P0","rationale":"y"},], }
    ```"""
    d = parse_json_safely(s)
    assert d.get("role") == "CTO"
    assert d.get("score") == 80
    assert isinstance(d.get("findings"), list)


def test_to_panel_item_and_aggregate() -> None:
    raw = {
        "role": "QA",
        "score": 90,
        "findings": [{"id": "F-1", "title": "A", "severity": "P1", "rationale": "B"}],
        "advice": {"for_pm": "p", "for_eng": "e"},
    }
    item = to_panel_item(raw)
    assert isinstance(item, PanelItem)
    summary = aggregate_panel_items([item])
    assert summary.total_score == 90
    assert summary.decision == "Proceed with fixes"


def test_aggregate_blockers_from_p0() -> None:
    raw_cto = {
        "role": "CTO",
        "score": 70,
        "findings": [{"id": "F-1", "title": "阻断项标题", "severity": "P0", "rationale": "风险"}],
        "advice": {"for_pm": "", "for_eng": ""},
    }
    item = to_panel_item(raw_cto)
    summary = aggregate_panel_items([item])
    assert summary.blockers == ["阻断项标题"]
    assert summary.decision == "Block"
