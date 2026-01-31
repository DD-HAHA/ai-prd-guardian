"""
桥接：在需要时用「现有每角色评审逻辑」跑一遍评审，并返回结构化 ExecSummary 的 dict。
默认使用 demo_runner；要接真实 LLM 时，传入可选的 role_runner（内部调用现有逻辑，
若返回纯文本则先用 structure_adapter.parse_json_safely 转 dict）。
"""
import asyncio
from typing import Any, Awaitable, Callable, Dict, Optional

from cli import demo_runner
from structured_orchestrator import run_review

RoleRunner = Callable[[str, str], Awaitable[Any]]


async def role_runner_placeholder(role: str, prd_text: str) -> Any:
    """
    占位：接入真实 LLM 时，替换为调用现有每角色评审逻辑；
    若该逻辑返回纯文本，先用 structure_adapter.parse_json_safely(s) 转 dict 再返回。
    """
    return await demo_runner(role, prd_text)


async def run_review_structured(
    prd_text: str,
    role_runner: Optional[RoleRunner] = None,
) -> Dict:
    """跑评审并返回 ExecSummary 的 dict。默认用 demo_runner。"""
    runner = role_runner if role_runner is not None else demo_runner
    return await run_review(prd_text, runner)


def run_review_structured_sync(
    prd_text: str,
    role_runner: Optional[RoleRunner] = None,
) -> Dict:
    """同步入口：供非 async 调用方（如 Streamlit）使用。"""
    return asyncio.run(run_review_structured(prd_text, role_runner))
