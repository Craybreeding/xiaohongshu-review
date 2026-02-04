import streamlit as st
import re
import os
import json
from datetime import datetime
from docx import Document
import io
import urllib.request

TODAY = datetime.now().strftime("%Y%m%d")

# 默认审稿规则（可被上传的JSON覆盖）
DEFAULT_RULES = {
    "version": "2026-02-04",
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
    "min_tags": 10,
    "suggestions": {"敏宝": "敏感体质宝宝", "新生儿": "初生宝宝", "过敏": "敏敏", "预防": "远离", "生长": "成长", "发育": "成长", "免疫": "保护力"}
}

# 默认内容切角方向
DEFAULT_ANGLES = {
    "防敏科普": "以科普形式介绍适度水解奶粉的防敏原理，强调雀巢尖峰水解技术和GINI研究认证，语气专业但易懂。",
    "妈妈分享": "以妈妈第一人称分享自己给宝宝选奶粉的经历，强调产品体验和宝宝的变化，语气亲切真实。",
    "产品测评": "以测评博主角度分析产品成分、配方优势，强调数据和对比，语气客观专业。",
    "新手妈妈攻略": "面向新手妈妈群体，以攻略形式介绍如何选择第一口奶粉，强调防敏的重要性，语气温暖引导。",
}

def get_rules():
    """获取当前生效的审稿规则"""
    if 'review_rules' in st.session_state:
        return st.session_state.review_rules
    return DEFAULT_RULES

def get_suggestions():
    """获取禁词替换建议"""
    rules = get_rules()
    return rules.get("suggestions", DEFAULT_RULES["suggestions"])

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
    rules = get_rules()
    suggestions = get_suggestions()
    data = parse_content(content)
    issues = []

    for kw in rules["required_keywords"]:
        if kw not in data["text"]:
            issues.append({"type": "keyword", "desc": f"缺少关键词: {kw}", "suggestion": f"请加入「{kw}」"})

    exceptions = rules.get("allowed_exceptions", [])
    for cat, words in rules["forbidden_words"].items():
        for w in words:
            if w in data["text"]:
                idx = data["text"].find(w)
                ctx = data["text"][max(0,idx-10):idx+len(w)+10]
                if not any(e in ctx for e in exceptions):
                    sug = suggestions.get(w, "删除")
                    issues.append({"type": "forbidden", "desc": f"禁词「{w}」", "context": ctx, "suggestion": f"改为「{sug}」"})

    for sp in rules["selling_points"]:
        if sp not in data["text"]:
            issues.append({"type": "selling", "desc": f"缺少卖点: {sp}", "suggestion": f"请加入: {sp}"})

    if data["word_count"] > rules["max_words"]:
        issues.append({"type": "structure", "desc": f"字数超限: {data['word_count']}/{rules['max_words']}", "suggestion": "请精简"})

    if len(data["tags"]) < rules["min_tags"]:
        issues.append({"type": "structure", "desc": f"标签不足: {len(data['tags'])}/{rules['min_tags']}", "suggestion": "请补充"})

    for t in rules["required_tags"]:
        if t not in data["tags"]:
            issues.append({"type": "tag", "desc": f"缺少标签: {t}", "suggestion": f"请加入 {t}"})

    return issues, data

def call_llm_api(prompt):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "Error: 未设置OPENAI_API_KEY环境变量"
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    data = {"model": "gpt-4o", "max_tokens": 4000, "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result["choices"][0]["message"]["content"]
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
    return call_llm_api(prompt)

def create_annotated_docx(content, issues, selected_issues, kol_name, version, step, extra_comments=None, selling_inputs=None):
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()

    # 设置默认字体
    style = doc.styles['Normal']
    font = style.font
    font.name = 'PingFang SC'
    font.size = Pt(11)

    if step == 2:
        title = f"{kol_name}_{TODAY}_KOL-赞意_第{version}版"
        subtitle = "赞意审核批注版"
    else:
        title = f"{kol_name}_{TODAY}_KOL-赞意-客户_第{version}版"
        subtitle = "客户反馈处理版"

    # 标题
    h = doc.add_heading(title, 0)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x2C, 0x3E, 0x6B)

    # 基本信息
    info = doc.add_paragraph()
    info_run = info.add_run(f"审核时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  文档类型: {subtitle}")
    info_run.font.size = Pt(9)
    info_run.font.color.rgb = RGBColor(0x71, 0x71, 0x71)

    # 分隔线
    doc.add_paragraph("─" * 50)

    # ===== 审核意见区域 =====
    if selected_issues:
        h2 = doc.add_heading("赞意审核意见（已采纳）", level=1)
        for run in h2.runs:
            run.font.color.rgb = RGBColor(0x8B, 0x45, 0x57)  # 酒红色

        issue_types_cn = {"keyword": "关键词", "forbidden": "禁词", "selling": "卖点", "structure": "结构", "tag": "标签"}

        for i, idx in enumerate(selected_issues):
            if idx < len(issues):
                issue = issues[idx]
                issue_type = issue.get("type", "")
                type_cn = issue_types_cn.get(issue_type, "")

                p = doc.add_paragraph()

                # 类型标签 - 酒红色背景
                tag_run = p.add_run(f"【{type_cn}】")
                tag_run.bold = True
                tag_run.font.color.rgb = RGBColor(0x8B, 0x45, 0x57)
                tag_run.font.size = Pt(11)

                # 问题描述 - 加粗
                desc_run = p.add_run(f" {issue['desc']}")
                desc_run.bold = True
                desc_run.font.size = Pt(11)

                # 建议 - 蓝色
                sug_run = p.add_run(f"\n    建议: {issue['suggestion']}")
                sug_run.font.color.rgb = RGBColor(0x2C, 0x3E, 0x6B)
                sug_run.font.size = Pt(10)

                # 卖点自定义写法 - 绿色
                sp_key = f"sp_{idx}"
                if selling_inputs and sp_key in selling_inputs and selling_inputs[sp_key]:
                    custom_run = p.add_run(f"\n    ★ 推荐表达: {selling_inputs[sp_key]}")
                    custom_run.font.color.rgb = RGBColor(0x0B, 0x6E, 0x2F)
                    custom_run.bold = True
                    custom_run.font.size = Pt(10)

                # 段落底部加间距
                p.paragraph_format.space_after = Pt(8)

        doc.add_paragraph("─" * 50)

    # ===== 补充意见 =====
    if extra_comments:
        h3 = doc.add_heading("赞意补充意见", level=1)
        for run in h3.runs:
            run.font.color.rgb = RGBColor(0x8B, 0x45, 0x57)

        p = doc.add_paragraph()
        r = p.add_run(extra_comments)
        r.font.color.rgb = RGBColor(0x8B, 0x45, 0x57)
        r.font.size = Pt(11)
        doc.add_paragraph("─" * 50)

    # ===== 稿件原文 =====
    h4 = doc.add_heading("稿件内容", level=1)
    for run in h4.runs:
        run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    # 在稿件中高亮标注禁词
    for line in content.split('\n'):
        if line.strip():
            p = doc.add_paragraph()
            remaining = line
            # 检查这行是否包含禁词
            has_forbidden = False
            for cat, words in get_rules()["forbidden_words"].items():
                for w in words:
                    if w in remaining:
                        has_forbidden = True
                        break
                if has_forbidden:
                    break

            if has_forbidden:
                # 逐词检查并高亮
                pos = 0
                segments = []
                temp = remaining
                for cat, words in get_rules()["forbidden_words"].items():
                    for w in words:
                        temp = temp.replace(w, f"\x00{w}\x01")
                parts = temp.split('\x00')
                for part in parts:
                    if '\x01' in part:
                        forbidden_word, rest = part.split('\x01', 1)
                        # 禁词 - 红色加粗
                        r = p.add_run(forbidden_word)
                        r.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)
                        r.bold = True
                        r.font.highlight_color = 6  # 黄色高亮
                        if rest:
                            p.add_run(rest)
                    else:
                        if part:
                            p.add_run(part)
            else:
                p.add_run(line).font.size = Pt(11)

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

# ========== 审稿规则 + 内容切角 ==========
with st.expander("📐 审稿规则 & 内容切角方向（点击展开配置）", expanded=False):
    rule_col, angle_col = st.columns([1, 1])

    with rule_col:
        st.markdown("**📋 审稿规则**")
        current_rules = get_rules()
        rule_ver = current_rules.get("version", "未知")
        st.markdown(f"当前规则版本: **{rule_ver}**")
        st.caption(f"关键词 {len(current_rules['required_keywords'])} 个 | 禁词 {sum(len(v) for v in current_rules['forbidden_words'].values())} 个 | 卖点 {len(current_rules['selling_points'])} 个 | 标签 {len(current_rules['required_tags'])} 个")

        rules_file = st.file_uploader("上传新规则 (JSON)", type=["json"], key="rules_upload")
        if rules_file:
            try:
                new_rules = json.loads(rules_file.read().decode('utf-8'))
                # 验证必要字段
                required_fields = ["required_keywords", "forbidden_words", "selling_points", "required_tags", "max_words", "min_tags"]
                missing = [f for f in required_fields if f not in new_rules]
                if missing:
                    st.error(f"规则文件缺少字段: {', '.join(missing)}")
                else:
                    st.session_state.review_rules = new_rules
                    st.success(f"规则已更新! 版本: {new_rules.get('version', '自定义')}")
                    # 如果已有稿件，重新审核
                    if st.session_state.kol_content:
                        issues, data = run_review(st.session_state.kol_content)
                        st.session_state.kol_issues = issues
                        st.session_state.kol_data = data
            except json.JSONDecodeError:
                st.error("JSON格式错误，请检查文件")

        # 下载当前规则模板
        rules_json = json.dumps(current_rules, ensure_ascii=False, indent=2)
        st.download_button("下载当前规则模板", rules_json.encode('utf-8'), "review_rules.json", "application/json", key="dl_rules")

    with angle_col:
        st.markdown("**🎯 内容切角方向**")
        angles = st.session_state.content_angles
        angle_options = ["请选择切角方向..."] + list(angles.keys())
        selected = st.selectbox("选择内容切角", angle_options, key="angle_select")

        if selected != "请选择切角方向...":
            st.session_state.selected_angle = selected
            st.info(f"**{selected}**: {angles[selected]}")
        else:
            st.session_state.selected_angle = None

        # 上传新的切角storyline
        st.markdown("---")
        st.caption("上传新的切角方向 (JSON)")
        angle_file = st.file_uploader("上传切角方向文件", type=["json"], key="angle_upload")
        if angle_file:
            try:
                new_angles = json.loads(angle_file.read().decode('utf-8'))
                if isinstance(new_angles, dict):
                    st.session_state.content_angles.update(new_angles)
                    st.success(f"已添加 {len(new_angles)} 个切角方向")
                    st.rerun()
                else:
                    st.error("格式错误: JSON应该是 {\"切角名称\": \"storyline描述\"} 格式")
            except json.JSONDecodeError:
                st.error("JSON格式错误")

        # 下载切角模板
        angles_json = json.dumps(angles, ensure_ascii=False, indent=2)
        st.download_button("下载当前切角模板", angles_json.encode('utf-8'), "content_angles.json", "application/json", key="dl_angles")

# ========== Session State 初始化 ==========
if 'review_rules' not in st.session_state:
    st.session_state.review_rules = DEFAULT_RULES.copy()
if 'content_angles' not in st.session_state:
    st.session_state.content_angles = DEFAULT_ANGLES.copy()
if 'selected_angle' not in st.session_state:
    st.session_state.selected_angle = None
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

    # 有内容就自动审稿
    if kol_content:
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
    s4.metric("字数上限", f"{get_rules()['max_words']}")

    # 左：原文 | 右：审核意见
    preview_left, preview_right = st.columns([1, 1])

    with preview_left:
        st.markdown("#### 📄 稿件原文")
        # 把原文中的禁词高亮显示
        highlighted = st.session_state.kol_content
        for cat, words in get_rules()["forbidden_words"].items():
            for w in words:
                if w in highlighted:
                    highlighted = highlighted.replace(w, f'<mark style="background-color:#fed7d7;padding:2px 4px;border-radius:3px;font-weight:bold;">{w}</mark>')
        # 把必含关键词高亮（绿色）
        for kw in get_rules()["required_keywords"]:
            if kw in highlighted:
                highlighted = highlighted.replace(kw, f'<mark style="background-color:#c6f6d5;padding:2px 4px;border-radius:3px;">{kw}</mark>')

        html_content = highlighted.replace('\n', '<br>')
        # 原文直接展开显示，不限高度
        st.markdown(f"""<div style="background-color:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:15px;font-size:14px;line-height:2.0;">
{html_content}
</div>""", unsafe_allow_html=True)
        st.caption("🔴 红色高亮 = 禁词  |  🟢 绿色高亮 = 必含关键词")

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

                    # 显示原文引用上下文
                    if issue.get("context"):
                        ctx = issue["context"]
                        st.markdown(f'<div style="background:#fff8f0;border-left:3px solid #ed8936;padding:5px 10px;margin:4px 0;font-size:12px;color:#744210;">📍 原文: "...{ctx}..."</div>', unsafe_allow_html=True)
                    elif issue_type in ["keyword", "selling"]:
                        st.markdown(f'<div style="background:#fff8f0;border-left:3px solid #ed8936;padding:5px 10px;margin:4px 0;font-size:12px;color:#744210;">📍 原文中未找到此内容</div>', unsafe_allow_html=True)

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
                            result = call_llm_api(prompt)
                            if result and not result.startswith("Error"):
                                st.session_state.selling_suggestions[sp_key] = result
                                st.rerun()
                            elif result and result.startswith("Error"):
                                st.error(f"AI调用失败: {result}")
                            else:
                                st.error("API Key未设置，请配置OPENAI_API_KEY环境变量")

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

    # ===== 人话修改 =====
    st.markdown("---")
    st.markdown("#### 🗣️ 人话修改")
    st.caption("用AI把稿件改得更口语化、更像真实妈妈在小红书分享的语气")

    if 'social_rewrite' not in st.session_state:
        st.session_state.social_rewrite = ""

    if st.button("🗣️ 人话修改", key="btn_social", use_container_width=True):
        content = st.session_state.kol_content
        rules = get_rules()
        # 构建禁词列表
        all_forbidden = []
        for cat, words in rules["forbidden_words"].items():
            all_forbidden.extend(words)
        forbidden_str = "、".join(all_forbidden)

        # 构建切角方向提示
        angle_hint = ""
        if st.session_state.selected_angle:
            angle_name = st.session_state.selected_angle
            angle_desc = st.session_state.content_angles.get(angle_name, "")
            angle_hint = f"\n内容切角方向：{angle_name}\n切角说明：{angle_desc}\n请按照这个切角方向来调整稿件的叙事角度和风格。\n"

        prompt = f"""你是小红书母婴领域的资深KOL文案改写专家。

请把以下稿件改写得更加口语化、social、接地气，像一个真实的妈妈在小红书上分享经验。
{angle_hint}
要求：
1. 保留所有产品卖点信息，不能删减核心内容
2. 语气要自然、亲切，像跟闺蜜聊天
3. 可以加一些妈妈的真实感受、口头禅（比如"姐妹们"、"真的绝了"、"谁懂啊"等）
4. 不能用这些禁词：{forbidden_str}
5. 段落要短，适合手机阅读
6. 保留所有标签（#开头的）

原稿件：
{content}

请直接输出改写后的完整稿件，不要加任何说明："""
        result = call_llm_api(prompt)
        if result and not result.startswith("Error"):
            st.session_state.social_rewrite = result
            st.rerun()
        elif result:
            st.error(f"AI调用失败: {result}")

    if st.session_state.social_rewrite:
        rewrite_left, rewrite_right = st.columns([1, 1])
        with rewrite_left:
            st.markdown("**原文**")
            st.text_area("原文内容", st.session_state.kol_content, height=300, disabled=True, key="social_orig")
        with rewrite_right:
            st.markdown("**人话版本** (可直接编辑)")
            edited_social = st.text_area("修改后内容", st.session_state.social_rewrite, height=300, key="social_edit")
            if edited_social != st.session_state.social_rewrite:
                st.session_state.social_rewrite = edited_social

        # 用人话版本替换原稿
        if st.button("采用人话版本作为正式稿件", key="btn_apply_social", use_container_width=True, type="primary"):
            st.session_state.kol_content = st.session_state.social_rewrite
            issues, data = run_review(st.session_state.social_rewrite)
            st.session_state.kol_issues = issues
            st.session_state.kol_data = data
            st.session_state.social_rewrite = ""
            st.rerun()

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
