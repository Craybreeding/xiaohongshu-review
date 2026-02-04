
小红书KOL审稿Agent - 网页版
基于 Streamlit 构建
"""
import streamlit as st
import re
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


# ============================================
# 版本信息
# ============================================
RULE_VERSION = "2026年2月4日"
BRIEF_VERSION = "2026年2月版"

# Brief内容
BRIEF_CONTENT = """
### Storyline：

1、以营养/育婴师等专业身份背景出发，收到很多妈妈咨询想带娃出去玩耍，又怕宝宝因户外环境导致敏敏的痛点出发，引出中国初生宝宝敏敏发生率高达40%，点出【宝宝敏敏具体原因】家族遗传史（父母双方都敏感，宝宝敏敏概率飙升到80%）、都是敏感高发的原因，再加上换季户外敏感源增多，宝宝敏感更加严重。

2、分享科学防敏攻略（E.g 常见致敏原因、户外日常防敏攻略）喂养方面强调第一口选奶对提前防敏的重要性，建议可以选择低敏的适度水解配方粉来作为宝宝的第一口配方粉。

3、从品牌实力、水解技术、加强配方、基础配方、粉质、口感等角度介绍产品，综合得出能恩全护是防敏奶粉中的顶配，突出（防敏+自护+长肉）三重喂养实力。

4、主题强化：呼吁宝爸宝妈，想带娃户外肆意玩耍，选对第一口奶粉是关键，建议优选能恩全护。

### 封面注意点：

1、背景文献图封面产品可不出镜，需着重强调第一口防敏科普内容，排版需有创新性

2、需包含"第一口（奶粉）"，"防敏" 关键词

3、不能出现"敏宝"相关文字

4、封面整体风格贴合博主自身主页调性，金色调/有金色元素，画面排版需要体现精致+高级

### 卖点描述（蓝字部分不能改动，黄色字可删减）

**1、敏敏现状：** 我国初生宝宝敏敏率高达40%，要是有父母敏敏史，宝宝敏敏的概率将飙升到80%

**2、专业人士建议：** 不少专业人士建议，可以给宝宝选择适度水解配方粉作为宝宝的第一口配方粉

**3、防敏卖点------水解技术+超多实证：** 拥有多项科学实证的雀巢尖峰水解科技，防敏领域权威德国GINI研究认证，能长效防敏20年，相比于牛奶蛋白致敏性降低1000倍

**4、保护力卖点------超倍自护科技：** 全球创新的超倍自护科技，6种HMO加上明星双菌B.Infantis和Bb-12，协同作用释放高倍的原生保护力，短短28天就能调理好娃的肚肚菌菌环境，保护力能持续15个月

**5、基础营养&口感：** 25种维生素和矿物质，全乳糖的配方口味清淡
"""


class Severity(Enum):
    MUST_FIX = "必改"
    SUGGEST = "建议"


@dataclass
class ReviewIssue:
    category: str
    severity: Severity
    location: str
    original_text: str
    problem: str
    suggestion: str


@dataclass
class ReviewResult:
    project_name: str
    kol_name: str
    version: str
    reviewer: str
    must_fix_issues: List[ReviewIssue] = field(default_factory=list)
    suggest_issues: List[ReviewIssue] = field(default_factory=list)
    good_points: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    total_score: float = 0.0


REVIEW_RULES = {
    "project_info": {
        "name": "能恩全护小红书达人种草",
        "brand": "能恩全护"
    },
    "required_keywords": {
        "标题": ["适度水解", "防敏", "科普"],
        "正文": ["适度水解", "防敏", "能恩全护"],
    },
    "forbidden_words": {
        "禁止词": ["敏宝", "奶瓶", "奶嘴", "新生儿", "过敏", "疾病"],
        "禁疗效表述": ["预防", "生长", "发育", "免疫"],
        "禁绝对化": ["最", "第一", "TOP1", "top1", "No.1", "no.1"]
    },
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
    "structure_requirements": {
        "正文字数上限": 900,
        "话题标签数量": 10,
        "必提tag": [
            "#能恩全护", "#能恩全护水奶", "#适度水解", 
            "#适度水解奶粉", "#适度水解奶粉推荐", "#防敏奶粉", 
            "#第一口奶粉", "#雀巢适度水解"
        ]
    },
    "scoring_weights": {
        "关键词检查": 0.15,
        "禁词检查": 0.20,
        "卖点覆盖": 0.30,
        "结构完整性": 0.20,
        "口吻风格": 0.15
    }
}

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
    "最": "非常/特别",
    "第一": "领先/优秀",
}


class ContentParser:
    def __init__(self, content: str):
        self.raw_content = content
        self.titles: List[str] = []
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
            else:
                self.body_paragraphs.append(line)
    
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


def review_content(content: str, kol_name: str, version: str, reviewer: str) -> ReviewResult:
    result = ReviewResult(
        project_name=REVIEW_RULES["project_info"]["name"],
        kol_name=kol_name,
        version=version,
        reviewer=reviewer
    )
    
    parser = ContentParser(content)
    rules = REVIEW_RULES
    
    # 1. 检查必须关键词
    required = rules.get('required_keywords', {})
    for keyword in required.get('正文', []):
        if keyword not in parser.body_text:
            result.must_fix_issues.append(ReviewIssue(
                category="关键词缺失",
                severity=Severity.MUST_FIX,
                location="正文",
                original_text="",
                problem=f"正文缺少必须关键词「{keyword}」",
                suggestion=f"请在正文中加入「{keyword}」"
            ))
    
    # 2. 检查禁词
    forbidden = rules.get('forbidden_words', {})
    for category, words in forbidden.items():
        for word in words:
            if word in parser.full_text:
                idx = parser.full_text.find(word)
                start = max(0, idx - 10)
                end = min(len(parser.full_text), idx + len(word) + 10)
                context = parser.full_text[start:end]
                
                suggestion = FORBIDDEN_SUGGESTIONS.get(word, "请删除或改用其他表达")
                if word in FORBIDDEN_SUGGESTIONS:
                    suggestion = f"建议改为「{FORBIDDEN_SUGGESTIONS[word]}」"
                
                result.must_fix_issues.append(ReviewIssue(
                    category="禁词违规",
                    severity=Severity.MUST_FIX,
                    location="正文",
                    original_text=f"...{context}...",
                    problem=f"出现{category}「{word}」",
                    suggestion=suggestion
                ))
    
    # 3. 检查精确卖点
    exact_points = rules.get('selling_points_exact', {})
    found_count = 0
    total_count = 0
    
    for category, points in exact_points.items():
        for point in points:
            total_count += 1
            if point in parser.full_text:
                found_count += 1
            else:
                result.must_fix_issues.append(ReviewIssue(
                    category="卖点缺失",
                    severity=Severity.MUST_FIX,
                    location="正文",
                    original_text="",
                    problem=f"缺少必须卖点（{category}）",
                    suggestion=f"请加入原文：「{point}」"
                ))
    
    result.scores['卖点覆盖'] = found_count / total_count if total_count > 0 else 1.0
    
    # 4. 检查结构
    struct_req = rules.get('structure_requirements', {})
    
    max_words = struct_req.get('正文字数上限', 900)
    if parser.word_count > max_words:
        result.must_fix_issues.append(ReviewIssue(
            category="结构问题",
            severity=Severity.MUST_FIX,
            location="正文",
            original_text=f"当前：{parser.word_count}字",
            problem=f"字数超限（上限{max_words}字）",
            suggestion=f"请精简内容，删减{parser.word_count - max_words}字"
        ))
    
    required_tags = struct_req.get('话题标签数量', 10)
    if len(parser.tags) < required_tags:
        result.suggest_issues.append(ReviewIssue(
            category="结构问题",
            severity=Severity.SUGGEST,
            location="话题标签",
            original_text=f"当前：{len(parser.tags)}个",
            problem=f"标签数量不足（要求{required_tags}个）",
            suggestion=f"请补充{required_tags - len(parser.tags)}个话题标签"
        ))
    
    required_tags_list = struct_req.get('必提tag', [])
    missing_tags = [tag for tag in required_tags_list if tag not in parser.tags]
    if missing_tags:
        result.must_fix_issues.append(ReviewIssue(
            category="结构问题",
            severity=Severity.MUST_FIX,
            location="话题标签",
            original_text=f"缺少：{', '.join(missing_tags[:3])}{'...' if len(missing_tags) > 3 else ''}",
            problem=f"缺少{len(missing_tags)}个必提标签",
            suggestion=f"请加入：{', '.join(missing_tags)}"
        ))
    
    # 5. 检查口吻
    professional_keywords = ['营养师', '育婴师', '博士', '硕士', '专业']
    has_professional = any(kw in parser.full_text for kw in professional_keywords)
    
    if not has_professional:
        result.suggest_issues.append(ReviewIssue(
            category="口吻问题",
            severity=Severity.SUGGEST,
            location="全文",
            original_text="",
            problem="未明确体现专业人士身份",
            suggestion="建议在开头明确身份，如「作为持证营养师」「育婴师建议」等"
        ))
    
    # 计算得分
    keyword_issues = len([i for i in result.must_fix_issues if '关键词' in i.category])
    forbidden_issues = len([i for i in result.must_fix_issues if '禁词' in i.category])
    structure_issues = len([i for i in result.must_fix_issues if '结构' in i.category])
    
    result.scores['关键词检查'] = max(0, 1 - keyword_issues * 0.2)
    result.scores['禁词检查'] = max(0, 1 - forbidden_issues * 0.2)
    result.scores['结构完整性'] = max(0, 1 - structure_issues * 0.25)
    result.scores['口吻风格'] = 1.0 if has_professional else 0.7
    
    weights = rules.get('scoring_weights', {})
    total = 0
    for key, weight in weights.items():
        score = result.scores.get(key, 0.5)
        total += score * weight
    result.total_score = round(total * 100, 1)
    
    if has_professional:
        result.good_points.append("专业身份明确")
    if result.scores.get('卖点覆盖', 0) > 0.5:
        result.good_points.append("核心卖点有覆盖")
    if parser.word_count <= max_words:
        result.good_points.append(f"字数控制合理（{parser.word_count}字）")
    
    return result


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
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">🔍 小红书KOL审稿系统</p>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: gray;">能恩全护 · 小红书达人种草项目</p>', unsafe_allow_html=True)

st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    st.markdown("### 📋 当前审核规则")
    st.info(f"✅ 已上传审核规则：**{RULE_VERSION}**")
with col2:
    st.markdown("### 📝 当前Brief")
    st.info(f"✅ 已上传达人Brief：**{BRIEF_VERSION}**")

with st.expander("📖 点击查看完整Brief内容"):
    st.markdown(BRIEF_CONTENT)

st.markdown("---")

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
    height=300,
    placeholder="粘贴稿件内容..."
)

if st.button("🔍 开始审核", type="primary", use_container_width=True):
    if not kol_name:
        st.error("请输入KOL名称")
    elif not content.strip():
        st.error("请粘贴稿件内容")
    else:
        with st.spinner("正在审核..."):
            result = review_content(content, kol_name, version, reviewer)
        
        st.markdown("---")
        st.markdown("## 📊 审核报告")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("KOL", f"@{result.kol_name}")
        with col2:
            st.metric("版本", result.version)
        with col3:
            st.metric("审核方", result.reviewer)
        with col4:
            score = result.total_score
            if score >= 80:
                st.metric("综合评分", f"{score}% ✨")
            elif score >= 60:
                st.metric("综合评分", f"{score}% 👍")
            else:
                st.metric("综合评分", f"{score}% ⚠️")
        
        st.markdown("### 📈 各项得分")
        score_cols = st.columns(len(result.scores))
        for i, (key, score) in enumerate(result.scores.items()):
            with score_cols[i]:
                score_pct = round(score * 100)
                emoji = "✅" if score_pct >= 80 else "⚠️" if score_pct >= 60 else "❌"
                st.metric(key, f"{emoji} {score_pct}%")
        
        st.markdown("### ❌ 必改项")
        if result.must_fix_issues:
            for i, issue in enumerate(result.must_fix_issues, 1):
                with st.expander(f"{i}. 【{issue.category}】{issue.location}", expanded=True):
                    if issue.original_text:
                        st.markdown(f"**原文**：`{issue.original_text}`")
                    st.markdown(f"**问题**：{issue.problem}")
                    st.success(f"**建议**：{issue.suggestion}")
        else:
            st.success("🎉 没有必改项！")
        
        st.markdown("### 💡 建议优化")
        if result.suggest_issues:
            for i, issue in enumerate(result.suggest_issues, 1):
                with st.expander(f"{i}. 【{issue.category}】{issue.location}"):
                    st.markdown(f"**问题**：{issue.problem}")
                    st.info(f"**建议**：{issue.suggestion}")
        else:
            st.info("暂无优化建议")
        
        st.markdown("### ✅ 做得好的地方")
        for point in result.good_points:
            st.markdown(f"- {point}")
        
        st.markdown("### 📝 审核总结")
        if result.total_score >= 90:
            st.success("✨ **优秀**：稿件质量很高，稍作调整即可通过！")
        elif result.total_score >= 75:
            st.info("👍 **良好**：整体不错，请根据必改项进行修改。")
        elif result.total_score >= 60:
            st.warning("⚠️ **需改进**：存在较多问题，请仔细修改后重新提交。")
        else:
            st.error("❌ **需大改**：问题较多，建议参考brief重新撰写。")
        
        report_text = f"""# 审核报告
## 基础信息
- 项目：{result.project_name}
- KOL：@{result.kol_name}
- 版本：{result.version}
- 审核方：{result.reviewer}
- 综合评分：{result.total_score}%
- 审核时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
- 审核规则版本：{RULE_VERSION}
- Brief版本：{BRIEF_VERSION}

## 必改项（{len(result.must_fix_issues)}条）
"""
        for i, issue in enumerate(result.must_fix_issues, 1):
            report_text += f"\n{i}. 【{issue.category}】{issue.location}\n"
            report_text += f"   问题：{issue.problem}\n"
            report_text += f"   建议：{issue.suggestion}\n"
        
        st.download_button(
            label="📥 下载审核报告",
            data=report_text,
            file_name=f"审核报告_{kol_name}_{version}.md",
            mime="text/markdown"
        )

st.markdown("---")
st.markdown(
    f'<p style="text-align: center; color: gray; font-size: 0.8rem;">'
    f'小红书KOL审稿系统 v1.0 | 审核规则：{RULE_VERSION} | Brief：{BRIEF_VERSION}'
    f'</p>', 
    unsafe_allow_html=True
)
