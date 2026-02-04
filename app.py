
小红书KOL审稿Agent - 网页版 v2.0
结构化审核报告
"""
import streamlit as st
import re
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum


# ============================================
# 版本信息
# ============================================
RULE_VERSION = "2026年2月4日"
BRIEF_VERSION = "2026年2月版"

BRIEF_CONTENT = """
### Storyline：

1、以营养/育婴师等专业身份背景出发，收到很多妈妈咨询想带娃出去玩耍，又怕宝宝因户外环境导致敏敏的痛点出发，引出中国初生宝宝敏敏发生率高达40%，点出【宝宝敏敏具体原因】家族遗传史（父母双方都敏感，宝宝敏敏概率飙升到80%）

2、分享科学防敏攻略，喂养方面强调第一口选奶对提前防敏的重要性，建议可以选择低敏的适度水解配方粉来作为宝宝的第一口配方粉。

3、从品牌实力、水解技术、加强配方、基础配方、粉质、口感等角度介绍产品，综合得出能恩全护是防敏奶粉中的顶配，突出（防敏+自护+长肉）三重喂养实力。

4、主题强化：呼吁宝爸宝妈，想带娃户外肆意玩耍，选对第一口奶粉是关键，建议优选能恩全护。

### 卖点描述（🔵蓝字不能改动，🟡黄字可删减）

**1、敏敏现状：** 我国初生宝宝敏敏率高达40%，要是有父母敏敏史，宝宝敏敏的概率将飙升到80%

**2、防敏卖点：** 🔵多项科学实证的雀巢尖峰水解技术 | 🔵防敏领域权威德国GINI研究认证 | 🔵能长效防敏20年 | 🔵相比于牛奶蛋白致敏性降低1000倍

**3、保护力卖点：** 🔵全球创新的超倍自护科技 | 🔵6种HMO加上明星双菌B.Infantis和Bb-12 | 🔵协同作用释放高倍的原生保护力 | 🔵短短28天就能调理好娃的肚肚菌菌环境 | 🔵保护力能持续15个月

**4、基础营养：** 🔵25种维生素和矿物质 | 🔵全乳糖的配方口味清淡
"""


# ============================================
# 审核规则配置
# ============================================
REVIEW_RULES = {
    "project_info": {
        "name": "能恩全护小红书达人种草",
        "brand": "能恩全护"
    },
    
    # 1.1 必须关键词
    "required_keywords": {
        "标题": ["适度水解", "防敏", "科普"],
        "正文": ["适度水解", "防敏", "能恩全护"],
    },
    
    # 1.2 禁词（分类）
    "forbidden_words": {
        "禁止词": ["敏宝", "奶瓶", "奶嘴", "新生儿", "过敏", "疾病"],
        "禁疗效表述": ["预防", "生长", "发育", "免疫"],
        "禁绝对化": ["最好", "最佳", "最优", "第一名", "TOP1", "top1", "No.1", "no.1"]
    },
    
    # 允许的例外（不算禁词）
    "allowed_exceptions": [
        "第一口奶粉", "第一口配方粉", "#第一口奶粉", "#第一口"
    ],
    
    # 1.3 不可改动卖点（必须精确匹配）
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
    
    # 1.4 结构要求
    "structure_requirements": {
        "正文字数上限": 900,
        "话题标签数量": 10,
    },
    
    # 1.5 必提Tag
    "required_tags": [
        "#能恩全护", "#能恩全护水奶", "#适度水解", 
        "#适度水解奶粉", "#适度水解奶粉推荐", "#防敏奶粉", 
        "#第一口奶粉", "#雀巢适度水解"
    ]
}

# 禁词替换建议
FORBIDDEN_SUGGESTIONS = {
    "敏宝": "敏感体质宝宝",
    "奶瓶": "喂养工具",
    "奶嘴": "喂养配件", 
    "新生儿": "初生宝宝",
    "过敏": "敏感/敏敏",
    "疾病": "不适",
    "预防": "远离/减少",
    "生长": "成长",
    "发育": "成长",
    "免疫": "保护力/自护力",
}


# ============================================
# 数据结构
# ============================================
@dataclass
class CheckItem:
    """单个检查项"""
    name: str
    passed: bool
    total: int = 0
    found: int = 0
    issues: List[str] = field(default_factory=list)
    details: List[Dict] = field(default_factory=list)


@dataclass
class ReviewReport:
    """审核报告"""
    kol_name: str
    version: str
    reviewer: str
    
    # 客观检查结果
    keyword_check: CheckItem = None
    forbidden_check: CheckItem = None
    selling_point_check: CheckItem = None
    structure_check: CheckItem = None
    tag_check: CheckItem = None
    
    # 主观检查结果（预留）
    professional_score: int = 0
    tone_score: int = 0
    natural_score: int = 0
    emotion_score: int = 0
    original_score: int = 0
    
    # 总分
    objective_score: float = 0.0
    subjective_score: float = 0.0
    total_score: float = 0.0
    
    # 好的地方
    good_points: List[str] = field(default_factory=list)

# ============================================
# 内容解析器
# ============================================
class ContentParser:
    def __init__(self, content: str):
        self.raw_content = content
        self.body_paragraphs: List[str] = []
        self.tags: List[str] = []
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
    def full_text(self) -> str:
        return self.raw_content
    
    @property
    def body_text(self) -> str:
        return '\n'.join(self.body_paragraphs)
    
    @property
    def word_count(self) -> int:
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', self.body_text)
        return len(chinese_chars)


# ============================================
# 审核引擎
# ============================================
def check_keywords(parser: ContentParser, rules: dict) -> CheckItem:
    """1.1 必须关键词检查"""
    required = rules.get('required_keywords', {})
    issues = []
    details = []
    total = 0
    found = 0
    
    for location, keywords in required.items():
        for kw in keywords:
            total += 1
            text = parser.full_text if location == "标题" else parser.body_text
            if kw in text:
                found += 1
                details.append({"keyword": kw, "location": location, "status": "✅"})
            else:
                issues.append(f"{location}缺少「{kw}」")
                details.append({"keyword": kw, "location": location, "status": "❌"})
    
    return CheckItem(
        name="必须关键词",
        passed=len(issues) == 0,
        total=total,
        found=found,
        issues=issues,
        details=details
    )


def check_forbidden(parser: ContentParser, rules: dict) -> CheckItem:
    """1.2 禁词检查（智能识别，排除例外）"""
    forbidden = rules.get('forbidden_words', {})
    exceptions = rules.get('allowed_exceptions', [])
    issues = []
    details = []
    
    full_text = parser.full_text
    
    for category, words in forbidden.items():
        for word in words:
            # 查找所有出现位置
            pattern = re.compile(re.escape(word))
            for match in pattern.finditer(full_text):
                start_idx = match.start()
                end_idx = match.end()
                
                # 获取上下文（前后各15个字符）
                context_start = max(0, start_idx - 15)
                context_end = min(len(full_text), end_idx + 15)
                context = full_text[context_start:context_end]
                
                # 检查是否在例外列表中
                is_exception = False
                for exc in exceptions:
                    if exc in context:
                        is_exception = True
                        break
                
                if not is_exception:
                    suggestion = FORBIDDEN_SUGGESTIONS.get(word, "请删除或改用其他表达")
                    issues.append(f"出现{category}「{word}」→ 建议改为「{suggestion}」")
                    details.append({
                        "word": word,
                        "category": category,
                        "context": f"...{context}...",
                        "suggestion": suggestion
                    })
    
    return CheckItem(
        name="禁词检查",
        passed=len(issues) == 0,
        total=len(issues) == 0,  # 0个问题=通过
        found=0,
        issues=issues,
        details=details
    )


def check_selling_points(parser: ContentParser, rules: dict) -> CheckItem:
    """1.3 不可改动卖点检查"""
    exact_points = rules.get('selling_points_exact', {})
    issues = []
    details = []
    total = 0
    found = 0
    
    for category, points in exact_points.items():
        for point in points:
            total += 1
            if point in parser.full_text:
                found += 1
                details.append({"point": point, "category": category, "status": "✅"})
            else:
                issues.append(f"[{category}] 缺少：{point[:20]}...")
                details.append({"point": point, "category": category, "status": "❌"})
    
    return CheckItem(
        name="不可改动卖点",
        passed=found == total,
        total=total,
        found=found,
        issues=issues,
        details=details
    )


def check_structure(parser: ContentParser, rules: dict) -> CheckItem:
    """1.4 结构完整性检查"""
    struct_req = rules.get('structure_requirements', {})
    issues = []
    details = []
    
    # 字数检查
    max_words = struct_req.get('正文字数上限', 900)
    word_count = parser.word_count
    if word_count > max_words:
        issues.append(f"字数超限：{word_count}字（上限{max_words}字）")
        details.append({"item": "字数", "value": word_count, "limit": max_words, "status": "❌"})
    else:
        details.append({"item": "字数", "value": word_count, "limit": max_words, "status": "✅"})
    
    # 标签数量检查
    required_tag_count = struct_req.get('话题标签数量', 10)
    tag_count = len(parser.tags)
    if tag_count < required_tag_count:
        issues.append(f"标签不足：{tag_count}个（要求{required_tag_count}个）")
        details.append({"item": "标签数量", "value": tag_count, "limit": required_tag_count, "status": "❌"})
    else:
        details.append({"item": "标签数量", "value": tag_count, "limit": required_tag_count, "status": "✅"})
    
    return CheckItem(
        name="结构完整性",
        passed=len(issues) == 0,
        total=2,
        found=2 - len(issues),
        issues=issues,
        details=details
    )


def check_tags(parser: ContentParser, rules: dict) -> CheckItem:
    """1.5 必提Tag检查"""
    required_tags = rules.get('required_tags', [])
    issues = []
    details = []
    found = 0
    
    for tag in required_tags:
        if tag in parser.tags:
            found += 1
            details.append({"tag": tag, "status": "✅"})
        else:
            issues.append(f"缺少必提标签：{tag}")
            details.append({"tag": tag, "status": "❌"})
    
    return CheckItem(
        name="必提Tag",
        passed=len(issues) == 0,
        total=len(required_tags),
        found=found,
        issues=issues,
        details=details
    )


def run_review(content: str, kol_name: str, version: str, reviewer: str) -> ReviewReport:
    """执行完整审核"""
    parser = ContentParser(content)
    rules = REVIEW_RULES
    
    report = ReviewReport(
        kol_name=kol_name,
        version=version,
        reviewer=reviewer
    )
    
    # 执行客观检查
    report.keyword_check = check_keywords(parser, rules)
    report.forbidden_check = check_forbidden(parser, rules)
    report.selling_point_check = check_selling_points(parser, rules)
    report.structure_check = check_structure(parser, rules)
    report.tag_check = check_tags(parser, rules)
    
    # 计算客观得分
    checks = [
        (report.keyword_check, 0.15),
        (report.forbidden_check, 0.20),
        (report.selling_point_check, 0.30),
        (report.structure_check, 0.15),
        (report.tag_check, 0.20),
    ]
    
    total_score = 0
    for check, weight in checks:
        if check.total > 0:
            score = check.found / check.total
        else:
            score = 1.0 if check.passed else 0.0
        total_score += score * weight
    
    report.objective_score = round(total_score * 100, 1)
    
    # 主观检查预留（暂时给默认分）
    report.professional_score = 80
    report.tone_score = 75
    report.natural_score = 70
    report.emotion_score = 75
    report.original_score = 85
    report.subjective_score = round((80 + 75 + 70 + 75 + 85) / 5, 1)
    
    # 总分（客观60% + 主观40%）
    report.total_score = round(report.objective_score * 0.6 + report.subjective_score * 0.4, 1)
    
    # 识别做得好的地方
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
    # ============================================
# Streamlit 网页界面
# ============================================
st.set_page_config(
    page_title="小红书KOL审稿系统",
    page_icon="🔍",
    layout="wide"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #ff6b6b, #ff8e53);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .check-pass { color: #10b981; font-weight: bold; }
    .check-fail { color: #ef4444; font-weight: bold; }
    .check-warn { color: #f59e0b; font-weight: bold; }
    .score-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">🔍 小红书KOL审稿系统</p>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: gray;">能恩全护 · 小红书达人种草项目 · v2.0 结构化审核</p>', unsafe_allow_html=True)

st.markdown("---")

# 版本信息
col1, col2 = st.columns(2)
with col1:
    st.info(f"📋 **审核规则版本**：{RULE_VERSION}")
with col2:
    st.info(f"📝 **Brief版本**：{BRIEF_VERSION}")

with st.expander("📖 点击查看完整Brief内容"):
    st.markdown(BRIEF_CONTENT)

st.markdown("---")

# 输入区域
col1, col2, col3 = st.columns(3)
with col1:
    kol_name = st.text_input("👤 KOL名称", placeholder="例如：小红薯妈妈")
with col2:
    version = st.selectbox("📌 版本号", ["V1", "V2", "V3", "V4", "V5", "FINAL"])
with col3:
    reviewer = st.selectbox("👁️ 审核方", ["赞意", "客户"])

st.markdown("### 📝 稿件内容")
content = st.text_area(
    "请粘贴KOL稿件内容（包含标题、正文、话题标签）",
    height=250,
    placeholder="粘贴稿件内容..."
)

if st.button("🔍 开始审核", type="primary", use_container_width=True):
    if not kol_name:
        st.error("请输入KOL名称")
    elif not content.strip():
        st.error("请粘贴稿件内容")
    else:
        with st.spinner("正在审核..."):
            report = run_review(content, kol_name, version, reviewer)
        
        st.markdown("---")
        
        # ==================== 审核报告头部 ====================
        st.markdown("## 📊 审核报告")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("KOL", f"@{report.kol_name}")
        with col2:
            st.metric("版本", report.version)
        with col3:
            st.metric("审核方", report.reviewer)
        with col4:
            if report.total_score >= 80:
                st.metric("综合评分", f"{report.total_score}% ✨")
            elif report.total_score >= 60:
                st.metric("综合评分", f"{report.total_score}% 👍")
            else:
                st.metric("综合评分", f"{report.total_score}% ⚠️")
        
        st.markdown("---")
        
        # ==================== 一、客观检查 ====================
        st.markdown("## 一、客观检查（硬性规则）")
        st.caption("以下检查项必须100%通过才算合格")
        
        # 1.1 必须关键词
        with st.expander(
            f"1.1 必须关键词 — {'✅ 全部通过' if report.keyword_check.passed else f'❌ {len(report.keyword_check.issues)}项未通过'}",
            expanded=not report.keyword_check.passed
        ):
            cols = st.columns(len(report.keyword_check.details))
            for i, detail in enumerate(report.keyword_check.details):
                with cols[i]:
                    st.markdown(f"{detail['status']} **{detail['keyword']}**")
                    st.caption(detail['location'])
            
            if report.keyword_check.issues:
                st.markdown("**需要修改：**")
                for issue in report.keyword_check.issues:
                    st.markdown(f"- {issue}")
        
        # 1.2 禁词检查
        with st.expander(
            f"1.2 禁词检查 — {'✅ 无违规' if report.forbidden_check.passed else f'❌ 发现{len(report.forbidden_check.issues)}处违规'}",
            expanded=not report.forbidden_check.passed
        ):
            if report.forbidden_check.passed:
                st.success("🎉 未发现禁词，非常好！")
            else:
                for detail in report.forbidden_check.details:
                    st.markdown(f"""
                    **❌ 禁词**：`{detail['word']}`（{detail['category']}）  
                    **上下文**：{detail['context']}  
                    **建议**：改为「{detail['suggestion']}」
                    """)
                    st.markdown("---")
        
        # 1.3 不可改动卖点
        with st.expander(
            f"1.3 不可改动卖点 — {'✅ 全部覆盖' if report.selling_point_check.passed else f'⚠️ {report.selling_point_check.found}/{report.selling_point_check.total} 已覆盖'}",
            expanded=not report.selling_point_check.passed
        ):
            # 按类别显示
            current_category = None
            for detail in report.selling_point_check.details:
                if detail['category'] != current_category:
                    current_category = detail['category']
                    st.markdown(f"**【{current_category}】**")
                
                status = detail['status']
                point = detail['point']
                if len(point) > 30:
                    st.markdown(f"{status} {point[:30]}...")
                else:
                    st.markdown(f"{status} {point}")
            
            if report.selling_point_check.issues:
                st.markdown("---")
                st.markdown("**缺失的卖点需要补充：**")
                for issue in report.selling_point_check.issues:
                    st.markdown(f"- {issue}")
        
        # 1.4 结构完整性
        with st.expander(
            f"1.4 结构完整性 — {'✅ 全部通过' if report.structure_check.passed else f'❌ {len(report.structure_check.issues)}项未通过'}",
            expanded=not report.structure_check.passed
        ):
            for detail in report.structure_check.details:
                status = detail['status']
                item = detail['item']
                value = detail['value']
                limit = detail['limit']
                
                if item == "字数":
                    st.markdown(f"{status} **{item}**：{value}字（上限{limit}字）")
                else:
                    st.markdown(f"{status} **{item}**：{value}个（要求≥{limit}个）")
        
        # 1.5 必提Tag
        with st.expander(
            f"1.5 必提Tag — {'✅ 全部包含' if report.tag_check.passed else f'❌ 缺少{len(report.tag_check.issues)}个'}",
            expanded=not report.tag_check.passed
        ):
            tag_cols = st.columns(4)
            for i, detail in enumerate(report.tag_check.details):
                with tag_cols[i % 4]:
                    st.markdown(f"{detail['status']} `{detail['tag']}`")
        
        # 客观检查得分
        st.markdown(f"### 📊 客观检查得分：**{report.objective_score}%**")
        
        st.markdown("---")
        
        # ==================== 二、主观检查 ====================
        st.markdown("## 二、主观检查（LLM评估）")
        st.caption("⏳ 此功能即将上线，以下为预留展示")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("专业身份呈现", f"{report.professional_score}分")
        with col2:
            st.metric("小红书调性", f"{report.tone_score}分")
        with col3:
            st.metric("卖点融入自然度", f"{report.natural_score}分")
        with col4:
            st.metric("情感共鸣度", f"{report.emotion_score}分")
        with col5:
            st.metric("原创性", f"{report.original_score}分")
        
        st.markdown(f"### 📊 主观检查得分：**{report.subjective_score}%**")
        
        st.markdown("---")
        
        # ==================== 三、综合评分 ====================
        st.markdown("## 三、综合评分")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div style="background:#f0f9ff; padding:15px; border-radius:10px; text-align:center;">
                <div style="color:#0369a1; font-size:14px;">客观检查（60%权重）</div>
                <div style="color:#0369a1; font-size:28px; font-weight:bold;">{report.objective_score}%</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div style="background:#fdf4ff; padding:15px; border-radius:10px; text-align:center;">
                <div style="color:#a21caf; font-size:14px;">主观检查（40%权重）</div>
                <div style="color:#a21caf; font-size:28px; font-weight:bold;">{report.subjective_score}%</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding:15px; border-radius:10px; text-align:center;">
                <div style="color:white; font-size:14px;">综合评分</div>
                <div style="color:white; font-size:28px; font-weight:bold;">{report.total_score}%</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # ==================== 四、做得好的地方 ====================
        if report.good_points:
            st.markdown("## ✅ 做得好的地方")
            for point in report.good_points:
                st.markdown(f"- {point}")
        
        # ==================== 五、审核总结 ====================
        st.markdown("## 📝 审核总结")
        
        if report.total_score >= 90:
            st.success("✨ **优秀**：稿件质量很高，稍作调整即可通过！")
        elif report.total_score >= 75:
            st.info("👍 **良好**：整体不错，请根据必改项进行修改。")
        elif report.total_score >= 60:
            st.warning("⚠️ **需改进**：存在较多问题，请仔细修改后重新提交。")
        else:
            st.error("❌ **需大改**：问题较多，建议参考Brief重新撰写。")
        
        # 下载报告
        report_text = f"""# 审核报告

## 基础信息
- KOL：@{report.kol_name}
- 版本：{report.version}
- 审核方：{report.reviewer}
- 审核时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}

## 评分
- 客观检查：{report.objective_score}%
- 主观检查：{report.subjective_score}%
- 综合评分：{report.total_score}%

## 客观检查详情

### 1.1 必须关键词（{report.keyword_check.found}/{report.keyword_check.total}）
"""
        for issue in report.keyword_check.issues:
            report_text += f"- ❌ {issue}\n"
        
        report_text += f"\n### 1.2 禁词检查\n"
        if report.forbidden_check.passed:
            report_text += "- ✅ 无违规\n"
        else:
            for issue in report.forbidden_check.issues:
                report_text += f"- ❌ {issue}\n"
        
        report_text += f"\n### 1.3 不可改动卖点（{report.selling_point_check.found}/{report.selling_point_check.total}）\n"
        for issue in report.selling_point_check.issues:
            report_text += f"- ❌ {issue}\n"
        
        report_text += f"\n### 1.4 结构完整性\n"
        for issue in report.structure_check.issues:
            report_text += f"- ❌ {issue}\n"
        
        report_text += f"\n### 1.5 必提Tag（{report.tag_check.found}/{report.tag_check.total}）\n"
        for issue in report.tag_check.issues:
            report_text += f"- ❌ {issue}\n"
        
        st.download_button(
            label="📥 下载审核报告",
            data=report_text,
            file_name=f"审核报告_{kol_name}_{version}.md",
            mime="text/markdown"
        )

# 页脚
st.markdown("---")
st.markdown(
    f'<p style="text-align: center; color: gray; font-size: 0.8rem;">'
    f'小红书KOL审稿系统 v2.0 | 审核规则：{RULE_VERSION} | Brief：{BRIEF_VERSION}'
    f'</p>', 
    unsafe_allow_html=True
)
