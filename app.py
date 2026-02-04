"""
小红书KOL审稿Agent - 网页版 v2.0
"""
import streamlit as st
import re
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict

RULE_VERSION = "2026年2月4日"
BRIEF_VERSION = "2026年2月版"

BRIEF_CONTENT = """
**Storyline：**
1. 以营养/育婴师等专业身份背景出发，引出中国初生宝宝敏敏发生率高达40%
2. 分享科学防敏攻略，强调第一口选奶对防敏的重要性
3. 从水解技术、加强配方等角度介绍产品，突出防敏+自护+长肉三重实力
4. 主题强化：选对第一口奶粉是关键，建议优选能恩全护

**不可改动卖点：**
- 多项科学实证的雀巢尖峰水解技术
- 防敏领域权威德国GINI研究认证
- 能长效防敏20年
- 相比于牛奶蛋白致敏性降低1000倍
- 全球创新的超倍自护科技
- 6种HMO加上明星双菌B.Infantis和Bb-12
- 协同作用释放高倍的原生保护力
- 短短28天就能调理好娃的肚肚菌菌环境
- 保护力能持续15个月
- 25种维生素和矿物质
- 全乳糖的配方口味清淡
"""

REVIEW_RULES = {
    "project_info": {"name": "能恩全护小红书达人种草", "brand": "能恩全护"},
    "required_keywords": {
        "正文": ["适度水解", "防敏", "能恩全护"],
    },
    "forbidden_words": {
        "禁止词": ["敏宝", "奶瓶", "奶嘴", "新生儿", "过敏", "疾病"],
        "禁疗效表述": ["预防", "生长", "发育", "免疫"],
        "禁绝对化": ["最好", "最佳", "最优", "第一名", "TOP1", "top1", "No.1"]
    },
    "allowed_exceptions": ["第一口奶粉", "第一口配方粉", "#第一口奶粉", "#第一口"],
    "selling_points_exact": {
        "防敏水解技术": [
            "多项科学实证的雀巢尖峰水解技术",
            "防敏领域权威德国GINI研究认证",
            "能长效防敏20年",
            "相比于牛奶蛋白致敏性降低1000倍"
        ],
        "自护力": [
            "全球创新的超倍自护科技",
            "6种HMO加上明星双菌B.Infantis和Bb-12",
            "协同作用释放高倍的原生保护力",
            "短短28天就能调理好娃的肚肚菌菌环境",
            "保护力能持续15个月"
        ],
        "基础营养": [
            "25种维生素和矿物质",
            "全乳糖的配方口味清淡"
        ]
    },
    "structure_requirements": {"正文字数上限": 900, "话题标签数量": 10},
    "required_tags": ["#能恩全护", "#能恩全护水奶", "#适度水解", "#适度水解奶粉", "#适度水解奶粉推荐", "#防敏奶粉", "#第一口奶粉", "#雀巢适度水解"]
}

FORBIDDEN_SUGGESTIONS = {
    "敏宝": "敏感体质宝宝", "奶瓶": "喂养工具", "奶嘴": "喂养配件",
    "新生儿": "初生宝宝", "过敏": "敏感/敏敏", "疾病": "不适",
    "预防": "远离/减少", "生长": "成长", "发育": "成长", "免疫": "保护力/自护力"
}

@dataclass
class CheckItem:
    name: str
    passed: bool
    total: int = 0
    found: int = 0
    issues: List[str] = field(default_factory=list)
    details: List[Dict] = field(default_factory=list)

@dataclass
class ReviewReport:
    kol_name: str
    version: str
    reviewer: str
    keyword_check: CheckItem = None
    forbidden_check: CheckItem = None
    selling_point_check: CheckItem = None
    structure_check: CheckItem = None
    tag_check: CheckItem = None
    objective_score: float = 0.0
    subjective_score: float = 80.0
    total_score: float = 0.0
    good_points: List[str] = field(default_factory=list)

class ContentParser:
    def __init__(self, content: str):
        self.raw_content = content
        self.body_paragraphs = []
        self.tags = []
        self._parse()
    
    def _parse(self):
        lines = self.raw_content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            tags_in_line = re.findall(r'#[\w\u4e00-\u9fff]+', line)
            if tags_in_line:
                self.tags.extend(tags_in_line)
            remaining = re.sub(r'#[\w\u4e00-\u9fff]+', '', line).strip()
            if remaining:
                self.body_paragraphs.append(remaining)
    
    @property
    def full_text(self):
        return self.raw_content
    
    @property
    def body_text(self):
        return '\n'.join(self.body_paragraphs)
    
    @property
    def word_count(self):
        return len(re.findall(r'[\u4e00-\u9fff]', self.body_text))

def check_keywords(parser, rules):
    required = rules.get('required_keywords', {})
    issues, details = [], []
    total, found = 0, 0
    for location, keywords in required.items():
        for kw in keywords:
            total += 1
            if kw in parser.full_text:
                found += 1
                details.append({"keyword": kw, "location": location, "status": "✅"})
            else:
                issues.append(f"{location}缺少「{kw}」")
                details.append({"keyword": kw, "location": location, "status": "❌"})
    return CheckItem(name="必须关键词", passed=len(issues)==0, total=total, found=found, issues=issues, details=details)

def check_forbidden(parser, rules):
    forbidden = rules.get('forbidden_words', {})
    exceptions = rules.get('allowed_exceptions', [])
    issues, details = [], []
    for category, words in forbidden.items():
        for word in words:
            for match in re.finditer(re.escape(word), parser.full_text):
                start, end = match.start(), match.end()
                context = parser.full_text[max(0,start-15):min(len(parser.full_text),end+15)]
                is_exception = any(exc in context for exc in exceptions)
                if not is_exception:
                    suggestion = FORBIDDEN_SUGGESTIONS.get(word, "请删除")
                    issues.append(f"出现{category}「{word}」")
                    details.append({"word": word, "category": category, "context": f"...{context}...", "suggestion": suggestion})
    return CheckItem(name="禁词检查", passed=len(issues)==0, total=0, found=0, issues=issues, details=details)

def check_selling_points(parser, rules):
    exact_points = rules.get('selling_points_exact', {})
    issues, details = [], []
    total, found = 0, 0
    for category, points in exact_points.items():
        for point in points:
            total += 1
            if point in parser.full_text:
                found += 1
                details.append({"point": point, "category": category, "status": "✅"})
            else:
                issues.append(f"[{category}] 缺少: {point[:25]}...")
                details.append({"point": point, "category": category, "status": "❌"})
    return CheckItem(name="不可改动卖点", passed=found==total, total=total, found=found, issues=issues, details=details)

def check_structure(parser, rules):
    struct_req = rules.get('structure_requirements', {})
    issues, details = [], []
    max_words = struct_req.get('正文字数上限', 900)
    word_count = parser.word_count
    if word_count > max_words:
        issues.append(f"字数超限: {word_count}字")
        details.append({"item": "字数", "value": word_count, "limit": max_words, "status": "❌"})
    else:
        details.append({"item": "字数", "value": word_count, "limit": max_words, "status": "✅"})
    req_tag_count = struct_req.get('话题标签数量', 10)
    tag_count = len(parser.tags)
    if tag_count < req_tag_count:
        issues.append(f"标签不足: {tag_count}个")
        details.append({"item": "标签数量", "value": tag_count, "limit": req_tag_count, "status": "❌"})
    else:
        details.append({"item": "标签数量", "value": tag_count, "limit": req_tag_count, "status": "✅"})
    return CheckItem(name="结构完整性", passed=len(issues)==0, total=2, found=2-len(issues), issues=issues, details=details)

def check_tags(parser, rules):
    required_tags = rules.get('required_tags', [])
    issues, details = [], []
    found = 0
    for tag in required_tags:
        if tag in parser.tags:
            found += 1
            details.append({"tag": tag, "status": "✅"})
        else:
            issues.append(f"缺少: {tag}")
            details.append({"tag": tag, "status": "❌"})
    return CheckItem(name="必提Tag", passed=len(issues)==0, total=len(required_tags), found=found, issues=issues, details=details)

def run_review(content, kol_name, version, reviewer):
    parser = ContentParser(content)
    report = ReviewReport(kol_name=kol_name, version=version, reviewer=reviewer)
    report.keyword_check = check_keywords(parser, REVIEW_RULES)
    report.forbidden_check = check_forbidden(parser, REVIEW_RULES)
    report.selling_point_check = check_selling_points(parser, REVIEW_RULES)
    report.structure_check = check_structure(parser, REVIEW_RULES)
    report.tag_check = check_tags(parser, REVIEW_RULES)
    
    checks = [(report.keyword_check, 0.15), (report.forbidden_check, 0.20), (report.selling_point_check, 0.30), (report.structure_check, 0.15), (report.tag_check, 0.20)]
    total_score = 0
    for check, weight in checks:
        if check.total > 0:
            score = check.found / check.total
        else:
            score = 1.0 if check.passed else 0.0
        total_score += score * weight
    report.objective_score = round(total_score * 100, 1)
    report.total_score = round(report.objective_score * 0.6 + report.subjective_score * 0.4, 1)
    
    if report.keyword_check.passed:
        report.good_points.append("关键词覆盖完整")
    if report.forbidden_check.passed:
        report.good_points.append("无禁词违规")
    if report.selling_point_check.found >= report.selling_point_check.total * 0.8:
        report.good_points.append("核心卖点覆盖良好")
    if report.structure_check.passed:
        report.good_points.append("结构规范")
    if report.tag_check.passed:
        report.good_points.append("必提标签完整")
    return report

st.set_page_config(page_title="小红书KOL审稿系统", page_icon="🔍", layout="wide")

st.markdown('<h1 style="text-align:center;color:#ff6b6b;">🔍 小红书KOL审稿系统</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align:center;color:gray;">能恩全护 · 小红书达人种草项目 · v2.0 结构化审核</p>', unsafe_allow_html=True)
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    st.info(f"📋 **审核规则版本**: {RULE_VERSION}")
with col2:
    st.info(f"📝 **Brief版本**: {BRIEF_VERSION}")

with st.expander("📖 点击查看完整Brief内容"):
    st.markdown(BRIEF_CONTENT)

st.markdown("---")

col1, col2, col3 = st.columns(3)
with col1:
    kol_name = st.text_input("👤 KOL名称", placeholder="例如: 小红薯妈妈")
with col2:
    version = st.selectbox("📌 版本号", ["V1", "V2", "V3", "V4", "V5", "FINAL"])
with col3:
    reviewer = st.selectbox("👁️ 审核方", ["赞意", "客户"])

st.markdown("### 📝 稿件内容")
content = st.text_area("请粘贴KOL稿件内容", height=250, placeholder="粘贴稿件内容...")

if st.button("🔍 开始审核", type="primary", use_container_width=True):
    if not kol_name:
        st.error("请输入KOL名称")
    elif not content.strip():
        st.error("请粘贴稿件内容")
    else:
        report = run_review(content, kol_name, version, reviewer)
        
        st.markdown("---")
        st.markdown("## 📊 审核报告")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("KOL", f"@{report.kol_name}")
        c2.metric("版本", report.version)
        c3.metric("审核方", report.reviewer)
        c4.metric("综合评分", f"{report.total_score}%")
        
        st.markdown("---")
        st.markdown("## 一、客观检查")
        
        with st.expander(f"1.1 必须关键词 — {'✅通过' if report.keyword_check.passed else '❌未通过'}", expanded=not report.keyword_check.passed):
            for d in report.keyword_check.details:
                st.markdown(f"{d['status']} **{d['keyword']}** ({d['location']})")
            for issue in report.keyword_check.issues:
                st.warning(issue)
        
        with st.expander(f"1.2 禁词检查 — {'✅无违规' if report.forbidden_check.passed else f'❌{len(report.forbidden_check.issues)}处违规'}", expanded=not report.forbidden_check.passed):
            if report.forbidden_check.passed:
                st.success("未发现禁词")
            for d in report.forbidden_check.details:
                st.error(f"**{d['word']}** ({d['category']}) → 建议: {d['suggestion']}")
                st.caption(f"上下文: {d['context']}")
        
        with st.expander(f"1.3 不可改动卖点 — {report.selling_point_check.found}/{report.selling_point_check.total}已覆盖", expanded=not report.selling_point_check.passed):
            for d in report.selling_point_check.details:
                st.markdown(f"{d['status']} [{d['category']}] {d['point'][:35]}...")
        
        with st.expander(f"1.4 结构完整性 — {'✅通过' if report.structure_check.passed else '❌未通过'}", expanded=not report.structure_check.passed):
            for d in report.structure_check.details:
                st.markdown(f"{d['status']} **{d['item']}**: {d['value']} (要求: {d['limit']})")
        
        with st.expander(f"1.5 必提Tag — {report.tag_check.found}/{report.tag_check.total}已包含", expanded=not report.tag_check.passed):
            cols = st.columns(4)
            for i, d in enumerate(report.tag_check.details):
                cols[i%4].markdown(f"{d['status']} `{d['tag']}`")
        
        st.markdown(f"### 📊 客观检查得分: **{report.objective_score}%**")
        
        st.markdown("---")
        st.markdown("## 二、主观检查 (LLM评估)")
        st.caption("⏳ 此功能即将上线，当前为预留展示")
        st.markdown(f"### 📊 主观检查得分: **{report.subjective_score}%**")
        
        st.markdown("---")
        st.markdown("## 三、综合评分")
        c1, c2, c3 = st.columns(3)
        c1.metric("客观检查 (60%)", f"{report.objective_score}%")
        c2.metric("主观检查 (40%)", f"{report.subjective_score}%")
        c3.metric("综合评分", f"{report.total_score}%")
        
        if report.good_points:
            st.markdown("## ✅ 做得好的地方")
            for p in report.good_points:
                st.markdown(f"- {p}")
        
        st.markdown("## 📝 审核总结")
        if report.total_score >= 90:
            st.success("✨ 优秀: 稿件质量很高!")
        elif report.total_score >= 75:
            st.info("👍 良好: 整体不错，请根据问题修改。")
        elif report.total_score >= 60:
            st.warning("⚠️ 需改进: 存在较多问题。")
        else:
            st.error("❌ 需大改: 建议参考Brief重新撰写。")

st.markdown("---")
st.markdown(f'<p style="text-align:center;color:gray;font-size:0.8rem;">小红书KOL审稿系统 v2.0 | 规则: {RULE_VERSION} | Brief: {BRIEF_VERSION}</p>', unsafe_allow_html=True)
