import streamlit as st
import os
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

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

def agent_review(client, prd_content, role_key):
    role = ROLES[role_key]
    prompt = f"""
    你现在是公司的 {role['name']}。你的性格是：{role['style']}
    
    任务：审查 PRD，只关注：【{role['focus']}】。
    
    【输出要求】
    对于发现的每一个漏洞，按此 Markdown 格式输出：
    1. **🛑 问题点**: [专业术语描述，如'缺乏幂等性']
       - **😟 风险**: [通俗解释后果，如'用户点一次可能被扣两次钱']
       - **💡 建议 (技术侧)**: [给开发的建议，如'使用Redis锁']
       - **📝 建议 (PM侧)**: [请直接给出一段可以让 PM 复制粘贴补充到 PRD 里的描述。例如：'后端需增加防重校验，同一订单号仅允许扣款一次。']
       
    无问题回复 "LGTM"。
    """
    # ... (后续代码不变)

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"请审查：\n{prd_content}"}
            ],
            temperature=0.4
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ {role['name']} 离线: {e}"

def generate_final_report(client, prd_content, reviews):
    reviews_text = "\n".join([f"=== {ROLES[r]['name']} 意见 ===\n{c}" for r, c in reviews.items()])
    
    system_prompt = """
    你是拥有20年经验的产品VP。你需要汇总各方（CTO/UX/QA）的评审意见，输出一份最终的【PRD 评审决议】。
    
    要求：
    1. **去重与清洗**：合并相似观点。
    2. **管理决策**：对于冲突意见，给出权衡后的决策。
    3. **输出结构**：
       - 📊 **评分卡**：打分 (0-100)，评级 (P0-P2)。
       - 🛑 **阻断性问题 (Must Fix)**：上线前必须解决的。
       - ⚠️ **优化建议 (Should Fix)**：建议迭代优化的。
       - ✅ **通过项**：做得好的地方。
    """
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"原始 PRD:\n{prd_content}\n\n评审记录:\n{reviews_text}"}
        ],
        temperature=0.2
    )
    return response.choices[0].message.content

def format_full_report(final_report, reviews):
    # 拼接最终报告
    md_content = final_report + "\n\n---\n\n# 💬 评审团详细记录 (Detailed Logs)\n\n"
    for role_key, content in reviews.items():
        role_name = ROLES[role_key]['name']
        md_content += f"## {role_name}\n\n{content}\n\n"
    return md_content

# ================= Session State =================
if 'reviews' not in st.session_state:
    st.session_state.reviews = {}
if 'final_report' not in st.session_state:
    st.session_state.final_report = ""

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
            st.session_state.reviews = {}
            
            # 1. 并行评审
            progress_bar = st.progress(0)
            status_text = st.empty()
            step = 1.0 / (len(selected_roles) + 1)
            current_progress = 0.0
            
            for role in selected_roles:
                status_text.markdown(f"**{ROLES[role]['name']}** 正在阅读文档...")
                review = agent_review(client, prd_content, role)
                st.session_state.reviews[role] = review
                current_progress += step
                progress_bar.progress(current_progress)
            
            # 2. 汇总
            status_text.markdown("✍️ **VP** 正在撰写最终决议...")
            final_report = generate_final_report(client, prd_content, st.session_state.reviews)
            st.session_state.final_report = final_report
            progress_bar.progress(100)
            status_text.success("✅ 评审完成！")

# ================= 结果展示区 =================
if st.session_state.final_report:
    st.divider()
    
    full_report_md = format_full_report(st.session_state.final_report, st.session_state.reviews)
    
    st.download_button(
        label="📥 下载完整评审报告 (Markdown)",
        data=full_report_md,
        file_name="prd_review_report.md",
        mime="text/markdown"
    )

    tab1, tab2 = st.tabs(["📊 最终决议", "💬 详细记录"])
    with tab1: st.markdown(st.session_state.final_report)
    with tab2:
        for role, review in st.session_state.reviews.items():
            with st.expander(f"{ROLES[role]['name']} 的详细意见", expanded=True):
                st.markdown(review)

elif not api_key:
    st.info("👈 请在左侧输入 API Key 以开始。")
