import streamlit as st
import json
import re
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# 加载环境变量
load_dotenv()

# ================= Pydantic Schema =================

class Finding(BaseModel):
    id: str
    title: str
    severity: str  # P0 / P1 / P2
    rationale: str

class Advice(BaseModel):
    for_pm: str
    for_eng: str

class PanelItem(BaseModel):
    role: str
    findings: list[Finding]
    advice: Advice
    score: int = Field(ge=0, le=100)

class ExecSummary(BaseModel):
    total_score: int = Field(ge=0, le=100)
    blockers: list[str]
    decision: str
    items: list[PanelItem]
    revision_blocks: list[str] = Field(default_factory=list, description="可复制到 PRD 的修订段落")

# 单角色评审输出（LLM 返回后解析为 PanelItem）
class RoleReviewOutput(BaseModel):
    findings: list[Finding]
    advice: Advice
    score: int = Field(ge=0, le=100)

# ================= 配置区 =================
st.set_page_config(page_title="AI PRD 卫士 Pro", page_icon="🛡️", layout="wide")

ROLES = {
    "CTO": {
        "name": "💀 首席技术官 (CTO)",
        "focus": "技术可行性、系统扩展性、数据一致性(CAP/BASE)、接口幂等性、竞态条件、安全合规(OWASP)、技术债务。",
        "style": "极度理性、毒舌。不仅指出问题，还要质问'为什么没考虑到？'。若发现死锁或脏写风险，直接标记为'系统级灾难'。"
    },
    "UX": {
        "name": "🎨 体验设计总监 (UXD)",
        "focus": "尼尔森可用性原则、认知负荷、交互一致性、异常容错(Error Recovery)、A11y无障碍、微交互反馈。",
        "style": "挑剔的完美主义者。如果文案歧义或操作无反馈，直接指出这是'反人类设计'。"
    },
    "QA": {
        "name": "🔍 资深测试专家 (QA)",
        "focus": "边界值分析、异常输入(Null/Max)、依赖服务熔断、状态机死循环、权限越权、历史数据兼容性。",
        "style": "悲观主义者。假设一切都会出错。不仅仅是找Bug，是找'逻辑漏洞'。喜欢问'如果网络断了重连会怎样？'。"
    }
}

# ================= 逻辑函数 =================

def get_client(api_key):
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

ROLE_OUTPUT_JSON_SCHEMA = """
你必须只输出一个合法 JSON 对象，不要包含 markdown 代码块或其它文字。格式如下：
{
  "findings": [
    { "id": "f1", "title": "问题点专业描述", "severity": "P0或P1或P2", "rationale": "风险与原因说明" }
  ],
  "advice": { "for_pm": "PM 可复制到 PRD 的修订描述", "for_eng": "给开发的技术建议" },
  "score": 85
}
若无问题：findings 为空数组 []，advice 可为空字符串，score 为 0-100。
"""

def agent_review(client, prd_content, role_key):
    role = ROLES[role_key]
    system = f"""你是公司的 {role['name']}。性格：{role['style']}
任务：审查 PRD，只关注【{role['focus']}】。
{ROLE_OUTPUT_JSON_SCHEMA}"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"请审查以下 PRD，仅输出上述格式的 JSON：\n\n{prd_content}"}
            ],
            temperature=0.4,
            response_format={"type": "json_object"}
        )
        raw = response.choices[0].message.content
        # 去除可能的 markdown 代码块
        if "```" in raw:
            raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
        data = json.loads(raw)
        out = RoleReviewOutput(**data)
        return PanelItem(role=role_key, findings=out.findings, advice=out.advice, score=out.score)
    except Exception as e:
        return PanelItem(
            role=role_key,
            findings=[Finding(id="err", title="解析失败", severity="P0", rationale=str(e))],
            advice=Advice(for_pm="", for_eng=""),
            score=0
        )

EXEC_SUMMARY_JSON_SCHEMA = """
你必须只输出一个合法 JSON 对象，不要包含 markdown 代码块或其它文字。格式如下：
{
  "total_score": 78,
  "blockers": ["阻断项1描述", "阻断项2描述"],
  "decision": "执行摘要：一段话总结是否通过、主要结论与决策。",
  "items": [
    { "role": "CTO", "findings": [...], "advice": { "for_pm": "", "for_eng": "" }, "score": 80 },
    ...
  ],
  "revision_blocks": ["可直接复制到 PRD 的修订段落1", "修订段落2"]
}
blockers：上线前必须解决的问题列表。revision_blocks：从各角色 advice.for_pm 提炼的可复制修订块，去重合并。
"""

def generate_final_report(client, prd_content, panel_items: list[PanelItem]):
    reviews_text = "\n".join([
        f"=== {ROLES[p.role]['name']} === score={p.score}\nfindings={[f.model_dump() for f in p.findings]}\nadvice={p.advice.model_dump()}"
        for p in panel_items
    ])
    system = f"""你是拥有20年经验的产品VP。汇总各方评审意见，输出最终的 PRD 评审决议（去重、合并、给出管理决策）。
{EXEC_SUMMARY_JSON_SCHEMA}"""
    user_content = f"原始 PRD:\n{prd_content}\n\n评审结构化记录:\n{reviews_text}"

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        raw = response.choices[0].message.content
        if "```" in raw:
            raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
        data = json.loads(raw)
        return ExecSummary(**data)
    except Exception as e:
        return ExecSummary(
            total_score=0,
            blockers=[f"VP 汇总解析失败: {e}"],
            decision="无法生成执行摘要。",
            items=[PanelItem(role=p.role, findings=p.findings, advice=p.advice, score=p.score) for p in panel_items],
            revision_blocks=[]
        )

def format_full_report_md(summary: ExecSummary, panel_items: list[PanelItem]) -> str:
    md = f"# 执行摘要\n\n{summary.decision}\n\n"
    md += f"**总分**: {summary.total_score}/100\n\n"
    md += "## 阻断项 (Must Fix)\n\n"
    for b in summary.blockers:
        md += f"- {b}\n"
    md += "\n## 可复制修订块\n\n"
    for i, block in enumerate(summary.revision_blocks, 1):
        md += f"{i}. {block}\n\n"
    md += "\n---\n\n# 评审团详细记录\n\n"
    for p in panel_items:
        md += f"## {ROLES[p.role]['name']} (评分: {p.score})\n\n"
        for f in p.findings:
            md += f"- **{f.title}** [{f.severity}] {f.rationale}\n"
        md += f"\n- PM 修订建议: {p.advice.for_pm}\n"
        md += f"- 技术建议: {p.advice.for_eng}\n\n"
    return md

# ================= Session State =================
if "panel_items" not in st.session_state:
    st.session_state.panel_items = []
if "exec_summary" not in st.session_state:
    st.session_state.exec_summary = None  # ExecSummary | None

# ================= 界面 UI =================
st.title("🛡️ AI PRD Guardian Pro")
st.caption("🚀 Multi-Agent 需求评审系统 | 模拟真实团队博弈")

with st.sidebar:
    st.header("⚙️ 评审配置")
    api_key = st.text_input("DeepSeek API Key", type="password")
    st.markdown("---")
    st.subheader("👥 选择评审团")
    selected_roles = []
    if st.checkbox("CTO", value=True): selected_roles.append("CTO")
    if st.checkbox("UXD", value=True): selected_roles.append("UX")
    if st.checkbox("QA", value=True): selected_roles.append("QA")

uploaded_file = st.file_uploader("📂 上传 PRD (支持 md/txt)", type=["md", "txt"])

if uploaded_file and api_key:
    prd_content = uploaded_file.read().decode("utf-8")
    
    if st.button("🚀 开始评审 (Start Review)", type="primary"):
        if not selected_roles:
            st.warning("请至少选择一位评审员！")
        else:
            client = get_client(api_key)
            st.session_state.panel_items = []
            st.session_state.exec_summary = None

            progress_bar = st.progress(0)
            status_text = st.empty()
            step = 1.0 / (len(selected_roles) + 1)
            current_progress = 0.0

            for role in selected_roles:
                status_text.markdown(f"**{ROLES[role]['name']}** 正在阅读文档...")
                panel_item = agent_review(client, prd_content, role)
                st.session_state.panel_items.append(panel_item)
                current_progress += step
                progress_bar.progress(min(1.0, current_progress))

            status_text.markdown("✍️ **VP** 正在撰写最终决议...")
            summary = generate_final_report(client, prd_content, st.session_state.panel_items)
            st.session_state.exec_summary = summary
            progress_bar.progress(1.0)
            status_text.success("✅ 评审完成！")

# ================= 结果展示区 =================
summary = st.session_state.exec_summary
panel_items = st.session_state.panel_items

if summary is not None and panel_items:
    st.divider()
    full_report_md = format_full_report_md(summary, panel_items)
    st.download_button(
        label="📥 下载完整评审报告 (Markdown)",
        data=full_report_md,
        file_name="prd_review_report.md",
        mime="text/markdown"
    )

    # 执行摘要 + 评分
    st.subheader("📊 执行摘要")
    st.markdown(summary.decision)
    st.metric("总分", f"{summary.total_score}/100")

    # 阻断项
    st.subheader("🛑 阻断项 (Must Fix)")
    if summary.blockers:
        for b in summary.blockers:
            st.markdown(f"- {b}")
    else:
        st.success("无阻断项")

    # 可复制修订块
    st.subheader("📝 可复制修订块")
    if summary.revision_blocks:
        for i, block in enumerate(summary.revision_blocks, 1):
            st.text_area(f"修订块 {i}（可复制）", value=block, height=80, key=f"rev_{i}")
    else:
        st.caption("无提炼的修订块")

    tab1, tab2 = st.tabs(["📊 评分卡与决议", "💬 各角色详细记录"])
    with tab1:
        st.markdown("**各角色评分**")
        cols = st.columns(min(len(summary.items), 3))
        for i, it in enumerate(summary.items):
            with cols[i % len(cols)]:
                st.metric(ROLES.get(it.role, {}).get("name", it.role), f"{it.score}/100")
        st.markdown("**决议**")
        st.markdown(summary.decision)
    with tab2:
        for p in panel_items:
            with st.expander(f"{ROLES[p.role]['name']} — 评分: {p.score}", expanded=True):
                for f in p.findings:
                    st.markdown(f"**{f.title}** `[{f.severity}]` {f.rationale}")
                if p.advice.for_pm:
                    st.markdown(f"**PM 修订**: {p.advice.for_pm}")
                if p.advice.for_eng:
                    st.markdown(f"**技术建议**: {p.advice.for_eng}")

elif not api_key:
    st.info("👈 请在左侧输入 API Key 以开始。")
