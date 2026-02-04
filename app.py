import streamlit as st
import re
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict

RULE_VERSION = "2026-02-04"
BRIEF_VERSION = "2026-02"

BRIEF_CONTENT = """
**核心卖点 (不可改动):**
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

@dataclass
class CheckResult:
    name: str
    passed: bool
    found: int = 0
    total: int = 0
    issues: List[str] = field(default_factory=list)

def parse_content(content):
    tags = re.findall(r'#[\w\u4e00-\u9fff]+', content)
    text = re.sub(r'#[\w\u4e00-\u9fff]+', '', content)
    word_count = len(re.findall(r'[\u4e00-\u9fff]', text))
    return {"text": content, "tags": tags, "word_count": word_count}

def run_review(content, kol, ver, reviewer):
    data = parse_content(content)
    results = {}
    
    # 1. Keywords
    kw_issues = []
    kw_found = 0
    for kw in REVIEW_RULES["required_keywords"]:
        if kw in data["text"]:
            kw_found += 1
        else:
            kw_issues.append(f"缺少: {kw}")
    results["keywords"] = CheckResult("必须关键词", len(kw_issues)==0, kw_found, len(REVIEW_RULES["required_keywords"]), kw_issues)
    
    # 2. Forbidden
    fb_issues = []
    exceptions = REVIEW_RULES["allowed_exceptions"]
    for cat, words in REVIEW_RULES["forbidden_words"].items():
        for w in words:
            if w in data["text"]:
                ctx = data["text"][max(0,data["text"].find(w)-10):data["text"].find(w)+len(w)+10]
                if not any(e in ctx for e in exceptions):
                    sug = SUGGESTIONS.get(w, "删除")
                    fb_issues.append(f"{cat} [{w}] -> {sug}")
    results["forbidden"] = CheckResult("禁词检查", len(fb_issues)==0, 0, 0, fb_issues)
    
    # 3. Selling points
    sp_issues = []
    sp_found = 0
    for sp in REVIEW_RULES["selling_points"]:
        if sp in data["text"]:
            sp_found += 1
        else:
            sp_issues.append(f"缺少: {sp[:20]}...")
    results["selling"] = CheckResult("不可改动卖点", sp_found==len(REVIEW_RULES["selling_points"]), sp_found, len(REVIEW_RULES["selling_points"]), sp_issues)
    
    # 4. Structure
    st_issues = []
    if data["word_count"] > REVIEW_RULES["max_words"]:
        st_issues.append(f"字数超限: {data['word_count']}/{REVIEW_RULES['max_words']}")
    if len(data["tags"]) < REVIEW_RULES["min_tags"]:
        st_issues.append(f"标签不足: {len(data['tags'])}/{REVIEW_RULES['min_tags']}")
    results["structure"] = CheckResult("结构完整性", len(st_issues)==0, 0, 0, st_issues)
    
    # 5. Tags
    tg_issues = []
    tg_found = 0
    for t in REVIEW_RULES["required_tags"]:
        if t in data["tags"]:
            tg_found += 1
        else:
            tg_issues.append(f"缺少: {t}")
    results["tags"] = CheckResult("必提Tag", len(tg_issues)==0, tg_found, len(REVIEW_RULES["required_tags"]), tg_issues)
    
    # Score
    score = 0
    weights = [("keywords", 0.15), ("forbidden", 0.20), ("selling", 0.30), ("structure", 0.15), ("tags", 0.20)]
    for key, w in weights:
        r = results[key]
        if r.total > 0:
            score += (r.found / r.total) * w * 100
        else:
            score += (100 if r.passed else 0) * w
    
    return {"kol": kol, "ver": ver, "reviewer": reviewer, "results": results, "score": round(score, 1), "word_count": data["word_count"], "tag_count": len(data["tags"])}

st.set_page_config(page_title="小红书KOL审稿系统", page_icon="🔍", layout="wide")
st.markdown("<h1 style='text-align:center;color:#ff6b6b;'>🔍 小红书KOL审稿系统 v2.0</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:gray;'>能恩全护 - 结构化审核</p>", unsafe_allow_html=True)
st.markdown("---")

c1, c2 = st.columns(2)
c1.info(f"📋 审核规则: {RULE_VERSION}")
c2.info(f"📝 Brief: {BRIEF_VERSION}")

with st.expander("📖 查看Brief内容"):
    st.markdown(BRIEF_CONTENT)

st.markdown("---")

c1, c2, c3 = st.columns(3)
kol = c1.text_input("👤 KOL名称", placeholder="例如: 小红薯妈妈")
ver = c2.selectbox("📌 版本", ["V1", "V2", "V3", "FINAL"])
reviewer = c3.selectbox("👁️ 审核方", ["赞意", "客户"])

content = st.text_area("📝 稿件内容", height=250, placeholder="粘贴稿件...")

if st.button("🔍 开始审核", type="primary", use_container_width=True):
    if not kol or not content.strip():
        st.error("请填写KOL名称和稿件内容")
    else:
        r = run_review(content, kol, ver, reviewer)
        
        st.markdown("---")
        st.markdown("## 📊 审核报告")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("KOL", f"@{r['kol']}")
        c2.metric("版本", r['ver'])
        c3.metric("审核方", r['reviewer'])
        c4.metric("综合评分", f"{r['score']}%")
        
        st.markdown("---")
        st.markdown("## 一、客观检查")
        
        checks = [
            ("1.1 必须关键词", "keywords"),
            ("1.2 禁词检查", "forbidden"),
            ("1.3 不可改动卖点", "selling"),
            ("1.4 结构完整性", "structure"),
            ("1.5 必提Tag", "tags")
        ]
        
        for title, key in checks:
            res = r["results"][key]
            status = "✅通过" if res.passed else f"❌{len(res.issues)}项问题"
            if res.total > 0:
                status = f"{'✅' if res.passed else '⚠️'} {res.found}/{res.total}"
            
            with st.expander(f"{title} - {status}", expanded=not res.passed):
                if res.passed:
                    st.success("通过")
                else:
                    for issue in res.issues:
                        st.warning(issue)
        
        st.markdown("---")
        st.markdown("## 二、审核总结")
        
        if r["score"] >= 90:
            st.success("✨ 优秀!")
        elif r["score"] >= 70:
            st.info("👍 良好")
        elif r["score"] >= 50:
            st.warning("⚠️ 需改进")
        else:
            st.error("❌ 需大改")
        
        st.caption(f"字数: {r['word_count']} | 标签: {r['tag_count']}个")

st.markdown("---")
st.caption(f"v2.0 | {RULE_VERSION}")
