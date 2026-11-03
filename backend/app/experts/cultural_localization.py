"""
文化本地化引擎（Cultural Localization）— 从「机翻 + 模板」升级为「按市场改写」。

市场依据：
- 76% 买家偏好母语商品信息，40% 直接拒绝非母语页面（CSA Research）；
- 逐字机翻在德/法/意市场转化显著低于母语文案（GuruXO 2025 EU 指南）；
- 各市场买家决策要素顺序不同：
  · 德国：认证与安全（TÜV/GS/CE）→ 技术参数精确性 → 材质与做工 → 保修；
  · 法国：生活场景与美学 → 保修与售后（SAV）→ 性价比 → 法语严谨性（Loi Toubon）；
  · 意大利：设计与视觉 → 家庭场景 → 情感共鸣 → 性价比；
  · 西班牙：家庭与热情场景 → 性价比 → 促销敏感；
  · 波兰：配送时效（Allegro Smart）→ 性价比 → 退货便利；
  · 荷兰：Delivery Promise → 直白务实（无营销套话）→ 可持续性；
  · 罗马尼亚：性价比 → 耐用性 → 配送确定性。

两个输出：
1. cultural_prompt_block()：注入 LLM prompt 的市场改写指令（生成侧生效）；
2. score_cultural_fit()：对生成结果做确定性文化适配评分（校验侧生效）。

零 LLM 依赖（本模块本身确定性；LLM 调用由 product_description 完成）。
"""
from typing import Dict, List, Optional

# 每个市场的买家画像与改写规则。key = 语言代码（与 platform_registry 的 language 对齐）。
MARKET_PROFILES: Dict[str, Dict] = {
    "de": {
        "market": "德国 (DE/AT)",
        "buyer_priorities": ["认证与安全背书", "技术参数精确", "材质与做工", "保修与售后", "环保回收"],
        "trust_signals": ["CE", "TÜV", "GS", "Prüfzeichen", "Garantie", "Schadstoffgeprüft"],
        "bullet_formula": "参数精确（带数值/单位）→ 认证安全 → 材质做工 → 保修条款 → 环保回收",
        "tone": "严谨克制，杜绝营销套话与绝对化用语（德国用户对夸张文案反感）",
        "avoid": ["best", "weltbeste", "Wunder", "magisch", "100% sicher",
                  "super", "mega", "!"*3],
        "donot": "数值必须带公制单位；保修以年为单位写明（如 2 Jahre Garantie）；"
                 "不要用感叹号堆叠情绪",
        "local_hint": "技术词用德语原词（Anschluss, Lieferumfang, Abmessungen），"
                      "不夹杂英语口语",
    },
    "fr": {
        "market": "法国 (FR)",
        "buyer_priorities": ["生活场景与美学", "保修与售后（SAV）", "性价比", "法语严谨性"],
        "trust_signals": ["Garantie", "SAV", "Norme CE", "Fabrication", "Livraison"],
        "bullet_formula": "生活场景描绘（优雅/格调）→ 核心功能 → 材质与设计感 → "
                          "保修与 SAV 承诺 → 退换便利",
        "tone": "优雅流畅，重叙事与场景，比德语市场更有情感温度",
        "avoid": ["best", "cheap", "no.1", "incroyable", "révolutionnaire"],
        "donot": "全法语，禁英语混杂（Loi Toubon 法案要求）；保修写作「Garantie X ans」",
        "local_hint": "场景用法国生活意象（apéritif、salon、 WEEK-END 前准备…按品类取用）",
    },
    "it": {
        "market": "意大利 (IT)",
        "buyer_priorities": ["设计与视觉", "家庭场景", "情感共鸣", "性价比"],
        "trust_signals": ["Garanzia", "Design italiano", "CE", "Qualità"],
        "bullet_formula": "设计感与视觉冲击 → 家庭使用场景 → 情感价值（分享/款待）→ "
                          "核心功能 → 性价比",
        "tone": "热情有画面感，允许适度形容词堆叠（与德语市场相反）",
        "avoid": ["best", "cheap", "top quality 100%"],
        "donot": "多用具体画面而非抽象参数；家庭与待客场景优先于单人效率场景",
        "local_hint": "意语形容词要与名词性数一致；场景围绕 famiglia / cucina / casa",
    },
    "es": {
        "market": "西班牙 (ES)",
        "buyer_priorities": ["家庭与社交场景", "性价比", "促销敏感", "售后"],
        "trust_signals": ["Garantía", "CE", "Envío rápido", "Devolución gratis"],
        "bullet_formula": "家庭/社交场景 → 核心功能 → 性价比 → 促销与保障 → 售后",
        "tone": "热情直接，促销信息可明示（西班牙买家对价格敏感）",
        "avoid": ["best", "barato "],
        "donot": "不要把「cheap/barato」写进文案（贬义）；用「calidad-precio」表达性价比",
        "local_hint": "场景围绕 familia / amigos / reuniones",
    },
    "pl": {
        "market": "波兰 (PL)",
        "buyer_priorities": ["配送时效（Allegro Smart）", "性价比", "退货便利", "本地语言严谨"],
        "trust_signals": ["Allegro Smart", "Darmowa dostawa", "Zwrot", "CE"],
        "bullet_formula": "配送时效与 Smart 兼容 → 核心功能 → 性价比 → 退货政策 → 品质",
        "tone": "务实直接，首屏信息密度高（波兰买家先看配送与价格）",
        "avoid": ["best", "super okazja"],
        "donot": "标题 75 字符硬限制内放核心关键词；配送信息（Smart/免费/时效）必须出现",
        "local_hint": "波兰语变格复杂，机翻后必须人工复核变格与复合词",
    },
    "nl": {
        "market": "荷兰/比利时 (NL/BE)",
        "buyer_priorities": ["Delivery Promise", "直白务实", "可持续性", "售后评分"],
        "trust_signals": ["vandaag bezorgd", "gratis retour", "duurzaam", "CE"],
        "bullet_formula": "配送承诺 → 核心功能（直白陈述）→ 可持续/材质 → 售后 → 价格",
        "tone": "极简务实，荷兰买家厌恶营销废话（无套话、无夸张）",
        "avoid": ["best", "amazing", "speciaal aanbod!!!"],
        "donot": "句子短、信息直给；不要用感叹号；EAN 与规格必须准确",
        "local_hint": "荷兰语宜短句；「gratis」是高转化词但只用于真实免费的项",
    },
    "ro": {
        "market": "罗马尼亚 (RO)",
        "buyer_priorities": ["性价比", "耐用性", "配送确定性", "本地语言"],
        "trust_signals": ["Garanție", "CE", "Livrare rapidă", "Retur"],
        "bullet_formula": "性价比 → 耐用性/材质 → 核心功能 → 配送与退换 → 保修",
        "tone": "务实带一点热情，价格价值比要显性表达",
        "avoid": ["best", "ieftin"],
        "donot": "不要用「ieftin」（廉价贬义）；用「raport calitate-preț」",
        "local_hint": "罗马尼亚语带变音符号（ă/â/î/ș/ț），机翻常见丢符号要检查",
    },
    "en": {
        "market": "泛欧/英语 (UK/IE…)",
        "buyer_priorities": ["核心功能", "社会证明", "售后保障", "价格价值"],
        "trust_signals": ["CE/UKCA", "warranty", "30-day returns"],
        "bullet_formula": "痛点 → 核心功能 → 使用场景 → 材质品质 → 售后保障（黄金公式）",
        "tone": "专业清晰，客观陈述",
        "avoid": ["best", "cheapest", "#1"],
        "donot": "作为多站点提交母版时保持中性（Fruugo/Zalando 会再本地化）",
        "local_hint": "避免美式俚语（泛欧读者）",
    },
}

# 平台 → 语言 的兜底映射缺失时，直接用 platform_registry 的 language 字段。


def profile_for(platform: str, language: Optional[str]) -> Optional[Dict]:
    """取市场画像。

    - 显式指定语言：有画像则用之；无画像语言（如 ar/tr/hi…）→ None（不回落，
      避免用错市场规则改写）；
    - 未指定语言：按平台默认语言回落（otto→德、allegro→波…）；
    - 未知平台 → None（不抛异常）。
    """
    from .platform_registry import platform_config
    if language:
        return MARKET_PROFILES.get(language)
    try:
        lang = platform_config(platform)["language"]
    except KeyError:
        return None
    return MARKET_PROFILES.get(lang)


def cultural_prompt_block(profile: Dict) -> str:
    """把市场画像转成注入 LLM prompt 的改写指令（生成侧）。"""
    priorities = " > ".join(profile["buyer_priorities"])
    avoid = "、".join(profile["avoid"])
    return f"""
【文化本地化（Cultural Localization，不是机翻）】
目标市场：{profile['market']}
买家决策要素（按此顺序组织卖点）：{priorities}
五点描述结构：{profile['bullet_formula']}
语气：{profile['tone']}
信任信号（自然融入，不堆砌）：{profile['trust_signals']}
禁止出现：{avoid}
市场写法要求：{profile['donot']}
本地化提示：{profile['local_hint']}
"""


def score_cultural_fit(title: str, bullets: List[str], description: str,
                       profile: Dict) -> Dict:
    """对生成结果做确定性文化适配评分（校验侧）。

    返回 {"score": 0-100, "gaps": [...], "hits": [...]}。
    - 命中信任信号加分；五点结构覆盖买家决策要素前 3 项加分；
    - 出现 avoid 词直接扣分并进 gaps。
    """
    text = " ".join([title] + bullets + [description]).lower()
    gaps: List[str] = []
    hits: List[str] = []

    score = 55.0

    signal_hits = [s for s in profile["trust_signals"] if s.lower() in text]
    score += min(len(signal_hits), 3) * 8      # 信任信号最多 +24
    hits += signal_hits
    if not signal_hits:
        gaps.append(f"未出现该市场信任信号（如 {profile['trust_signals'][:3]}）")

    priority_hits = [p for p in profile["buyer_priorities"]
                     if any(w.lower() in text for w in _priority_words(p))]
    score += min(len(priority_hits), 3) * 5    # 决策要素覆盖最多 +15
    if len(priority_hits) < 2:
        gaps.append("卖点顺序未覆盖该市场前几位决策要素"
                    f"（{ ' / '.join(profile['buyer_priorities'][:2]) }）")

    avoid_hits = [a for a in profile["avoid"] if a.lower() in text and a.strip()]
    if avoid_hits:
        score -= min(len(avoid_hits) * 10, 30)
        gaps.append(f"出现该市场禁用/低效词：{ '、'.join(avoid_hits) }")

    exclam = text.count("!")
    if profile["market"].startswith(("德国", "荷兰")) and exclam >= 2:
        score -= 10
        gaps.append("德/荷市场忌感叹号堆叠（营销套话感）")

    return {
        "score": round(max(min(score, 100.0), 0.0), 1),
        "gaps": gaps,
        "hits": hits,
        "market": profile["market"],
    }


def _priority_words(priority: str) -> List[str]:
    """把决策要素映射成文案里常见的具象词（用于文本命中检测）。"""
    mapping = {
        "认证与安全背书": ["ce", "tüv", "gs", "zertifiziert", "geprüft", "安全", "认证"],
        "技术参数精确": ["mm", "cm", "watt", "volt", "mah", "寸", "mm", "参数"],
        "材质与做工": ["material", "stahl", "steel", "acier", "acciaio", "材质", "不锈钢"],
        "保修与售后": ["garantie", "garanzia", "garantía", "garanție", "warranty", "保修"],
        "环保回收": ["recycling", "weee", "recycel", "回收", "环保"],
        "生活场景与美学": ["salon", "cuisine", "maison", "elegan", "chic", "场景"],
        "保修与售后（sav）": ["garantie", "sav", "retour", "保修"],
        "性价比": ["calidad-precio", "rapport", "calitate", "value", "性价比"],
        "法语严谨性": ["garantie"],
        "设计与视觉": ["design", "stile", "estetica", "设计"],
        "家庭场景": ["famiglia", "familia", "casa", "famille", "家庭"],
        "情感共鸣": ["momenti", "condividere", "conviviale", "moment"],
        "家庭与社交场景": ["familia", "amigos", "reuniones", "家庭"],
        "促销敏感": ["oferta", "descuento", "promo", "优惠"],
        "配送时效（allegro smart）": ["smart", "dostawa", "delivery", "配送"],
        "退货便利": ["zwrot", "retour", "devolución", "return", "退货"],
        "本地语言严谨": [],
        "delivery promise": ["bezorgd", "bezorging", "delivery", "配送"],
        "直白务实": ["duidelijk", "eenvoudig"],
        "可持续性": ["duurzaam", "recycle", "可持续", "环保"],
        "性价比（罗马尼亚）": ["raport calitate", "calitate-preț"],
        "耐用性": ["durabil", "rezistent", "durable", "耐用"],
        "配送确定性": ["livrare", "livrarea", "delivery", "配送"],
        "核心功能": [],
        "社会证明": ["review", "rated", "口碑"],
        "售后保障": ["warranty", "guarantee", "returns", "售后"],
        "价格价值": ["value"],
    }
    return mapping.get(priority, [])
