import streamlit as st
import re
import os
import json
from datetime import datetime
from docx import Document
import io
import urllib.request

RULE_VERSION = "2026-02-04"
TODAY = datetime.now().strftime("%Y%m%d")

REVIEW_RULES = {
    "required_keywords": ["适度水解", "防敏", "能恩全护"],
    "forbidden_words": {
        "禁止词": ["敏宝", "奶瓶", "奶嘴", "新生儿", "过敏", "疾病"],
        "禁疗效": ["预防", "生长", "发育", "免疫"],
        "禁绝对化": ["最好", "最佳", "TOP1", "No.1"]
    },
    "allowed_exceptions": ["第一口奶粉", "第一口配方粉"],
    "selling_points": [
        "多项科学实证的雀巢尖峰水解技术",
        "防敏领域权威德国GINI研究认证",
        "能长效防敏20年",
        "相比于牛奶蛋白致敏性降低1000倍",
        "全球创新的超倍自护科技",
        "6种HMO加上明星双菌B.Infantis和Bb-12",
        "协同作用释放高倍的原生保护力",
        "短短28天就能调理好娃的肚肚菌菌环境",
        "保护力能持续15个月",
        "25种维生素和矿物质",
        "全乳糖的配方口味清淡"
    ],
    "required_tags": ["#能恩全护", "#能恩全护水奶", "#适度水解", "#适度水解奶粉", "#适度水解奶粉推荐", "#防敏奶粉", "#第一口奶粉", "#雀巢适度水解"],
    "max_words": 900,
    "min_tags": 10
}

SUGGESTIONS = {"敏宝": "敏感体质宝宝", "新生儿": "初生宝宝", "过敏": "敏敏", "预防": "远离", "生长": "成长", "发育": "成长", "免疫": "保护力"}

def read_docx(file):
    doc = Document(io.BytesIO(file.read()))
    text = []
    for para in doc.paragraphs:
        if para.text.strip():
            text.append(para.text)
    return "\n".join(text)

def parse_content(content):
    tags = re.findall(r'#[\w\u4e00-\u9fff]+', content)
    text = re.sub(r'#[\w\u4e00-\u9fff]+', '', content)
    word_count = len(re.findall(r'[\u4e00-\u9fff]', text))
    return {"text": content, "tags": tags, "word_count": word_count}

def run_review(content):
    data = parse_content(content)
    issues = []

    for kw in REVIEW_RULES["required_keywords"]:
        if kw not in data["text"]:
            issues.append({"type": "keyword", "desc": f"缺少关键词: {kw}", "suggestion": f"请加入「{kw}」"})

    exceptions = REVIEW_RULES["allowed_exceptions"]
    for cat, words in REVIEW_RULES["forbidden_words"].items():
        for w in words:
            if w in data["text"]:
                idx = data["text"].find(w)
                ctx = data["text"][max(0,idx-10):idx+len(w)+10]
                if not any(e in ctx for e in exceptions):
                    sug = SUGGESTIONS.get(w, "删除")
                    issues.append({"type": "forbidden", "desc": f"禁词「{w}」", "context": ctx, "suggestion": f"改为「{sug}」"})

    for sp in REVIEW_RULES["selling_points"]:
        if sp not in data["text"]:
            issues.append({"type": "selling", "desc": f"缺少卖点", "suggestion": f"请加入: {sp}"})

    if data["word_count"] > REVIEW_RULES["max_words"]:
        issues.append({"type": "structure", "desc": f"字数超限: {data['word_count']}/{REVIEW_RULES['max_words']}", "suggestion": "请精简"})

    if len(data["tags"]) < REVIEW_RULES["min_tags"]:
        issues.append({"type": "structure", "desc": f"标签不足: {len(data['tags'])}/{REVIEW_RULES['min_tags']}", "suggestion": "请补充"})

    for t in REVIEW_RULES["required_tags"]:
        if t not in data["tags"]:
            issues.append({"type": "tag", "desc": f"缺少标签: {t}", "suggestion": f"请加入 {t}"})

    return issues, data

def call_claude_api(prompt):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    url = "https://api.anthropic.com/v1/messages"
    headers = {"Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"}
    data = {"model": "claude-sonnet-4-20250514", "max_tokens": 4000, "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result["content"][0]["text"]
    except Exception as e:
        return f"Error: {str(e)}"

def analyze_client_feedback(original, client_modified):
    prompt = f"""你是小红书KOL稿件审核专家。对比分析客户修改。

原稿件:
{original}

客户修改后:
{client_modified}

审核规则: 禁词包括敏宝、奶瓶、奶嘴、新生儿、过敏、疾病、预防、生长、发育、免疫、最好、最佳。例外:"第一口奶粉"中的"第一"不算禁词。

请分析客户修改了哪些内容,每条是否符合规则,不符合的给建议。

格式:
===修改分析===
修改1: [描述]
状态: 符合/不符合
建议: [建议]

===总结===
符合: X条
需调整: X条
"""
    return call_claude_api(prompt)

def create_annotated_docx(content, issues, selected_issues, kol_name, version, step, extra_comments=None):
    doc = Document()
    if step == 2:
        title = f"{kol_name}_{TODAY}_KOL-赞意_第{version}版"
        subtitle = "赞意审核批注版"
    else:
        title = f"{kol_name}_{TODAY}_KOL-赞意-客户_第{version}版"
        subtitle = "客户反馈处理版"

    doc.add_heading(title, 0)
    doc.add_paragraph(f"审核时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    doc.add_paragraph(f"文档类型: {subtitle}")
    doc.add_paragraph("---")

    if selected_issues:
        doc.add_heading("审核意见（已采纳）", level=1)
        for i, idx in enumerate(selected_issues):
            if idx < len(issues):
                issue = issues[idx]
                p = doc.add_paragraph()
                p.add_run(f"{i+1}. {issue['desc']}").bold = True
                p.add_run(f"\n   建议: {issue['suggestion']}")
        doc.add_paragraph("---")

    if extra_comments:
        doc.add_heading("补充意见", level=1)
        doc.add_paragraph(extra_comments)
        doc.add_paragraph("---")

    doc.add_heading("稿件内容", level=1)
    for line in content.split('\n'):
        if line.strip():
            doc.add_paragraph(line)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer, title

st.set_page_config(page_title="赞意AI审稿系统", page_icon="🤖", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1rem !important; padding-bottom: 1rem !important;}
[data-testid="column"]:first-child {
    background-color: #fff0f3;
    border-radius: 15px;
    padding: 20px;
    border: 2px solid #ff6b6b;
}
[data-testid="column"]:last-child {
    background-color: #f0fff4;
    border-radius: 15px;
    padding: 20px;
    border: 2px solid #38a169;
}
.step-badge-pink {
    background-color: #ff6b6b;
    color: white;
    padding: 8px 16px;
    border-radius: 20px;
    font-weight: bold;
    font-size: 14px;
}
.step-badge-green {
    background-color: #38a169;
    color: white;
    padding: 8px 16px;
    border-radius: 20px;
    font-weight: bold;
    font-size: 14px;
}
.file-output {
    background-color: #f7fafc;
    border: 1px dashed #cbd5e0;
    padding: 10px;
    border-radius: 8px;
    font-family: monospace;
    margin: 10px 0;
}
/* 文件上传中文化 */
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] p {
    font-size: 0 !important;
}
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] p::after {
    content: "将文件拖到此处上传";
    font-size: 14px !important;
}
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] button {
    font-size: 0 !important;
    position: relative;
}
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] button::after {
    content: "选择文件";
    font-size: 14px !important;
    position: absolute;
}
/* 绿色按钮样式 */
.green-btn button {
    background-color: #38a169 !important;
    color: white !important;
    border: none !important;
}
.green-btn button:hover {
    background-color: #2f855a !important;
}
/* 在线预览区域 */
.preview-box {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 20px;
    margin: 15px 0;
    max-height: 500px;
    overflow-y: auto;
}
.preview-title {
    font-size: 16px;
    font-weight: bold;
    color: #2d3748;
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 2px solid #edf2f7;
}
.issue-card {
    background-color: #fff5f5;
    border-left: 4px solid #fc8181;
    padding: 10px 15px;
    margin: 8px 0;
    border-radius: 0 8px 8px 0;
}
.issue-card.accepted {
    background-color: #f0fff4;
    border-left-color: #68d391;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 15px 25px; margin-bottom: 15px;">
    <h2 style="color: white; margin: 0;">🤖 赞意AI · 小红书KOL审稿系统</h2>
    <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0 0; font-size: 15px;">兔子小姐，你好呀！我是能恩全护的AI机器人，为你服务~</p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    kol_name = st.text_input("KOL名称", placeholder="例如: 团妈爱测评")
with col2:
    version_num = st.selectbox("当前版本", [1, 2, 3, 4, 5])

st.caption(f"当前日期: {TODAY}")

if 'kol_issues' not in st.session_state:
    st.session_state.kol_issues = []
if 'kol_content' not in st.session_state:
    st.session_state.kol_content = ""
if 'client_analysis' not in st.session_state:
    st.session_state.client_analysis = ""

col_left, col_right = st.columns(2)

with col_left:
    st.markdown('<span class="step-badge-pink">Step 1: KOL稿件 - 赞意审核 - 完毕给客户</span>', unsafe_allow_html=True)
    st.markdown("#### 📄 上传KOL稿件")

    kol_file = st.file_uploader("上传 .docx 文件（可拖拽上传）", type=["docx"], key="kol_file")
    kol_text = st.text_area("或粘贴内容", height=180, placeholder="粘贴KOL稿件...", key="kol_text")

    kol_content = ""
    if kol_file:
        kol_file.seek(0)
        kol_content = read_docx(kol_file)
        st.success(f"已读取: {kol_file.name}")
    elif kol_text:
        kol_content = kol_text

    if st.button("开始审稿", type="primary", key="btn_review", use_container_width=True):
        if not kol_name:
            st.error("请填写KOL名称")
        elif not kol_content:
            st.error("请上传或粘贴稿件")
        else:
            issues, data = run_review(kol_content)
            st.session_state.kol_issues = issues
            st.session_state.kol_content = kol_content
            st.success(f"审核完成! 发现 {len(issues)} 个问题")

    if st.session_state.kol_issues and st.session_state.kol_content:
        # --- 在线预览区域 ---
        st.markdown("---")
        st.markdown("#### 📋 在线审核预览")

        # 显示稿件内容预览
        with st.expander("📄 查看稿件原文", expanded=False):
            st.text_area("稿件内容", st.session_state.kol_content, height=200, disabled=True, key="preview_content")

        # 审核意见 - 逐条勾选
        st.markdown("#### ✏️ 审核意见（勾选采纳的批注）")

        issue_types = {"keyword": "关键词", "forbidden": "禁词", "selling": "卖点", "structure": "结构", "tag": "标签"}
        selected = []

        # 按类型分组显示
        grouped = {}
        for i, issue in enumerate(st.session_state.kol_issues):
            t = issue["type"]
            if t not in grouped:
                grouped[t] = []
            grouped[t].append((i, issue))

        for issue_type, items in grouped.items():
            type_label = issue_types.get(issue_type, issue_type)
            st.markdown(f"**{type_label}类问题** ({len(items)}条)")
            for i, issue in items:
                col_check, col_text = st.columns([0.05, 0.95])
                with col_check:
                    checked = st.checkbox("", key=f"iss_{i}", value=True, label_visibility="collapsed")
                with col_text:
                    if checked:
                        selected.append(i)
                        st.markdown(f'<div class="issue-card accepted">✅ {issue["desc"]}<br><small>建议: {issue["suggestion"]}</small></div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="issue-card">❌ {issue["desc"]}<br><small>建议: {issue["suggestion"]}</small></div>', unsafe_allow_html=True)

        # 补充意见输入
        st.markdown("---")
        st.markdown("#### 💬 补充意见（可选）")
        extra_comments = st.text_area("在此输入额外的审核意见或备注", height=100, placeholder="例如: 整体语气偏硬，建议更口语化一些...", key="extra_comments")

        # 统计
        st.markdown("---")
        total = len(st.session_state.kol_issues)
        accepted = len(selected)
        st.markdown(f"**审核统计**: 共 {total} 条意见，已采纳 {accepted} 条，未采纳 {total - accepted} 条")

        # 生成文档
        if kol_name:
            output_name = f"{kol_name}_{TODAY}_KOL-赞意_第{version_num}版"
            st.markdown(f'<div class="file-output">📁 {output_name}.docx</div>', unsafe_allow_html=True)

            if st.button("确认并生成批注文档", key="btn_gen_kol", use_container_width=True):
                buffer, title = create_annotated_docx(
                    st.session_state.kol_content,
                    st.session_state.kol_issues,
                    selected, kol_name, version_num, 2,
                    extra_comments if extra_comments else None
                )
                st.download_button("下载文档 - 可发给客户", buffer, f"{output_name}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="dl_kol")

with col_right:
    st.markdown('<span class="step-badge-green">Step 2: 客户反馈 - 赞意处理 - 完毕给KOL</span>', unsafe_allow_html=True)
    st.markdown("#### 💬 上传客户反馈")

    client_file = st.file_uploader("上传 .docx 文件（可拖拽上传）", type=["docx"], key="client_file")
    client_text = st.text_area("或粘贴内容", height=180, placeholder="粘贴客户反馈...", key="client_text")

    client_content = ""
    if client_file:
        client_file.seek(0)
        client_content = read_docx(client_file)
        st.success(f"已读取: {client_file.name}")
    elif client_text:
        client_content = client_text

    # 绿色按钮
    st.markdown('<div class="green-btn">', unsafe_allow_html=True)
    analyze_clicked = st.button("分析反馈", key="btn_analyze", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if analyze_clicked:
        if not kol_name:
            st.error("请填写KOL名称")
        elif not client_content:
            st.error("请上传或粘贴客户反馈")
        elif not st.session_state.kol_content:
            st.error("请先在左侧上传KOL原稿")
        else:
            with st.spinner("AI分析中..."):
                analysis = analyze_client_feedback(st.session_state.kol_content, client_content)
                st.session_state.client_analysis = analysis

    if st.session_state.client_analysis:
        st.markdown("---")
        st.markdown("#### 📋 修改分析预览")

        if "===修改分析===" in st.session_state.client_analysis:
            parts = st.session_state.client_analysis.split("===总结===")
            analysis_part = parts[0].replace("===修改分析===", "").strip()

            lines = analysis_part.split("\n")
            changes = []
            current = {}
            for line in lines:
                line = line.strip()
                if line.startswith("修改"):
                    if current:
                        changes.append(current)
                    current = {"desc": line, "status": "", "suggestion": ""}
                elif line.startswith("状态:"):
                    current["status"] = line.replace("状态:", "").strip()
                elif line.startswith("建议:"):
                    current["suggestion"] = line.replace("建议:", "").strip()
            if current:
                changes.append(current)

            for i, c in enumerate(changes):
                is_ok = "符合" in c.get("status", "")
                col_check, col_text = st.columns([0.05, 0.95])
                with col_check:
                    st.checkbox("", key=f"cc_{i}", value=is_ok, label_visibility="collapsed")
                with col_text:
                    status_icon = "✅" if is_ok else "⚠️"
                    card_class = "accepted" if is_ok else ""
                    desc = c.get('desc', '')
                    sug = c.get('suggestion', '')
                    st.markdown(f'<div class="issue-card {card_class}">{status_icon} {desc}<br><small>{sug}</small></div>', unsafe_allow_html=True)

            if len(parts) > 1:
                st.info(parts[1].strip())
        else:
            st.write(st.session_state.client_analysis)

        # 补充意见
        st.markdown("---")
        st.markdown("#### 💬 补充意见给KOL（可选）")
        client_extra = st.text_area("在此输入额外的反馈意见", height=100, placeholder="例如: 客户希望第3张图片突出产品包装...", key="client_extra")

        if kol_name and client_content:
            output_name = f"{kol_name}_{TODAY}_KOL-赞意-客户_第{version_num}版"
            st.markdown(f'<div class="file-output">📁 {output_name}.docx</div>', unsafe_allow_html=True)

            if st.button("确认并生成给KOL的文档", key="btn_gen_client", use_container_width=True):
                doc = Document()
                doc.add_heading(output_name, 0)
                doc.add_paragraph(f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                doc.add_paragraph("---")
                doc.add_heading("客户修改分析", level=1)
                doc.add_paragraph(st.session_state.client_analysis)
                if client_extra:
                    doc.add_paragraph("---")
                    doc.add_heading("补充意见", level=1)
                    doc.add_paragraph(client_extra)
                doc.add_paragraph("---")
                doc.add_heading("修改后内容", level=1)
                for line in client_content.split('\n'):
                    if line.strip():
                        doc.add_paragraph(line)
                buffer = io.BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                st.download_button("下载文档 - 可发给KOL", buffer, f"{output_name}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="dl_client")

st.markdown("---")
st.caption("🤖 赞意AI审稿系统 v3.1")
