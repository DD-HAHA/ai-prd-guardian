import argparse
import asyncio
import json
from pathlib import Path

from structured_orchestrator import run_review


async def demo_runner(role: str, prd_text: str) -> dict:
    """占位 runner：返回符合结构的假数据，确保端到端跑通。"""
    if role == "CTO":
        return {
            "role": role,
            "score": 85,
            "findings": [
                {"id": "F-001", "title": "缺少幂等性说明", "severity": "P0", "rationale": "重复提交可能导致资损"},
                {"id": "F-002", "title": "错误码未统一", "severity": "P1", "rationale": "难以观测与重试"},
            ],
            "advice": {"for_pm": "补充接口约束与异常流覆盖", "for_eng": "引入幂等键与统一错误码"},
        }
    if role == "UXD":
        return {
            "role": role,
            "score": 88,
            "findings": [
                {"id": "F-003", "title": "错误态文案不一致", "severity": "P1", "rationale": "提升容错与一致性"},
            ],
            "advice": {"for_pm": "规范错误文案与占位", "for_eng": "前端统一文案源"},
        }
    return {
        "role": role,
        "score": 90,
        "findings": [
            {"id": "F-004", "title": "弱网重试策略缺失", "severity": "P1", "rationale": "易导致失败体验差"},
        ],
        "advice": {"for_pm": "补充弱网与重试策略", "for_eng": "添加退避与超时机制"},
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Path to PRD file (e.g. prd.md)")
    p.add_argument("--output", required=True, help="Path to output JSON report")
    args = p.parse_args()
    text = Path(args.input).read_text(encoding="utf-8")
    result = asyncio.run(run_review(text, demo_runner))
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved result to {args.output}")


if __name__ == "__main__":
    main()
