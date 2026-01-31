import asyncio
from typing import Any, Awaitable, Callable, Dict, List

from structure_adapter import aggregate_panel_items, to_panel_item

RoleRunner = Callable[[str, str], Awaitable[Any]]


async def run_review(prd_text: str, role_runner: RoleRunner) -> Dict:
    """并行跑 CTO/UXD/QA，结构化后聚合并返回 ExecSummary 的 dict。"""
    roles = ["CTO", "UXD", "QA"]
    tasks = [role_runner(r, prd_text) for r in roles]
    raw_results = await asyncio.gather(*tasks)
    items = [to_panel_item(raw_results[i], roles[i]) for i in range(len(roles))]
    summary = aggregate_panel_items(items)
    return summary.model_dump()
