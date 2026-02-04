import streamlit as st
import re
import os
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_COLOR_INDEX
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
            issues.append({"type": "keyword", "desc": f"缺少必须关键词: {kw}", "suggestion": f"请在稿件中加入「{kw}」"})
    
    exceptions = REVIEW_RULES["allowed_exceptions"]
    for cat, words in REVIEW_RULES["forbidden_words"].items():
        for w in words:
            if w in data["text"]:
                idx = data["text"].find(w)
                ctx = data["text"][max(0,idx-10):idx+len(w)+10]
                if not any(e in ctx for e in exceptions):
                    sug = SUGGESTIONS.get(w, "删除此词")
                    issues.append({"type": "forbidden", "desc": f"出现禁词「{w}」", "context": ctx, "suggestion": f"建议改为「{sug}」"})
    
    for sp in REVIEW_RULES["selling_points"]:
        if sp not in data["text"]:
            issues.append({"type": "selling", "desc": f"缺少卖点", "suggestion": f"请加入: {sp}"})
    
    if data["word_count"] > REVIEW_RULES["max_words"]:
        issues.append({"type": "structure", "desc": f"字数超限: {data['word_count']}/{REVIEW_RULES['max_words']}", "suggestion": "请精简内容"})
    
    if len(data["tags"]) < REVIEW_RULES["min_tags"]:
        issues.append({"type": "structure", "desc": f"标签不足: {len(data['tags'])}/{REVIEW_RULES['min_tags']}", "suggestion": "请补充标签"})
    
    for t in REVIEW_RULES["required_tags"]:
        if t not in data["tags"]:
            issues.append({"type": "tag", "desc": f"缺少必提标签: {t}", "suggestion": f"请加入 {t}"})
    
    return issues, data

def call_claude_api(prompt):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    data = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result["content"][0]["text"]
    except Exception as e:
        return f"Error: {str(e)}"

def analyze_client_feedback(original, client_modified):
    prompt = f"""你是小红书KOL稿件审核专家。请对比分析客户修改的内容。

原稿件(赞意审核后):
{original}

客户修改后:
{client_modified}

审核规则:
- 禁词: 敏宝、奶瓶、奶嘴、新生儿、过敏、疾病、预防、生长、发育、免疫、最好、最佳
- 例外: "第一口奶粉"中的"第一"不算禁词

请分析:
1. 客户修改了哪些内容(逐条列出)
2. 每条修改是否符合审核规则
3. 不符合的给出修改建议

用以下格式回复:

===修改分析===
修改1: [修改内容描述]
状态: 符合/不符合
建议: [如不符合,给出建议]

修改2: ...

===总结===
符合规则的修改: X条
需要调整的修改: X条
"""
    return call_claude_api(prompt)

def create_annotated_docx(content, issues, selected_issues, kol_name, version, step):
    doc = Document()
    
    if step == 1:
        title = f"{kol_name}_{TODAY}_KOL_第{version}版"
        subtitle = "KOL原稿"
    elif step == 2:
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
        doc.add_heading("审核意见", level=1)
        for i, idx in enumerate(selected_issues):
            if idx < len(issues):
                issue = issues[idx]
                p = doc.add_paragraph()
                p.add_run(f"{i+1}. {issue['desc']}").bold = True
                p.add_run(f"\n   建议: {issue['suggestion']}")
        doc.add_paragraph("---")
    
    doc.add_heading("稿件内容", level=1)
    for line in content.split('\n'):
        if line.strip():
            p = doc.add_paragraph(line)
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer, title

st.set_page_config(page_title="小红书KOL审稿系统", page_icon="🔍", layout="wide")

st.markdown("""
<style>
.kol-box {
    background-color: #fff0f3;
    border: 2px solid #ff6b6b;
    border-radius: 15px;
    padding: 20px;
    margin: 10px 0;
}
.client-box {
    background-color: #f0fff4;
    border: 2px solid #38a169;
    border-radius: 15px;
    padding: 20px;
    margin: 10px 0;
}
.step-badge {
    background-color: #667eea;
    color: white;
    padding: 8px 20px;
    border-radius: 20px;
    font-weight: bold;
    display: inline-block;
    margin-bottom: 15px;
    font-size: 14px;
}
.step-badge-pink {
    background-color: #ff6b6b;
}
.step-badge-green {
    background-color: #38a169;
}
.file-name {
    background-color: #f7fafc;
    border: 1px solid #e2e8f0;
    padding: 10px;
    border-radius: 8px;
    font-family: monospace;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align:center;color:#ff6b6b;'>小红书KOL审稿系统</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:gray;'>能恩全护 - 完整审核工作流</p>", unsafe_allow_html=True)
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    kol_name = st.text_input("KOL名称", placeholder="例如: 团妈爱测评", value="")
with col2:
    version_num = st.selectbox("当前版本", [1, 2, 3, 4, 5], index=0)

st.markdown(f"**当前日期**: {TODAY}")
st.markdown("---")

if 'kol_issues' not in st.session_state:
    st.session_state.kol_issues = []
if 'kol_content' not in st.session_state:
    st.session_state.kol_content = ""
if 'client_analysis' not in st.session_state:
    st.session_state.client_analysis = ""

col_left, col_right = st.columns(2)

with col_left:
    st.markdown('<span class="step-badge step-badge-pink">Step 1: KOL稿件 - 赞意审核 - 完毕给客户</span>', unsafe_allow_html=True)
    st.markdown('<div class="kol-box">', unsafe_allow_html=True)
    
    st.markdown("### 📄 上传KOL稿件")
    st.caption("上传KOL提交的大纲或稿件，进行审核")
    
    kol_file = st.file_uploader("上传稿件 (.docx)", type=["docx"], key="kol_file")
    kol_text = st.text_area("或粘贴内容", height=200, placeholder="粘贴KOL稿件内容...", key="kol_text_input")
    
    kol_content = ""
    if kol_file:
        kol_file.seek(0)
        kol_content = read_docx(kol_file)
        st.success(f"已读取: {kol_file.name}")
    elif kol_text:
        kol_content = kol_text
    
    if st.button("开始审稿", type="primary", key="review_kol", use_container_width=True):
        if not kol_name:
            st.error("请先填写KOL名称")
        elif not kol_content:
            st.error("请上传或粘贴KOL稿件")
        else:
            issues, data = run_review(kol_content)
            st.session_state.kol_issues = issues
            st.session_state.kol_content = kol_content
            st.success(f"审核完成! 发现 {len(issues)} 个问题")
    
    if st.session_state.kol_issues:
        st.markdown("### 审核意见 (勾选采纳)")
        selected = []
        for i, issue in enumerate(st.session_state.kol_issues):
            checked = st.checkbox(f"{issue['desc']}", key=f"issue_{i}", value=True)
            if checked:
                selected.append(i)
            st.caption(f"  建议: {issue['suggestion']}")
        
        st.markdown("---")
        
        if kol_name and st.session_state.kol_content:
            output_name = f"{kol_name}_{TODAY}_KOL-赞意_第{version_num}版"
            st.markdown(f'<div class="file-name">📁 输出: {output_name}.docx</div>', unsafe_allow_html=True)
            
            if st.button("生成批注文档", key="gen_kol_doc", use_container_width=True):
                buffer, title = create_annotated_docx(
                    st.session_state.kol_content, 
                    st.session_state.kol_issues, 
                    selected, 
                    kol_name, 
                    version_num, 
                    2
                )
                st.download_button(
                    label="下载批注文档 - 可发给客户",
                    data=buffer,
                    file_name=f"{output_name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="download_kol"
                )
                st.success("文档已生成!")
    
    st.markdown('</div>', unsafe_allow_html=True)

with col_right:
    st.markdown('<span class="step-badge step-badge-green">Step 2: 客户反馈 - 赞意处理 - 完毕给KOL</span>', unsafe_allow_html=True)
    st.markdown('<div class="client-box">', unsafe_allow_html=True)
    
    st.markdown("### 💬 上传客户反馈")
    st.caption("上传客户修改后的文档，分析修改内容")
    
    client_file = st.file_uploader("上传客户反馈 (.docx)", type=["docx"], key="client_file")
    client_text = st.text_area("或粘贴内容", height=200, placeholder="粘贴客户修改后的内容...", key="client_text_input")
    
    client_content = ""
    if client_file:
        client_file.seek(0)
        client_content = read_docx(client_file)
        st.success(f"已读取: {client_file.name}")
    elif client_text:
        client_content = client_text
    
    if st.button("分析客户反馈", type="primary", key="analyze_client", use_container_width=True):
        if not kol_name:
            st.error("请先填写KOL名称")
        elif not client_content:
            st.error("请上传或粘贴客户反馈")
        elif not st.session_state.kol_content:
            st.error("请先在左侧上传KOL原稿")
        else:
            with st.spinner("AI正在分析客户修改..."):
                analysis = analyze_client_feedback(st.session_state.kol_content, client_content)
                st.session_state.client_analysis = analysis
    
    if st.session_state.client_analysis:
        st.markdown("### 客户修改分析")
        
        if "===修改分析===" in st.session_state.client_analysis:
            parts = st.session_state.client_analysis.split("===总结===")
            analysis_part = parts[0].replace("===修改分析===", "").strip()
            
            lines = analysis_part.split("\n")
            current_change = {}
            changes = []
            
            for line in lines:
                line = line.strip()
                if line.startswith("修改"):
                    if current_change:
                        changes.append(current_change)
                    current_change = {"desc": line, "status": "", "suggestion": ""}
                elif line.startswith("状态:"):
                    current_change["status"] = line.replace("状态:", "").strip()
                elif line.startswith("建议:"):
                    current_change["suggestion"] = line.replace("建议:", "").strip()
            if current_change:
                changes.append(current_change)
            
            for i, change in enumerate(changes):
                is_ok = "符合" in change.get("status", "")
                icon = "✅" if is_ok else "⚠️"
                
                checked = st.checkbox(
                    f"{icon} {change.get('desc', '')}",
                    key=f"client_change_{i}",
                    value=is_ok
                )
                if change.get("suggestion"):
                    st.caption(f"  {change['suggestion']}")
            
            if len(parts) > 1:
                st.markdown("---")
                st.markdown("### 总结")
                st.info(parts[1].strip())
        else:
            st.markdown(st.session_state.client_analysis)
        
        st.markdown("---")
        
        if kol_name and client_content:
            output_name = f"{kol_name}_{TODAY}_KOL-赞意-客户_第{version_num}版"
            st.markdown(f'<div class="file-name">📁 输出: {output_name}.docx</div>', unsafe_allow_html=True)
            
            if st.button("生成给KOL的文档", key="gen_client_doc", use_container_width=True):
                doc = Document()
                doc.add_heading(output_name, 0)
                doc.add_paragraph(f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                doc.add_paragraph("文档类型: 客户反馈处理版 - 可发给KOL")
                doc.add_paragraph("---")
                doc.add_heading("客户修改分析", level=1)
                doc.add_paragraph(st.session_state.client_analysis)
                doc.add_paragraph("---")
                doc.add_heading("修改后内容", level=1)
                for line in client_content.split('\n'):
                    if line.strip():
                        doc.add_paragraph(line)
                
                buffer = io.BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                
                st.download_button(
                    label="下载文档 - 可发给KOL",
                    data=buffer,
                    file_name=f"{output_name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="download_client"
                )
                st.success("文档已生成!")
    
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown("### 📋 文件命名规范")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"""
    **Step 1: KOL原稿**
```
    {kol_name or 'KOL名'}_{TODAY}_KOL_第{version_num}版
```
    """)
with col2:
    st.markdown(f"""
    **Step 2: 赞意审核后**
```
    {kol_name or 'KOL名'}_{TODAY}_KOL-赞意_第{version_num}版
```
    """)
with col3:
    st.markdown(f"""
    **Step 3: 客户反馈后**
```
    {kol_name or 'KOL名'}_{TODAY}_KOL-赞意-客户_第{version_num}版
```
    """)

st.markdown("---")
st.caption(f"小红书KOL审稿系统 v3.0 | {RULE_VERSION}")
