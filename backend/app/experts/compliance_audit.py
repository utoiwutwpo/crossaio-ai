"""
一键合规体检（Compliance Audit）— GPSR 付费闭环的核心引擎。

针对的市场事实（2024-2025）：
- GPSR (EU 2023/988) 2024-12-13 起强制执行，2026 年进入全面强执法（800+ 条款）；
- 平台（Amazon/eBay/bol/Kaufland 等）已把欧代校验设为上架前置条件，缺资料直接
  失购物车 / 屏蔽搜索 / 强制下架；
- 15%-20% 中小卖家因合规门槛退出欧洲 —— 本模块把「合规体检 → 欧代标注 →
  技术文件清单 → 当地语言警示语包」做成一次调用可交付的闭环。

与既有模块的关系（不重复造轮子）：
- gpsr.py          → 品类识别 / CE 判定 / 法定检查清单 / 合规块
- eu_rep.py        → 欧代台账（真实数据，不再用占位符）
- platform_rules.py→ 平台原生规则卡 / 平台原生合规块
- safety_gate.py   → 安全词库（事故上报协议）

免费/付费切分（付费墙）：
- 免费：风险等级 + 缺项数量 + 就绪分 + 平台规则卡 —— 只报问题不给答案；
- Starter+：解锁 欧代标注行（含标注位置指引）+ 技术文件清单（10 年存档）
  + 当地语言警示语包 + 平台原生合规块。

零 LLM 依赖（确定性规则）。
"""
from typing import Dict, List, Optional

from . import gpsr
from . import platform_rules
from . import safety_gate


# GPSR (EU 2023/988) 技术文件清单 —— Art.9(2)：量产后动态更新，保存 10 年。
# 每项给卖家「该准备什么 + 保存多久 + 监管多久内要拿出来」。
TECH_FILE_CHECKLIST: List[Dict] = [
    {"item": "product_description", "name": "产品描述与规格",
     "detail": "产品类型、型号、功能、材质、预期用途与合理可预见滥用",
     "retention": "10 年", "deadline": "上架前"},
    {"item": "risk_assessment", "name": "风险评估报告",
     "detail": "按产品类目逐项识别危害（机械/化学/电气/窒息…）并评估等级与缓解措施",
     "retention": "10 年", "deadline": "量产后动态更新"},
    {"item": "bom_supplier", "name": "物料清单与供应商信息",
     "detail": "关键部件/材料的来源，支撑 48 小时内全链路追溯要求",
     "retention": "6 年（供应链追溯）", "deadline": "监管问询 48 小时内可提供"},
    {"item": "test_reports", "name": "检测报告与证书",
     "detail": "CE 类目对应指令的测试报告（EN 71 / RED / LVD / EMC…）",
     "retention": "10 年", "deadline": "平台/监管要求时随时出示"},
    {"item": "labels_manual", "name": "标签样张与当地语言说明书",
     "detail": "产品/包装实拍标签 + 目标市场官方语言警示语与说明书",
     "retention": "10 年", "deadline": "上架前"},
    {"item": "batch_traceability", "name": "批次追溯记录",
     "detail": "型号/批次/序列号与进销存对应关系，支持精准召回",
     "retention": "6 年", "deadline": "监管问询 48 小时内可提供"},
    {"item": "dof_declaration", "name": "符合性声明（DoC）",
     "detail": "CE 类目：制造商签署的 EU Declaration of Conformity",
     "retention": "10 年", "deadline": "平台要求 7-14 天内补交，否则下架"},
    {"item": "eu_rep_agreement", "name": "欧代任命协议",
     "detail": "欧盟责任人的书面任命（不可倒签，责任自首次投放市场起算）",
     "retention": "10 年", "deadline": "首次投放欧盟市场前"},
]

# 欧代标注位置指引 —— GPSR 要求产品本体/包装/随附文件三者「统一」展示欧代信息。
REP_MARKING_PLACES = [
    ("product", "产品本体", "刻印/丝印/铭牌（电子类目常见于机身底部）"),
    ("packaging", "外包装", "印刷在销售包装可视面，与制造商信息并列"),
    ("listing", "Listing 详情页", "合规块（本工具自动生成）+ 平台合规字段双写入"),
]


def _rep_marking(eu_rep: Optional[Dict], rep_line: str) -> Dict:
    """欧代标注包：标注行 + 三处标注位置指引。欧代未配置时如实标注缺失。"""
    configured = bool(eu_rep)
    return {
        "configured": configured,
        "rep_line": rep_line if configured else "",
        "placeholder": None if configured else "[欧代公司名称], [欧代地址], [联系邮箱]",
        "marking_places": [
            {"place": key, "label": label, "how": how}
            for key, label, how in REP_MARKING_PLACES
        ],
        "note": ("欧代信息来自你的欧代台账（默认欧代），产品本体/包装/Listing 三处"
                 "必须统一展示同一条欧代信息。" if configured else
                 "尚未配置欧代：先在工作台「欧代台账」添加并设为默认，"
                 "体检报告将自动嵌入真实欧代信息。"),
    }


def _tech_file_status(categories: List[Dict], eu_rep: Optional[Dict]) -> List[Dict]:
    """技术文件清单 + 按当前输入的即时状态提示（哪些项现在就该着手）。"""
    rows = [dict(r) for r in TECH_FILE_CHECKLIST]
    ce = any(r["risk"] == "high" for r in categories)
    for r in rows:
        r["priority"] = "P0"
        if r["item"] == "dof_declaration" and not ce:
            r["priority"] = "P2"
            r["detail"] += "（当前未识别到 CE 类目，暂可降级）"
        if r["item"] == "eu_rep_agreement" and not eu_rep:
            r["detail"] += "（⚠️ 你还没有配置欧代）"
    return rows


def _warnings_pack(categories: List[Dict], languages: List[str]) -> List[Dict]:
    """当地语言警示语包：每种必需语言 × 每个命中类目的一段可粘贴警示语。"""
    pack = []
    for lang in languages:
        header = gpsr.LANG_HEADER.get(lang, gpsr.LANG_HEADER["en"])
        lines = []
        for rule in categories:
            w = rule["warnings"].get(lang) or rule["warnings"]["en"] + " (EN)"
            lines.append(w)
        if not lines:
            lines.append("This product complies with the EU General Product Safety "
                         "Regulation (EU 2023/988). Read the instructions before use.")
        pack.append({"lang": lang, "header": header, "lines": lines})
    return pack


def _gaps(eu_rep: Optional[Dict], categories: List[Dict],
          ce_required: bool, languages: List[str]) -> List[Dict]:
    """缺项清单（免费层可见的核心价值：知道自己差什么，但不给答案）。"""
    gaps = []
    if not eu_rep:
        gaps.append({"item": "eu_responsible_person", "severity": "critical",
                     "label": "未配置欧代（欧盟授权代表）",
                     "consequence": "平台前置校验直接拦截：失去购物车 / 屏蔽搜索 / 强制下架"})
    if ce_required:
        gaps.append({"item": "dof_declaration", "severity": "high",
                     "label": "符合性声明（DoC）待确认",
                     "consequence": "平台要求 7-14 天内补交，逾期 ASIN 级下架"})
    if categories:
        gaps.append({"item": "safety_warnings_local", "severity": "high",
                     "label": f"当地语言警示语待部署（{len(languages)} 种语言）",
                     "consequence": "警示语语言不符 = 标签违规，海关/平台双重拦截"})
    else:
        gaps.append({"item": "general_safety_info", "severity": "medium",
                     "label": "未识别到受监管类目，但 GPSR 一般安全要求仍适用",
                     "consequence": "仍需欧代 + 当地语言安全信息（Art.9 基本义务）"})
    gaps.append({"item": "tech_file", "severity": "medium",
                 "label": "技术文件档案待建立（8 项，保存 10 年）",
                 "consequence": "监管问询 48 小时内无法提供全链路记录将被处罚"})
    return gaps


def _readiness_score(eu_rep: Optional[Dict], ce_required: bool,
                     categories: List[Dict]) -> int:
    """合规就绪分 0-100：欧代 40 + 类目风险控制 30 + 技术文件 30。"""
    score = 0
    if eu_rep:
        score += 40
    if not ce_required:
        score += 20
    elif categories:
        score += 8   # 有 CE 类目但需 DoC/测试报告，扣减
    score += 30      # 技术文件按「生成清单即具备建档路径」给基础分
    return min(score, 100)


def run_audit(platform: str, product_name: str, keywords: List[str],
              eu_rep: Optional[Dict], rep_line: str = "",
              full: bool = True) -> Dict:
    """一键体检主入口（确定性输出）。

    eu_rep / rep_line 来自欧代台账（experts.eu_rep）。
    full=False → 免费版：只给风险摘要 + 缺项 + 就绪分 + 平台规则卡。
    """
    check = gpsr.check(product_name, keywords, platform,
                       eu_rep_line=rep_line if eu_rep else "")
    categories = gpsr.detect_categories(product_name, keywords)
    languages = check["required_languages"]
    ce_required = check["ce_required"]

    gaps = _gaps(eu_rep, categories, ce_required, languages)
    score = _readiness_score(eu_rep, ce_required, categories)

    report: Dict = {
        "platform": platform,
        "product_name": product_name,
        "risk_level": check["risk_level"],
        "ce_required": ce_required,
        "matched_categories": check["matched_categories"],
        "ce_directives": check["ce_directives"],
        "required_languages": languages,
        "compliance_score": score,
        "critical_gap_count": sum(1 for g in gaps if g["severity"] == "critical"),
        "gaps": gaps,
        "platform_card": platform_rules.platform_rules_card(platform),
        "safety_gate_protocol": {
            "window": "15 天",
            "rule": "GPSR (EU 2023/988) Art.35：确认产品存在安全风险后 15 天内"
                    "经 EU Safety Gate 门户上报",
            "keywords_hint": safety_gate.safety_keywords_hint()[:6],
        },
        "disclaimer": "本报告为工程辅助建议，不能替代法律意见；"
                      "具体类目适用指令以欧盟官方文本与认证机构意见为准。",
    }

    if full:
        report["rep_marking"] = _rep_marking(eu_rep, rep_line)
        report["tech_file_checklist"] = _tech_file_status(categories, eu_rep)
        report["warnings_pack"] = _warnings_pack(categories, languages)
        report["gpsr_block"] = check["gpsr_block"]
        if platform_rules.has_native_rules(platform):
            rep_dict = None
            if eu_rep:
                rep_dict = {"company_name": eu_rep.get("company_name", ""),
                            "address": eu_rep.get("address", ""),
                            "email": eu_rep.get("email", "")}
            nb = platform_rules.native_compliance_block(
                platform, product_name, keywords, eu_rep=rep_dict)
            report["native_block"] = nb
    return report
