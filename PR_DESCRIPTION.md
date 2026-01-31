# PR 标题

feat: 引入结构化输出模型、CLI 与 CI；增加 Orchestrator 结构化桥接

---

# PR 描述（复制下面整段到 GitHub 的 PR 描述框）

## 变更综述

- 将评审结果统一为结构化 JSON（可编程、可复现）
- 新增命令行入口（CLI）把 PRD 文本一键转为结构化报告
- 接入 GitHub Actions（CI）自动跑单测与 CLI，并上传报告为构建产物
- 预留与现有 Orchestrator 的桥接入口，后续可直接复用「多 Agent + VP 决策」编排

## 修改文件

| 类型 | 文件 | 说明 |
|------|------|------|
| 新增 | `models.py` | 统一数据模型（Finding / Advice / PanelItem / ExecSummary） |
| 新增 | `structure_adapter.py` | LLM/原始输出的容错解析与聚合 |
| 新增 | `structured_orchestrator.py` | 并行跑角色、聚合为结构化报告 |
| 新增 | `cli.py` | 命令行入口；先提供假数据跑通最短闭环 |
| 新增 | `tests/test_structured_output.py` | 基础单测与模型校验 |
| 新增 | `.github/workflows/ci.yml` | CI 跑单测与 CLI，产出 review-report 构建产物 |
| 预留 | `orchestrator_structured_bridge.py` | 与现有 Orchestrator 对接的桥接函数（可选落地） |
| 修改 | `.gitignore` / `app.py` / `requirements.txt` / `README.md` | 见仓库变更 |

## 动机与意义

- **标准化能力入口**：从「只能在 UI 点」升级为「可编程/可自动化」的工具
- **批量评测与对比**：支持在本地与 CI 批量跑样例 PRD，量化阻断项召回与评分变化
- **报告可复现**：每次提交自动生成结构化报告，评审者无需跑 UI 即可查看结果

## 技术细节

**结构化模型（统一数据结构）**

- `Finding{id, title, severity, rationale}`
- `Advice{for_pm, for_eng}`
- `PanelItem{role, findings[], advice, score(0..100)}`
- `ExecSummary{total_score(0..100), blockers[], decision, items[]}`

**容错解析与聚合**

- `parse_json_safely`：去除代码块、中文引号、尾逗号等，尽量转为合法 JSON
- `to_panel_item`：统一角色输出为 PanelItem；严重级别仅允许 P0/P1/P2
- `aggregate_panel_items`：计算平均分、阻断项与最终决策（有 P0 → Block）

**并行编排**

- `run_review(prd_text, role_runner)`：并发执行 CTO/UXD/QA 角色；将原始结果结构化并聚合返回

**CLI 最短闭环**

```bash
python cli.py --input examples/prd_samples/sample1.md --output out/sample1.json
```

产出结构化报告 JSON，作为对外演示与 CI 构建产物。

**CI 工作流**

安装依赖 → 跑 pytest → 执行 CLI → 上传 `out/sample1.json`（artifact 名称 `review-report`）

**Orchestrator 桥接（可选）**

- `role_runner(role, prd_text)` 内部调用现有多 Agent 评审；返回字典或 JSON 字符串
- `run_review_structured(prd_text)` 复用 `run_review`，保持结构化输出不变

## 收益与指标

- **输出可编程**：统一 JSON 模型，便于统计阻断项、评分、对比实验
- **可复现与不回退**：CLI + CI 固化运行路径，每次改动自动生成报告
- **易集成**：一条命令即可使用；对现有 UI 零侵入（桥接后复用编排）

## 验收标准

- 本地命令可运行：`python cli.py --input examples/prd_samples/sample1.md --output out/sample1.json`
- 报告包含：`total_score`（0–100）、`blockers`（至少包含所有 P0 的标题）、`decision` ∈ {Block, Proceed with fixes}、`items` 同时包含 CTO/UXD/QA 三角色
- `pytest` 通过；GitHub Actions 成功且产出 artifact `review-report/out/sample1.json`

## 使用方式

**本地**

```bash
# 准备示例
echo "# demo prd" > examples/prd_samples/sample1.md
# 运行
python cli.py --input examples/prd_samples/sample1.md --output out/sample1.json
# 查看
cat out/sample1.json
```

**CI 构建产物**

在 PR 页面 → Checks → Artifacts → 下载 `review-report` 查看报告

## 兼容性与风险

- **兼容性**：不修改现有 Streamlit UI；新增 CLI/CI 与桥接文件
- **风险控制**：模型校验与单测覆盖基本解析与聚合逻辑；JSON 容错解析兜底，避免 LLM 返回不合法格式导致崩溃
- **安全**：不记录或上传 API Key；日志与构建产物不包含敏感信息

## 后续迭代计划

- 替换 `demo_runner` 为真实 `agent_review` + VP，在 CLI 复用现有编排
- 增加基准集批量跑与指标看板（召回率、P0 比例、平均分）
- 引入规则引擎与静态 Lint，形成「规则 + 智能」的两段流
- 增加更多角色/场景（如 API Contract Guardian）构建系列化能力

## PR 检查清单

- [ ] 新增文件均存在且无语法错误
- [ ] `pytest` 通过
- [ ] CLI 本地可跑，生成 `out/sample1.json`
- [ ] CI 成功并产出 `review-report`
- [ ] PR 描述清晰，包含动机、改动与收益
