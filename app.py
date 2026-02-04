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

def create_annotated_docx(content, issues, selected_issues, kol_name, version, step, extra_comments=None, selling_inputs=None):
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
                # 如果是卖点类且有自定义写法
                sp_key = f"sp_{idx}"
                if selling_inputs and sp_key in selling_inputs and selling_inputs[sp_key]:
                    p.add_run(f"\n   推荐表达: {selling_inputs[sp_key]}")
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

# ========== 页面配置 ==========
st.set_page_config(page_title="赞意AI审稿系统", page_icon="🤖", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1rem !important; padding-bottom: 1rem !important;}
/* 左栏：淡酒红色 */
[data-testid="column"]:first-child {
    background-color: #f5eaed;
    border-radius: 15px;
    padding: 20px;
    border: 2px solid #8b4557;
}
/* 右栏：淡海军蓝 */
[data-testid="column"]:nth-child(2) {
    background-color: #e8ecf4;
    border-radius: 15px;
    padding: 20px;
    border: 2px solid #2c3e6b;
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
/* 海军蓝按钮样式 */
.navy-btn button {
    background-color: #2c3e6b !important;
    color: white !important;
    border: none !important;
}
.navy-btn button:hover {
    background-color: #1e2d52 !important;
}
/* 审核预览区 */
.original-text-box {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 15px;
    height: 400px;
    overflow-y: auto;
    font-size: 14px;
    line-height: 1.8;
}
.issue-card {
    background-color: #fff5f5;
    border-left: 4px solid #fc8181;
    padding: 10px 15px;
    margin: 6px 0;
    border-radius: 0 8px 8px 0;
    font-size: 13px;
}
.issue-card.accepted {
    background-color: #f0fff4;
    border-left-color: #68d391;
}
</style>
""", unsafe_allow_html=True)

# ========== 标题 ==========
st.markdown("""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 15px 25px; margin-bottom: 15px;">
    <h2 style="color: white; margin: 0;">🤖 赞意AI · 小红书KOL审稿系统</h2>
    <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0 0; font-size: 15px;">兔子小姐，你好呀！我是能恩全护的AI机器人，为你服务~</p>
</div>
""", unsafe_allow_html=True)

# ========== 基本信息 ==========
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    kol_name = st.text_input("KOL名称", placeholder="例如: 团妈爱测评")
with col2:
    version_num = st.selectbox("当前版本", [1, 2, 3, 4, 5])
with col3:
    st.caption(f"当前日期: {TODAY}")

# ========== Session State 初始化 ==========
if 'kol_issues' not in st.session_state:
    st.session_state.kol_issues = []
if 'kol_content' not in st.session_state:
    st.session_state.kol_content = ""
if 'kol_data' not in st.session_state:
    st.session_state.kol_data = None
if 'client_analysis' not in st.session_state:
    st.session_state.client_analysis = ""
if 'client_content_saved' not in st.session_state:
    st.session_state.client_content_saved = ""
if 'selling_suggestions' not in st.session_state:
    st.session_state.selling_suggestions = {}
if 'selling_inputs' not in st.session_state:
    st.session_state.selling_inputs = {}

# ========== 上传区：左右两栏 ==========
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### 📄 上传KOL稿件")
    kol_file = st.file_uploader("上传 .docx 文件（可拖拽上传）", type=["docx"], key="kol_file")
    kol_text = st.text_area("或粘贴内容", height=120, placeholder="粘贴KOL稿件...", key="kol_text")

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
            st.session_state.kol_data = data
            st.success(f"审核完成! 发现 {len(issues)} 个问题")

with col_right:
    st.markdown("#### 💬 上传客户反馈")
    client_file = st.file_uploader("上传 .docx 文件（可拖拽上传）", type=["docx"], key="client_file")
    client_text = st.text_area("或粘贴内容", height=120, placeholder="粘贴客户反馈...", key="client_text")

    client_content = ""
    if client_file:
        client_file.seek(0)
        client_content = read_docx(client_file)
        st.success(f"已读取: {client_file.name}")
    elif client_text:
        client_content = client_text

    st.markdown('<div class="navy-btn">', unsafe_allow_html=True)
    analyze_clicked = st.button("分析反馈", key="btn_analyze", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if analyze_clicked:
        if not kol_name:
            st.error("请填写KOL名称")
        elif not client_content:
            st.error("请上传或粘贴客户反馈")
        elif not st.session_state.kol_content:
            st.error("请先上传KOL原稿并审核")
        else:
            st.session_state.client_content_saved = client_content
            with st.spinner("AI分析中..."):
                analysis = analyze_client_feedback(st.session_state.kol_content, client_content)
                st.session_state.client_analysis = analysis

# ========== 审核预览区（全宽，横跨两栏） ==========
if st.session_state.kol_issues and st.session_state.kol_content:
    st.markdown("---")
    st.markdown("### 📋 在线审核预览")

    # 统计栏
    total = len(st.session_state.kol_issues)
    data = st.session_state.kol_data
    word_count = data["word_count"] if data else 0
    tag_count = len(data["tags"]) if data else 0

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("审核问题", f"{total} 条")
    s2.metric("稿件字数", f"{word_count}")
    s3.metric("标签数量", f"{tag_count}")
    s4.metric("字数上限", f"{REVIEW_RULES['max_words']}")

    # 左：原文 | 右：审核意见
    preview_left, preview_right = st.columns([1, 1])

    with preview_left:
        st.markdown("#### 📄 稿件原文")
        # 把原文中的禁词高亮显示
        highlighted = st.session_state.kol_content
        for cat, words in REVIEW_RULES["forbidden_words"].items():
            for w in words:
                if w in highlighted:
                    highlighted = highlighted.replace(w, f'<mark style="background-color:#fed7d7;padding:2px 4px;border-radius:3px;">{w}</mark>')
        # 把必含关键词高亮
        for kw in REVIEW_RULES["required_keywords"]:
            if kw in highlighted:
                highlighted = highlighted.replace(kw, f'<mark style="background-color:#c6f6d5;padding:2px 4px;border-radius:3px;">{kw}</mark>')

        html_content = highlighted.replace('\n', '<br>')
        st.markdown(f'<div class="original-text-box">{html_content}</div>', unsafe_allow_html=True)

    with preview_right:
        st.markdown("#### ✏️ 审核意见（勾选采纳）")

        issue_types = {"keyword": "🔑 关键词", "forbidden": "🚫 禁词", "selling": "💡 卖点", "structure": "📐 结构", "tag": "🏷️ 标签"}
        selected = []

        # 按类型分组
        grouped = {}
        for i, issue in enumerate(st.session_state.kol_issues):
            t = issue["type"]
            if t not in grouped:
                grouped[t] = []
            grouped[t].append((i, issue))

        for issue_type, items in grouped.items():
            type_label = issue_types.get(issue_type, issue_type)
            is_selling = (issue_type == "selling")
            with st.expander(f"{type_label} ({len(items)}条)", expanded=(issue_type in ["forbidden", "keyword", "selling"])):
                for i, issue in items:
                    checked = st.checkbox(issue["desc"], key=f"iss_{i}", value=True)
                    if checked:
                        selected.append(i)
                    st.caption(f"建议: {issue['suggestion']}")

                    # 卖点类：提供在线输入 + AI建议
                    if is_selling:
                        sp_key = f"sp_{i}"

                        btn_col, input_col = st.columns([1, 2])
                        with btn_col:
                            ai_clicked = st.button("🤖 AI帮我写", key=f"btn_ai_{i}")
                        with input_col:
                            current_val = st.session_state.selling_inputs.get(sp_key, "")
                            user_input = st.text_input(
                                "自定义写法",
                                value=current_val,
                                placeholder="在此输入你的表达方式...",
                                key=f"input_{i}",
                                label_visibility="collapsed",
                            )
                            if user_input:
                                st.session_state.selling_inputs[sp_key] = user_input

                        # AI生成建议
                        if ai_clicked:
                            selling_point = issue["suggestion"].replace("请加入: ", "")
                            prompt = f"""你是小红书母婴KOL文案专家。KOL需要在稿件中加入以下产品卖点：
「{selling_point}」

请生成3个不同风格的表达方式，要求：
1. 口语化、接地气、像妈妈在分享
2. 不能用禁词（敏宝、过敏、预防、新生儿、免疫、生长、发育）
3. 每个控制在30字以内

只输出3个表达，每行一个，用序号开头：
1. xxx
2. xxx
3. xxx"""
                            result = call_claude_api(prompt)
                            if result and not result.startswith("Error"):
                                st.session_state.selling_suggestions[sp_key] = result
                                st.rerun()
                            elif result and result.startswith("Error"):
                                st.error(f"AI调用失败: {result}")
                            else:
                                st.error("API Key未设置，请在Render环境变量中配置ANTHROPIC_API_KEY")

                        # 显示AI建议（如果有）
                        if sp_key in st.session_state.selling_suggestions:
                            suggestions_text = st.session_state.selling_suggestions[sp_key]
                            suggestion_lines = [l.strip() for l in suggestions_text.split('\n') if l.strip() and l.strip()[0].isdigit()]
                            for si, sline in enumerate(suggestion_lines):
                                clean = re.sub(r'^\d+[\.\、\)]\s*', '', sline)
                                if st.button(f"👆 选用: {clean}", key=f"pick_{i}_{si}"):
                                    st.session_state.selling_inputs[sp_key] = clean
                                    st.rerun()

                        st.markdown("---")

    # 补充意见 + 生成文档（全宽）
    st.markdown("---")
    comment_col, action_col = st.columns([2, 1])

    with comment_col:
        st.markdown("#### 💬 补充意见（可选）")
        extra_comments = st.text_area("输入额外的审核意见或备注", height=80, placeholder="例如: 整体语气偏硬，建议更口语化一些...", key="extra_comments")

    with action_col:
        st.markdown("#### 📊 审核统计")
        accepted = len(selected)
        st.markdown(f"已采纳 **{accepted}** / {total} 条")
        st.progress(accepted / total if total > 0 else 0)

        if kol_name:
            output_name = f"{kol_name}_{TODAY}_KOL-赞意_第{version_num}版"
            st.markdown(f"`📁 {output_name}.docx`")

            if st.button("确认并生成批注文档", key="btn_gen_kol", use_container_width=True, type="primary"):
                buffer, title = create_annotated_docx(
                    st.session_state.kol_content,
                    st.session_state.kol_issues,
                    selected, kol_name, version_num, 2,
                    extra_comments if extra_comments else None,
                    st.session_state.selling_inputs
                )
                st.download_button("下载文档 - 可发给客户", buffer, f"{output_name}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="dl_kol")

# ========== 客户反馈分析区（全宽） ==========
if st.session_state.client_analysis:
    st.markdown("---")
    st.markdown("### 💬 客户反馈分析")

    feedback_left, feedback_right = st.columns([1, 1])

    with feedback_left:
        st.markdown("#### 📄 客户修改内容")
        if st.session_state.client_content_saved:
            st.markdown(f'<div class="original-text-box">{st.session_state.client_content_saved.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)

    with feedback_right:
        st.markdown("#### ✏️ 修改分析")
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
                checked = st.checkbox(c.get('desc', ''), key=f"cc_{i}", value=is_ok)
                status_icon = "✅" if is_ok else "⚠️"
                if c.get("suggestion"):
                    st.caption(f"{status_icon} {c['suggestion']}")

            if len(parts) > 1:
                st.info(parts[1].strip())
        else:
            st.write(st.session_state.client_analysis)

    # 补充意见 + 生成
    st.markdown("---")
    fc_col, fa_col = st.columns([2, 1])

    with fc_col:
        st.markdown("#### 💬 补充意见给KOL（可选）")
        client_extra = st.text_area("输入额外的反馈意见", height=80, placeholder="例如: 客户希望第3张图片突出产品包装...", key="client_extra")

    with fa_col:
        if kol_name:
            output_name = f"{kol_name}_{TODAY}_KOL-赞意-客户_第{version_num}版"
            st.markdown(f"`📁 {output_name}.docx`")

            if st.button("确认并生成给KOL的文档", key="btn_gen_client", use_container_width=True, type="primary"):
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
                saved = st.session_state.client_content_saved
                for line in saved.split('\n'):
                    if line.strip():
                        doc.add_paragraph(line)
                buffer = io.BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                st.download_button("下载文档 - 可发给KOL", buffer, f"{output_name}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="dl_client")

st.markdown("---")
st.caption("🤖 赞意AI审稿系统 v3.2")
