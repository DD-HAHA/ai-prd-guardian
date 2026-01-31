import json
import re
from typing import Any, Dict, List

from models import PanelItem, Finding, Advice, ExecSummary


def parse_json_safely(s: str) -> Dict[str, Any]:
    """去除 ```json 代码块、中文引号、尾逗号，尽可能返回 dict。"""
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"```\s*$", "", s)
    i = s.find("{")
    j = s.rfind("}")
    if i != -1 and j != -1 and j > i:
        s = s[i : j + 1]
    s = s.replace(""", '"').replace(""", '"').replace("'", "'").replace("'", "'")
    # 尾逗号：移除 , 后紧跟 } 或 ] 的逗号（可多次以处理嵌套）
    for _ in range(5):
        s = re.sub(r",\s*([}\]])", r"\1", s)
    try:
        return json.loads(s)
    except Exception:
        return {}


def to_panel_item(raw: Any, role_hint: str = "") -> PanelItem:
    """把各角色原始输出转为结构化 PanelItem。"""
    data = raw if isinstance(raw, dict) else parse_json_safely(str(raw))
    role = data.get("role") or role_hint or "Unknown"
    score = int(data.get("score", 80))
    score = max(0, min(100, score))
    items = data.get("findings") or data.get("issues") or []
    findings: List[Finding] = []
    for idx, f in enumerate(items):
        if not isinstance(f, dict):
            continue
        fid = f.get("id") or f"F-{idx + 1:03d}"
        title = f.get("title") or ""
        sev = (f.get("severity") or "P1").upper().strip()
        if sev not in {"P0", "P1", "P2"}:
            sev = "P1"
        rationale = f.get("rationale") or ""
        findings.append(Finding(id=fid, title=title, severity=sev, rationale=rationale))
    advice_dict = data.get("advice") or {}
    for_pm = advice_dict.get("for_pm") or data.get("pm_advice") or ""
    for_eng = advice_dict.get("for_eng") or data.get("eng_advice") or ""
    advice = Advice(for_pm=for_pm, for_eng=for_eng)
    return PanelItem(role=role, findings=findings, advice=advice, score=score)


def aggregate_panel_items(items: List[PanelItem]) -> ExecSummary:
    """计算 total_score（平均）、blockers（所有 P0 标题）、decision。"""
    if not items:
        return ExecSummary(total_score=0, blockers=[], decision="Block", items=[])
    blockers = [f.title for i in items for f in i.findings if f.severity == "P0"]
    total = round(sum(i.score for i in items) / len(items))
    total = max(0, min(100, total))
    decision = "Block" if blockers else "Proceed with fixes"
    return ExecSummary(total_score=total, blockers=blockers, decision=decision, items=items)
