"""产品能力落地页（SEO）— /features/{slug} 动态渲染。

首页「产品能力」四层结构拆分为 6 个独立落地页，消除"所有能力挤在一页"的问题。
单一数据源：本模块 FEATURES 字典 → 页面自动同步。
每页结构（对标 H10 功能页架构）：
  Hero（定位 + CTA + SVG 产品图）→ 痛点/违规后果 → 功能拆解（类目分组卡）→
  工作原理三步 → 数据信任条 → 定价付费墙 → FAQ → 底部 CTA → 相关页面交叉链接。
每页导航与首页一致（多页式：产品能力 / 覆盖平台 / 免费工具 / 定价 dropdown）。
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from ..config import settings
from .feature_pages_i18n_de import CHROME_DE, FEATURES_DE, MOCKUP_DE
from .feature_pages_i18n_en import CHROME_EN, FEATURES_EN, MOCKUP_EN
from .feature_pages_i18n_fr import CHROME_FR, FEATURES_FR, MOCKUP_FR
from .site_nav import NAV_CSS, site_nav

router = APIRouter()

# ---------------------------------------------------------------------------
# 多语言基础设施（zh 默认无前缀；en/de/fr 加语言前缀镜像路由）
# zh 输出与历史逐字节一致；仅 en/de/fr 分支注入切换器 / hreflang / 偏好脚本。
# ---------------------------------------------------------------------------
_LANG_HTML = {"zh": "zh-CN", "en": "en", "de": "de", "fr": "fr"}
_LANG_PREFIX = {"zh": "", "en": "/en", "de": "/de", "fr": "/fr"}
_LANGS = ("en", "de", "fr")

_FEATURES_LANG = {"en": FEATURES_EN, "de": FEATURES_DE, "fr": FEATURES_FR}
_CHROME_LANG = {"en": CHROME_EN, "de": CHROME_DE, "fr": CHROME_FR}
_MOCKUP_LANG = {"en": MOCKUP_EN, "de": MOCKUP_DE, "fr": MOCKUP_FR}

_LANG_SCRIPT = ('<script>(function(){try{localStorage.setItem("crossaio_lang",'
                'document.documentElement.lang||"zh")}catch(e){}})();</script>')


def _hreflang_feature(base: str, lang: str) -> str:
    """<head> 内 5 行 hreflang；中文路径无前缀，x-default 指向中文版。"""
    b = settings.app_url.rstrip("/")
    return (
        f'<link rel="alternate" hreflang="zh" href="{b}{base}">\n'
        f'<link rel="alternate" hreflang="en" href="{b}/en{base}">\n'
        f'<link rel="alternate" hreflang="de" href="{b}/de{base}">\n'
        f'<link rel="alternate" hreflang="fr" href="{b}/fr{base}">\n'
        f'<link rel="alternate" hreflang="x-default" href="{b}{base}">'
    )


def _switcher_feature(base: str, lang: str) -> str:
    """语言切换器：桌面按钮组 + 移动端(<640px)折叠为图标+原生下拉。

    冻结按钮组 markup（当前语言高亮 + aria-current）；<640px 用 CSS 隐藏按钮组、
    显示原生 <select>，onchange 跳转到所选语言对应路径（保持当前页面不丢）。
    """
    paths = {"zh": base, "en": "/en" + base, "de": "/de" + base, "fr": "/fr" + base}
    items = []
    opts = []
    for code, label in (("zh", "中文"), ("en", "EN"), ("de", "DE"), ("fr", "FR")):
        if code == lang:
            style = ("text-decoration:none;font-size:12.5px;font-weight:700;"
                     "padding:4px 10px;border-radius:999px;background:#2563eb;color:#fff")
            items.append(f'<a href="{paths[code]}" data-lang="{code}" aria-current="page" style="{style}">{label}</a>')
            opts.append(f'<option value="{paths[code]}" data-lang="{code}" selected>{label}</option>')
        else:
            style = ("text-decoration:none;font-size:12.5px;font-weight:700;"
                     "padding:4px 10px;border-radius:999px;color:#334155")
            items.append(f'<a href="{paths[code]}" data-lang="{code}" style="{style}">{label}</a>')
            opts.append(f'<option value="{paths[code]}" data-lang="{code}">{label}</option>')
    css = ('<style>.lang-switch-mobile{display:none;padding:6px 12px;font-size:13px;'
           'border:1px solid #cbd5e1;border-radius:999px;color:#0f172a;background:#fff;'
           'max-width:132px}'
           '@media(max-width:639px){.lang-switch{display:none!important}'
           '.lang-switch-mobile{display:inline-flex!important}}</style>')
    sel = ('<select class="lang-switch-mobile" role="navigation" aria-label="Language" '
           'onchange="location.href=this.value">' + "".join(opts) + "</select>")
    return (css + '<div class="lang-switch" role="navigation" aria-label="Language" '
            'style="display:inline-flex;gap:6px;align-items:center">' + "".join(items) + "</div>" + sel)


def _mockup_i18n(svg: str, name: str, lang: str) -> str:
    """对 SVG mockup 做「最长键优先」的中文源字面量→译文替换（含 alt/title）。

    zh 原样返回（逐字节等价）。lang 分支按 MOCKUP_XX[name] 字典顺序由长到短
    替换，防止「输入产品」误吞「输入产品信息」之类子串问题。
    """
    if lang == "zh":
        return svg
    table = _MOCKUP_LANG.get(lang, {}).get(name, {})
    for k in sorted(table.keys(), key=len, reverse=True):
        svg = svg.replace(k, table[k])
    return svg

# ---------------------------------------------------------------------------
# 数据源
# ---------------------------------------------------------------------------

FEATURES = {
    "gpsr": {
        "icon": "🛡️",
        "name": "GPSR 合规引擎",
        "title": "GPSR 合规引擎 — CE 类目识别 · 欧代 + 当地语言警示语 · 合规块一键回填 | CrossAIO",
        "meta_desc": "EU 2023/988 GPSR 已强制执行：自动识别 CE 类目与适用指令，生成含欧代与 16 国语言警示语的合规块，属性树硬阻断，7x24 监控 + 安全事件预警。免费体检开始。",
        "eyebrow": "产品能力 ① · 付费理由 #1",
        "h1": "缺一块合规块，<br>listing 就可能<em>整个下架</em>",
        "sub": "CrossAIO 合规引擎：CE 类目自动识别 → 适用指令匹配 → 欧代 + 当地语言安全警示语 → 生成可直接粘贴或 API 回填的 GPSR 合规块。恐惧驱动的付费理由：一次违规，损失远超一年订阅费。",
        "hero_note": "✓ 免费体检先报风险 · ✓ Starter 解锁合规块全文 · ✓ 无需绑定店铺",
        "mockup": "gpsr",
        "pain_title": "不做 GPSR 的代价",
        "pains": [
            "EU 2023/988 已于 2024-12 强制执行：欧盟市场非食品类产品必须有欧代 + 当地语言警示语，缺一块即下架",
            "SellSafe 只管合规文档不管 listing 文案；文案工具（H10 等）完全不管合规 —— 两个工具都不解决「listing 内的合规块」",
            "机翻警示语不被监管认可：德/法/波/罗等语言警示语必须是「该语言的市场表述」，不是直译",
            "欧代信息散落在 Excel 和聊天记录里，30% 的 listing 忘记填或填错",
        ],
        "caps": [
            {"group": "合规块生成", "color": "g1", "items": [
                ("CE 类目自动识别", "7 大类目规则库（玩具/电气/PPE/母婴/食品接触等），自动匹配适用指令"),
                ("欧代 + 警示语合规块", "欧代行自动替换台账中的默认责任人；7 种语言原生警示语，非直译"),
                ("平台原生头部", "Allegro 波兰语 / eMAG 罗马尼亚语等平台当地语言头部，直接回填对应字段"),
            ]},
            {"group": "硬阻断与监控", "color": "g2", "items": [
                ("属性树硬阻断", "像平台审核一样硬拦截：EAN 校验位错误、材质缺失 → ready_to_list = false"),
                ("7x24 监控 + 风险日报", "每日定时体检已上架 listing，规则更新自动复检，风险日报推送"),
                ("安全事件预警", "买家消息触及安全/人身伤害 → 15 天 Safety Gate 上报提示"),
            ]},
        ],
        "steps": [
            ("输入产品信息", "产品标题 + 关键词 + 类目，无需绑定店铺，30 秒出体检结果"),
            ("自动识别类目与指令", "7 类 CE 规则库匹配适用指令与警示语要求，免费版先报问题清单"),
            ("解锁合规块并回填", "Starter 解锁合规块全文：欧代行 + 当地语言警示语 + 平台原生头部，可粘贴或 API 回填"),
        ],
        "stats": [("7", "CE 类目规则库"), ("7", "警示语原生语言"), ("13", "平台回填适配"), ("15天", "Safety Gate 上报提示")],
        "tier_line": "Free：体检只报问题 · Starter €29/月：合规块全文 + 属性树校验 + 7x24 监控",
        "faqs": [
            ("免费体检和付费合规块的区别？", "免费体检告诉你缺什么、会被怎么罚（问题清单）；Starter 起生成可直接粘贴的合规块全文（欧代 + 警示语 + 平台原生头部），并支持 API 回填到 13 个平台。"),
            ("警示语是机器翻译吗？", "不是。德/法/意/西/波/罗/英 7 种语言的警示语为该语言的市场原生表述（如德国 ProdSG / 法国 DGCCRF 执法语境），不是直译。其余语言输出英文标注行并明确标示，避免空占位。"),
            ("欧代信息从哪里来？", "你可以在欧代台账中维护多个欧盟责任人并设默认；生成合规块时自动替换占位符，不需要每次手动填。"),
        ],
        "related": [("listing-generator", "📦 Listing 生成器"), ("matrix", "🌍 多平台矩阵"), ("safety-redline", "🚨 安全红线层")],
    },
    "listing-generator": {
        "icon": "📦",
        "name": "Listing 生成器",
        "title": "Listing 生成器 — 平台字数硬校验 · 五点+详情+搜索词 · 16 语言 | CrossAIO",
        "meta_desc": "一次输入生成标题/五点/详情/搜索词，Otto 70 / Allegro 75 / Amazon 200 字数硬校验，生成后自动评分标记违规项，16 语言本地化。免费每天 5 次。",
        "eyebrow": "产品能力 ② · 入口",
        "h1": "一次输入，<br>按平台规则写出<em>能过审</em>的 listing",
        "sub": "标题 + 五点 + 详情 + 搜索词，按 13 个平台的字数、语言、结构规则生成。生成后自动评分并标记违规项 —— 不是「建议填写」，是像平台审核一样硬校验。",
        "hero_note": "✓ 每天免费 5 次 · ✓ 无需绑定店铺 · ✓ 复制粘贴即上架",
        "mockup": "generator",
        "pain_title": "文案工具的通病",
        "pains": [
            "通用 AI 写出来的标题超过 Otto 70 字符 / Allegro 75 字符限制，直接被平台拒审",
            "先写完再翻译：翻译出来的五点不像「该语言卖家的表述」，转化率折半",
            "生成质量全靠肉眼检查，没有一个工具在生成时就按平台规则硬校验",
            "详情页和搜索词不符合平台结构要求，隐性影响搜索排名",
        ],
        "caps": [
            {"group": "生成", "color": "g1", "items": [
                ("标题 / 五点 / 详情 / 搜索词", "四件套一次生成，按平台结构要求组织，不是简单拼接"),
                ("16 语言本地化", "en/de/fr/es/it/pl/ro/nl/cs/sk/hu/bg/sv 等，按平台自动匹配"),
                ("广告文案", "Pro 起：站内广告标题与卖点文案，与 listing 同源关键词"),
            ]},
            {"group": "校验", "color": "g2", "items": [
                ("字数硬校验", "Otto 70 / Allegro 75 / Amazon 200 等字数限制内置为硬规则，超限直接标记"),
                ("完整度评分", "生成后自动评分，标记违规项与缺失字段，上架前发现问题"),
                ("平台结构规则", "各平台标题结构、五点条数、搜索词格式按卖家中心文档持续维护"),
            ]},
        ],
        "steps": [
            ("输入产品信息", "产品名称 + 核心关键词，可选填品牌/EAN/材质属性"),
            ("选择平台生成", "单平台精修或矩阵批量，语言与规则自动匹配"),
            ("校验后直接上架", "字数硬校验 + 完整度评分通过后，复制粘贴到平台卖家中心"),
        ],
        "stats": [("13", "平台规则内置"), ("16", "生成语言"), ("5次/天", "免费额度"), ("90%", "平均节省运营时间")],
        "tier_line": "Free：每天 5 次 · Starter €29/月：每天 50 次 + GPSR 合规块内嵌 · Pro €49/月：每天 200 次 + 广告文案",
        "faqs": [
            ("和 ChatGPT 直接写有什么区别？", "ChatGPT 不知道 Otto 70 字符、Allegro 75 字符这些平台硬规则，也不知道 GPSR 要内嵌什么。CrossAIO 把 13 个平台的规则做成硬校验，生成即合规，不用反复改。"),
            ("生成的 listing 质量如何保证？", "生成后自动评分：字数、语言、结构化要求逐项核对并标记违规项；属性树对 EAN 校验位等做硬阻断，上架前就能发现会被拒审的问题。"),
            ("需要绑定我的店铺吗？", "不需要。CrossAIO 是独立工作台，注册即用，生成结果复制粘贴到任何平台卖家中心即可。"),
        ],
        "related": [("matrix", "🌍 多平台矩阵"), ("gpsr", "🛡️ GPSR 合规引擎"), ("review-rewrite", "📈 差评改写")],
    },
    "matrix": {
        "icon": "🌍",
        "name": "多平台本地化矩阵",
        "title": "多平台矩阵 — 一次输入 13 平台批量本地化 · Allegro/eMAG/Cdiscount 竞品零覆盖 | CrossAIO",
        "meta_desc": "一次输入 → 13 平台批量生成本地化 Listing：Amazon EU+US、eBay、Allegro、Otto、Cdiscount、eMAG、TikTok Shop、Fruugo、Walmart、Kaufland、Zalando、bol.com。不绑店独立工作台。",
        "eyebrow": "产品能力 ③ · 规模杠杆",
        "h1": "一次输入，<br><em>13 平台</em>批量本地化",
        "sub": "Amazon 欧洲站 + 美国站、eBay、Allegro、Otto、Cdiscount、eMAG、TikTok Shop、Fruugo、Walmart、Kaufland、Zalando、bol.com —— 规则全部内置，语言自动匹配。H10 不碰本土平台，Marqetir 逼你绑店，我们都不。",
        "hero_note": "✓ 不绑店独立工作台 · ✓ 小平台联动覆盖东欧/南欧 · ✓ 矩阵结果逐平台可编辑",
        "mockup": "matrix",
        "pain_title": "扩平台的真实成本",
        "pains": [
            "每进一个新平台都要重学一遍规则：字数、语言、类目属性、合规字段全部不同",
            "H10 只做 Amazon；Marqetir/SellerCloud 要绑定店铺 API 才能用，数据安全存疑",
            "Allegro（波兰）、eMAG（罗马尼亚）、Cdiscount（法国）在主流工具中覆盖率为零，而这是东欧/南欧增长最快的市场",
            "多平台逐个翻译、逐个粘贴，一个 SKU 上全平台要花一整天",
        ],
        "caps": [
            {"group": "矩阵生成", "color": "g1", "items": [
                ("13 平台批量生成", "一次输入 → 13 平台本地化结果，逐平台可编辑、可复制、可回填"),
                ("语言自动匹配", "pl/de/fr/ro/nl 等按平台自动选择，无需手动指定"),
                ("合规块随行内嵌", "每份 listing 输出自带 GPSR 合规块（Starter 起），扩平台不漏合规"),
            ]},
            {"group": "小平台联动", "color": "g3", "items": [
                ("东欧增长引擎", "Allegro（波/捷/斯/匈）+ eMAG（罗/匈/保）—— 竞品覆盖率为零的市场"),
                ("南欧/西欧补齐", "Cdiscount（法）+ Fruugo（泛欧 20+ 国）率先支持"),
                ("规则页全公开", "6 个深耕平台的规则细节直接做成免费落地页，规则库透明可查"),
            ]},
        ],
        "steps": [
            ("输入一次产品信息", "产品名称 + 关键词 + 属性，所有平台共用同一输入"),
            ("勾选目标平台", "单选精修或 13 平台全选，规则与语言自动按平台匹配"),
            ("批量导出/回填", "逐平台复制粘贴，或经 API 适配层回填（Amazon SP-API / eBay REST）"),
        ],
        "stats": [("13", "平台规则内置"), ("16", "生成语言"), ("0", "需要绑定的店铺"), ("4", "竞品零覆盖小平台")],
        "tier_line": "Free：单平台体验 · Pro €49/月：3 平台矩阵 · Business €149/月：无限平台矩阵 + 优先支持",
        "faqs": [
            ("13 个平台包括哪些？", "Amazon 欧洲站+美国站、eBay、Allegro、Otto、Cdiscount、eMAG、TikTok Shop、Fruugo、Walmart、Kaufland、Zalando、bol.com。其中 Cdiscount、Allegro、eMAG、Fruugo 在竞品中覆盖率为零。"),
            ("矩阵生成的质量和小语种质量如何？", "每个平台按其卖家中心文档的字数/语言/结构规则硬校验；小语种按平台自动匹配当地语言，GPSR 警示语用该语言原生表述。"),
            ("真的不用绑定店铺？", "对。矩阵生成完全在 CrossAIO 工作台内完成。只有使用「API 回填」时才需要你提供对应平台的开发者凭证（Amazon SP-API / eBay OAuth），凭证存你自己的环境变量。"),
        ],
        "related": [("listing-generator", "📦 Listing 生成器"), ("gpsr", "🛡️ GPSR 合规引擎"), ("ai-service", "💬 AI 客服")],
    },
    "review-rewrite": {
        "icon": "📈",
        "name": "差评改写闭环",
        "title": "差评改写 — 8 类主题定位 · 五点修复 · 语义评分（Rufus/iZi 适配）| CrossAIO",
        "meta_desc": "差评自动定位主题（8 类），生成 listing 五点修复建议并改写；8 类买家问题语义覆盖度评分，面向 Rufus / iZi 等 AI 购物助手优化。周频使用，直接关联转化。",
        "eyebrow": "产品能力 ④ · 续费理由",
        "h1": "差评不是终点，<br>是 listing 的<em>改写指令</em>",
        "sub": "差评自动定位主题（尺寸偏大/续航不足/包装破损等 8 类），生成五点修复建议并改写对应卖点；再用语义评分检查 listing 是否回答了买家最常问的 8 类问题 —— 让 Rufus、iZi 这些 AI 导购也推荐你的产品。",
        "hero_note": "✓ 周频使用 · ✓ 修复建议可直接生成新五点 · ✓ 语义评分免费体验",
        "mockup": "review",
        "pain_title": "被浪费的差评数据",
        "pains": [
            "差评只被「回复」没有被「利用」：主题散落在评论里，没有人系统性转成 listing 修复",
            "Rufus（Amazon）、iZi（Allegro）等 AI 购物助手开始替买家做决策，listing 没回答到的问题 AI 就替你回答成竞品",
            "人工改五点靠感觉，没有任何工具能量化「这个 listing 回答了几类买家问题」",
            "差评里混着安全诉求（断裂/过热/窒息风险），普通客服流程会漏掉 GPSR 安全事件上报义务",
        ],
        "caps": [
            {"group": "差评 → Listing 闭环", "color": "g1", "items": [
                ("8 类主题定位", "尺寸/续航/材质/包装/物流/假货质疑/安装难度/安全诉求自动归类"),
                ("五点修复 + 改写", "按主题生成修复建议，直接改写对应五点，形成可上架的新版本"),
                ("安全诉求预警", "安全类差评自动触发 GPSR 安全事件预警（15 天 Safety Gate 提示）"),
            ]},
            {"group": "语义评分", "color": "g3", "items": [
                ("8 类买家问题覆盖度", "量化 listing 对常见买家问题的回答覆盖度，逐类给出缺口"),
                ("Rufus / iZi 适配", "面向 AI 购物助手优化语义结构，让 AI 导购引用你的卖点"),
                ("迭代追踪", "改写后复评，量化每次修复带来的覆盖度提升"),
            ]},
        ],
        "steps": [
            ("导入差评", "粘贴差评/评论，或选平台自动拉取（开发中：eBay 接入）"),
            ("主题定位 + 修复建议", "8 类主题归类，生成针对对应五点的修复与改写"),
            ("复评上架", "语义评分复评覆盖度，新版本直接替换上架"),
        ],
        "stats": [("8", "差评主题类型"), ("8", "语义覆盖度维度"), ("2", "AI 导购平台适配"), ("周频", "典型使用频率")],
        "tier_line": "Free：语义评分体验 · Pro €49/月：差评改写闭环 + 广告文案 · Business：批量监控",
        "faqs": [
            ("差评数据从哪来？", "目前支持手动粘贴差评/评论；eBay 平台接入后可经授权自动拉取。所有分析在你的 CrossAIO 账户内完成，不与第三方共享。"),
            ("语义评分是什么？", "把买家最常见的 8 类问题（尺寸、续航、材质、安全等）作为维度，量化你的 listing 每一类的回答覆盖度。Rufus、iZi 这类 AI 导购就是按类似逻辑替买家筛选的。"),
            ("安全类差评会被特殊处理吗？", "会。触及安全/人身伤害的差评自动触发合规优先流程：GPSR 指引 + 15 天 Safety Gate 上报提示，不会当成普通差评处理。"),
        ],
        "related": [("gpsr", "🛡️ GPSR 合规引擎"), ("listing-generator", "📦 Listing 生成器"), ("safety-redline", "🚨 安全红线层")],
    },
    "ai-service": {
        "icon": "💬",
        "name": "AI 客服 + 统一收件箱",
        "title": "AI 客服 — AI Act Art.50 披露原生内嵌 · eBay 接入 · 跨平台统一收件箱 | CrossAIO",
        "meta_desc": "买家消息 webhook 推送 → LLM 生成回复草稿 → 每条回复原生内嵌 EU AI Act Art.50 披露（2026-08-02 强制），GPSR 红线拦截，跨平台统一收件箱。竞品只卖快回复，我们卖不违规。",
        "eyebrow": "产品能力 ⑤ · 合规获客入口",
        "h1": "每条 AI 回复，<br>原生内嵌 <em>AI Act Art.50 披露</em>",
        "sub": "eBay 卖家授权后买家消息 webhook 推送到 CrossAIO，AI 生成回复草稿，你确认后发回；每条回复原生内嵌 EU AI Act Art.50 机器身份披露（2026-08-02 强制生效，罚 €1500 万或营收 3%）。16 语言披露，跨平台统一收件箱管理。",
        "hero_note": "✓ 你确认后才发送 · ✓ Art.50 披露 16 语言 · ✓ 不需第三方客服工具",
        "mockup": "inbox",
        "pain_title": "客服工具的合规盲区",
        "pains": [
            "Amazon/eBay 官方 AI 客服只解决「快回复」，完全没有 AI Act 合规层",
            "Responso / eDesk / BaseLinker 等客服工具至今零内建 AI Act Art.50 披露 —— 而它 2026-08-02 强制生效",
            "买家消息里的安全诉求（产品断裂/过热/儿童误吞）被当成普通咨询自动秒回，漏掉 GPSR 上报义务",
            "13 个平台的买家消息分散在各卖家后台，回复口径不一致，合规状态无法追踪",
        ],
        "caps": [
            {"group": "回复与披露", "color": "g1", "items": [
                ("Art.50 披露原生内嵌", "每条 AI 回复自动带 16 语言机器身份披露，按买家语言选择表述"),
                ("LLM 回复草稿", "上下文感知生成回复，你确认后才发送，全程留痕"),
                ("GPSR 红线拦截", "买家消息触及安全/人身伤害 → 切换「合规优先回复」：GPSR 指引 + 15 天 Safety Gate 提示"),
            ]},
            {"group": "接入与收件箱", "color": "g2", "items": [
                ("eBay webhook 接入", "OAuth2 授权后买家消息实时推送，无需第三方工具介入"),
                ("跨平台统一收件箱", "13 平台会话统一管理，手动导入 + API 拉取，GPSR/AI Act 状态逐条标记"),
                ("数据自留", "所有数据在你的 CrossAIO 账户内，凭证存你自己的环境变量"),
            ]},
        ],
        "steps": [
            ("授权接入", "eBay OAuth2 授权，买家消息 webhook 推送到 CrossAIO（其他平台手动导入）"),
            ("AI 生成草稿", "LLM 按买家语言生成回复，自动内嵌 Art.50 披露；安全诉求触发合规优先回复"),
            ("确认发送", "你在统一收件箱确认后发回；每条会话的 GPSR / AI Act 状态留痕可审计"),
        ],
        "stats": [("16", "Art.50 披露语言"), ("13", "统一收件箱平台"), ("€15M", "AI Act 最高罚款"), ("2026-08", "Art.50 生效日")],
        "tier_line": "Pro €49/月：AI 客服 + 统一收件箱 · Business：多店铺 + 优先支持",
        "faqs": [
            ("AI Act Art.50 披露是什么？", "EU AI Act 第 50 条要求 AI 与人交互时必须披露机器身份，2026-08-02 强制生效，违规最高罚 €1500 万或全球营收 3%。CrossAIO 在每条 AI 回复原生内嵌按买家语言选择的披露文本。"),
            ("AI 会直接发给买家吗？", "不会。AI 只生成草稿，你在统一收件箱确认后才发送；安全类诉求会被强制切换为「合规优先回复」并提示 15 天上报义务。"),
            ("除了 eBay 还能接哪些平台？", "eBay 已接（webhook 实时推送）；其余 12 个平台支持统一收件箱手动导入 + API 适配层，按平台逐步开放实时接入。"),
        ],
        "related": [("safety-redline", "🚨 安全红线层"), ("gpsr", "🛡️ GPSR 合规引擎"), ("matrix", "🌍 多平台矩阵")],
    },
    "safety-redline": {
        "icon": "🚨",
        "name": "政策安全红线层",
        "title": "政策安全红线层 — 威胁/勒索识别 · 合规优先回复 · Safety Gate 15 天上报 | CrossAIO",
        "meta_desc": "威胁、勒索、人身伤害诉求自动识别：安抚 + 转人工留证，不做无脑秒回；触发 GPSR 安全事件流程（15 天 Safety Gate 上报提示）+ AI Act 披露。合规优先于效率。",
        "eyebrow": "产品能力 ⑥ · 兜底线",
        "h1": "威胁、勒索、伤害诉求，<br><em>合规优先</em>，不做无脑秒回",
        "sub": "AI 客服效率再高，遇到威胁、勒索、人身伤害诉求也不能自动秒回。CrossAIO 红线层自动识别高风险消息：安抚 + 转人工 + 留证，触发 GPSR 安全事件流程（15 天 Safety Gate 上报提示）与 AI Act 披露 —— 竞品卖效率，我们守住你的合规底线。",
        "hero_note": "✓ 高风险消息强制转人工 · ✓ 上报时限自动提示 · ✓ 全程留证可审计",
        "mockup": "redline",
        "pain_title": "无脑秒回的代价",
        "pains": [
            "纯效率型 AI 客服对「产品起火/儿童误吞」类消息照样礼貌秒回，错过 15 天 Safety Gate 强制上报窗口",
            "威胁与勒索消息被当普通纠纷处理，没有留证，后续纠纷/平台申诉时拿不出证据链",
            "情绪升级后由不同客服随意接手，口径混乱，把小纠纷拖成平台投诉",
            "安全事件的 GPSR 处理流程（下架评估、上报、召回评估）没有任何客服工具内建",
        ],
        "caps": [
            {"group": "识别与拦截", "color": "g2", "items": [
                ("高风险消息识别", "威胁/勒索/人身伤害/儿童安全诉求自动分类标记，强制不走自动回复"),
                ("安抚 + 转人工", "生成安抚话术并转人工处理，提示留证要点（截图/订单号/消息原文）"),
                ("合规优先回复", "安全事件切换 GPSR 指引回复：停售评估建议 + 15 天 Safety Gate 上报提示"),
            ]},
            {"group": "留证与上报", "color": "g3", "items": [
                ("全程留证", "会话全量留痕：识别结果、处理动作、回复内容可审计"),
                ("Safety Gate 提示", "15 天上报时限自动提醒，附 Safety Gate 提交要点清单"),
                ("Art.50 合规不变", "红线层回复同样原生内嵌 AI Act 披露，合规层无死角"),
            ]},
        ],
        "steps": [
            ("消息进入红线层", "所有买家消息先过高风险识别（威胁/勒索/伤害/儿童安全）"),
            ("强制转人工留证", "高风险消息不走自动回复：安抚话术 + 转人工 + 留证提示"),
            ("GPSR 安全事件流程", "确认安全事件 → 停售评估建议 + 15 天 Safety Gate 上报提示 → 全程留痕"),
        ],
        "stats": [("15天", "Safety Gate 上报时限"), ("4", "高风险消息类型"), ("100%", "高风险强制转人工"), ("全程", "留证可审计")],
        "tier_line": "Pro €49/月起含红线层 · 与 AI 客服、统一收件箱同层联动",
        "faqs": [
            ("什么算高风险消息？", "四类：威胁（人身/诉讼恐吓）、勒索（以差评/举报要挟）、产品人身伤害诉求（起火/断裂/过敏）、儿童安全诉求（误吞/窒息）。命中任意一类即拦截自动回复。"),
            ("拦截后具体发生什么？", "生成安抚话术转人工处理，提示留证要点；若确认为安全事件，走 GPSR 流程：停售评估建议、15 天 Safety Gate 上报提示。所有动作留痕。"),
            ("这和 AI 客服是什么关系？", "红线层是 AI 客服的前置层：所有消息先过高风险识别，普通消息才进入 AI 草稿流程。两层都在统一收件箱内运作。"),
        ],
        "related": [("ai-service", "💬 AI 客服"), ("gpsr", "🛡️ GPSR 合规引擎"), ("review-rewrite", "📈 差评改写")],
    },
    "inbox": {
        "icon": "📥",
        "name": "跨平台统一收件箱",
        "title": "统一收件箱 — 13 平台买家消息一处管理 · AI 母语回复 · 合规状态逐条标记 | CrossAIO",
        "meta_desc": "把 Amazon/eBay/Allegro/Otto/Kaufland 等 13 个平台的买家消息汇到一个界面：AI 按买家母语起草回复，Art.50 披露与 GPSR 安全指引自动内嵌，合规状态逐条留痕。",
        "eyebrow": "产品能力 ⑦ · 规模瓶颈解药",
        "h1": "13 个平台的买家消息，<br>一个收件箱<em>全部管完</em>",
        "sub": "欧洲跨境卖家平均同时运营 6+ 平台，买家消息散落各后台、语言各异。CrossAIO 统一收件箱把 13 平台会话汇到一处：eBay OAuth 实时同步，其余平台凭证自助接入或批量导入；AI 草稿按买家母语生成，Art.50 披露 + GPSR 安全指引自动内嵌。",
        "hero_note": "✓ eBay 实时同步 · ✓ 12 平台自助凭证/导入 · ✓ 回复合规留痕",
        "mockup": "inbox",
        "pain_title": "多平台客服的三重消耗",
        "pains": [
            "逐个平台登录查消息：一天 6 个后台来回切换，漏回一条就是差评或退货",
            "德语/波兰语/罗马尼亚语消息看不懂，机翻回复转化差还容易失礼",
            "AI 客服工具不认平台规则：Art.50 披露缺失、安全诉求被当普通咨询秒回",
            "哪个会话处理过、哪个触发过安全事件 —— 分散在各平台无从审计",
        ],
        "caps": [
            {"group": "汇聚与同步", "color": "g1", "items": [
                ("eBay 实时同步", "OAuth2 授权后买家消息 webhook 实时推送，AI 回复可直发买家"),
                ("12 平台自助凭证/导入", "Allegro/Otto/Kaufland 等粘贴 API 凭证（AES-256 加密）即接入，或每批 200 条批量导入"),
                ("平台与语言筛选", "按平台/语言/合规状态过滤会话，优先处理安全类"),
            ]},
            {"group": "回复与合规", "color": "g2", "items": [
                ("AI 母语草稿", "按买家语言生成回复草稿，你确认后才发送"),
                ("Art.50 + GPSR 自动内嵌", "每条回复自动过组合工作流：AI 身份披露 + 安全诉求升级为合规优先回复"),
                ("合规状态留痕", "每条会话的 GPSR / AI Act 处理状态标记，可审计可追溯"),
            ]},
        ],
        "steps": [
            ("接入平台", "eBay 一键 OAuth；其余平台在工作台凭证中心粘贴 API 凭证或批量导入消息"),
            ("统一处理", "13 平台会话一个列表：筛选 → AI 母语草稿 → 确认发送"),
            ("合规留痕", "Art.50 披露与 GPSR 事件逐条标记，随时导出审计"),
        ],
        "stats": [("13", "平台统一接入"), ("12", "支持自助凭证"), ("16", "AI 回复语言"), ("100%", "回复合规留痕")],
        "tier_line": "Pro €49/月：统一收件箱 + AI 客服 · Business：多店铺隔离 + 优先同步",
        "faqs": [
            ("哪些平台能实时同步？", "eBay 已接 OAuth 实时同步；Allegro/Otto/Kaufland 等 12 个平台支持自助粘贴 API 凭证接入（凭证 AES-256 加密），或每批 200 条的批量导入，实时同步按平台逐步开放。"),
            ("凭证安全吗？", "AES-256 加密封存，界面与日志永不回显明文；也可随时在工作台一键断开删除。"),
            ("AI 回复合规吗？", "每条回复自动内嵌 EU AI Act Art.50 机器身份披露（按买家语言），触及产品安全时自动切换 GPSR 合规优先回复 + 15 天 Safety Gate 上报提示。"),
        ],
        "related": [("ai-service", "💬 AI 客服"), ("safety-redline", "🚨 安全红线层"), ("gpsr", "🛡️ GPSR 合规引擎")],
    },
    "ad-copy": {
        "icon": "📣",
        "name": "广告文案生成",
        "title": "广告文案 — 按平台广告位规则生成 · 合规词校验 · 多语言 A/B 变体 | CrossAIO",
        "meta_desc": "Amazon SP/SB/SD 广告标题与描述、各平台推广位文案一键生成：字数与禁用词按平台规则硬校验，多语言变体支持 A/B 测试，不含违规促销词。",
        "eyebrow": "产品能力 ⑧ · 增长杠杆",
        "h1": "广告文案不再裸奔，<br>平台规则<em>先校验再生成</em>",
        "sub": "广告文案被拒审一次就烧掉一天流量。CrossAIO 按目标平台广告位规则生成标题/描述：字数、禁用词（best/cheapest/联系方式的硬禁令）、当地语言习惯全部前置校验，输出多组变体支持 A/B 投放。",
        "hero_note": "✓ 禁用词前置拦截 · ✓ 多语言 A/B 变体 · ✓ 字数硬校验",
        "mockup": "ad",
        "pain_title": "广告文案的三个隐形坑",
        "pains": [
            "促销词踩线：best / cheapest / No.1 在多数平台广告政策里直接拒审",
            "德国站广告写英语转化腰斩，本地化又请不起母语文案",
            "每个平台广告位字数规则不同，手写 13 平台版本纯人力消耗",
        ],
        "caps": [
            {"group": "生成", "color": "g1", "items": [
                ("多平台广告文案", "按平台广告位规则生成标题 + 描述，一次输入多平台输出"),
                ("A/B 变体", "每组输出多语言变体，支持投放测试择优"),
                ("文化本地化", "按市场画像改写：德国重参数认证、法国重场景（与 Listing 同一画像引擎）"),
            ]},
            {"group": "合规", "color": "g2", "items": [
                ("禁用词前置拦截", "促销词 / 夸大词 / 联系方式在生成前拦截，不浪费拒审机会"),
                ("字数硬校验", "各平台广告位字符上限逐项校验，超限即时提示"),
            ]},
        ],
        "steps": [
            ("输入产品与平台", "选目标平台与语言，给核心关键词"),
            ("规则校验生成", "禁用词与字数前置校验 → 生成多组合规文案变体"),
            ("投放择优", "A/B 变体投放，表现差的随时重新生成"),
        ],
        "stats": [("13", "平台规则库"), ("0", "促销词拒审目标"), ("8", "市场文化画像"), ("11", "输出语言")],
        "tier_line": "Starter €9/月 起：广告文案 · Pro：多平台矩阵 + A/B 变体",
        "faqs": [
            ("会生成被拒审的文案吗？", "生成前按平台广告政策做禁用词与字数硬校验，促销夸大词与联系方式直接拦截；但平台审核政策随时调整，最终以平台判定为准。"),
            ("支持哪些语言？", "与 Listing 生成同一引擎：11 种输出语言 + 8 市场文化画像（德/法/意/西/波/荷/罗等）。"),
            ("和 Listing 生成器什么区别？", "Listing 生成器产出的是商品页四件套；广告文案针对推广位场景，输出更短更聚焦转化的标题/描述与 A/B 变体。"),
        ],
        "related": [("listing-generator", "📦 Listing 生成器"), ("matrix", "🌍 多平台矩阵"), ("gpsr", "🛡️ GPSR 合规引擎")],
    },
    "listing-watch": {
        "icon": "📡",
        "name": "Listing 监控日报",
        "title": "Listing 监控 — 每日自动体检 · 风险升级即日报 · 合规漂移预警 | CrossAIO",
        "meta_desc": "每天自动体检你的 Listing：字数漂移、合规块缺失、差评新增、语义评分下滑逐项追踪；风险升级时邮件日报直达，不用天天登录后台巡检。",
        "eyebrow": "产品能力 ⑨ · 留存抓手",
        "h1": "Listing 不是发完就完了，<br>每天<em>自动体检一次</em>",
        "sub": "Listing 被平台静默改写、合规块被吞、新差评带安全词 —— 这些变化你发现时损失已经发生。CrossAIO 每日定时体检你的监控列表：字数漂移 / 合规缺失 / 差评主题 / 语义评分逐项追踪，风险升级即发邮件日报。",
        "hero_note": "✓ 每日定时体检 · ✓ 风险升级邮件日报 · ✓ 差评主题追踪",
        "mockup": "watch",
        "pain_title": "不管不问的代价",
        "pains": [
            "平台静默改写 Listing：关键词被删、类目被换，销量掉了才发现",
            "新差评里的安全诉求（过热/断裂）没被看到 → 错过 15 天 Safety Gate 上报窗口",
            "每天逐平台手动巡检 = 又一轮人力消耗，且容易漏",
        ],
        "caps": [
            {"group": "自动体检", "color": "g1", "items": [
                ("每日定时体检", "监控列表里的 Listing 每天自动跑一遍：字数 / 合规块 / 语义评分"),
                ("风险分级", "致命（合规缺失）/ 高（差评安全词）/ 中（评分下滑）分级告警"),
                ("邮件日报", "风险升级时 SMTP 邮件直达，无需登录后台巡检"),
            ]},
            {"group": "修复闭环", "color": "g2", "items": [
                ("差评主题追踪", "新差评自动做主题定位，安全类直接转 GPSR 合规优先流程"),
                ("一键改写", "从日报直达差评改写闭环，修复后复评追踪提升"),
            ]},
        ],
        "steps": [
            ("添加监控", "把要盯的 Listing 加入监控列表（按平台）"),
            ("每日体检", "定时任务每天自动体检，逐项比对漂移与风险"),
            ("日报直达", "风险升级 → 邮件日报 → 一键跳转修复"),
        ],
        "stats": [("每日", "自动体检频率"), ("146", "安全事故词库"), ("3 级", "风险分级"), ("15 天", "Safety Gate 窗口")],
        "tier_line": "Starter €9/月 起：5 个监控位 · Pro：50 个 + 邮件日报 · Business：多店铺",
        "faqs": [
            ("监控什么内容？", "标题/五点字数漂移、GPSR 合规块完整性、新差评与主题、语义评分变化 —— 每日定时跑一遍并分级。"),
            ("怎么通知我？", "风险升级时 SMTP 邮件日报直达（需在环境配置 SMTP）；也可随时在工作台查看历史报告。"),
            ("和差评改写什么关系？", "日报发现安全类差评后，一键跳转差评改写闭环：主题定位 → 五点修复 → 复评追踪，形成监控-修复闭环。"),
        ],
        "related": [("review-rewrite", "📈 差评改写"), ("gpsr", "🛡️ GPSR 合规引擎"), ("ai-service", "💬 AI 客服")],
    },
}

_FEATURE_ORDER = ["gpsr", "listing-generator", "matrix", "review-rewrite", "ai-service",
                  "safety-redline", "inbox", "ad-copy", "listing-watch"]

# 落地页 → 工作台面板深链（/app?tab=xxx），双向互通
_WORKBENCH_TAB = {
    "listing-generator": "desc",
    "gpsr": "gpsr",
    "ai-service": "cs",
    "inbox": "inbox",
    "ad-copy": "ad",
    "review-rewrite": "review",
    "listing-watch": "watch",
}

# ---------------------------------------------------------------------------
# SVG 产品图（每页一张 H10 风格产品 mockup，600x420 viewBox）
# ---------------------------------------------------------------------------

def _wrap(text: str, width: int = 16) -> list:
    """中文/混排文本按宽度粗略折行为两行。"""
    if len(text) <= width:
        return [text]
    cut = width
    for i in range(min(width, len(text) - 1), max(4, width - 8), -1):
        if text[i] in "，、；：（·→ )/":
            cut = i + 1
            break
    return [text[:cut], text[cut:][:width + 4]]


_FLOW_COLORS = [("#eff6ff", "#bfdbfe", "#1d4ed8", "#2563eb"),
                ("#f5f3ff", "#ddd6fe", "#6d28d9", "#8b5cf6"),
                ("#f0fdf4", "#bbf7d0", "#065f46", "#059669")]


def _flow_svg(steps, lang: str = "zh") -> str:
    """三步原理动画流程图 — 数据驱动（节点/文案来自调用方 steps，已按语言译好）。

    节点依次浮入，连接线虚线流动，箭头延迟出现。
    """
    _FLOW_ARIA = {
        "zh": "三步工作原理流程图",
        "en": "three-step how-it-works flow diagram",
        "de": "Dreischritt-Arbeitsablauf-Diagramm",
        "fr": "schéma de fonctionnement en trois étapes",
    }
    node_w, node_h, gap = 188, 128, 38
    x0, y0 = 12, 34
    parts = [
        '<svg viewBox="0 0 640 190" width="100%" role="img" aria-label="' + _FLOW_ARIA[lang] + '" '
        'style="max-width:720px;display:block;margin:0 auto">',
        '<defs><marker id="flArr" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">'
        '<path d="M0,0 L8,4 L0,8 z" fill="#94a3b8"/></marker></defs>',
    ]
    for i, (title, desc) in enumerate(steps[:3]):
        fill, stroke, ink, accent = _FLOW_COLORS[i % 3]
        x = x0 + i * (node_w + gap)
        lines = _wrap(_esc(desc))
        parts.append(
            f'<g class="fl-node n{i+1}">'
            f'<rect x="{x}" y="{y0}" width="{node_w}" height="{node_h}" rx="14" fill="{fill}" stroke="{stroke}"/>'
            f'<circle cx="{x+24}" cy="{y0+24}" r="13" fill="{accent}"/>'
            f'<text x="{x+24}" y="{y0+29}" text-anchor="middle" font-size="13" font-weight="800" fill="#fff" font-family="Arial">{i+1}</text>'
            f'<text x="{x+44}" y="{y0+29}" font-size="13.5" font-weight="800" fill="{ink}" font-family="Arial">{_esc(title)}</text>'
            f'<text x="{x+16}" y="{y0+58}" font-size="11" fill="#475569" font-family="Arial">{lines[0]}</text>'
            + (f'<text x="{x+16}" y="{y0+76}" font-size="11" fill="#475569" font-family="Arial">{lines[1]}</text>' if len(lines) > 1 else "")
            + f'<rect x="{x+16}" y="{y0+node_h-26}" width="{node_w-32}" height="6" rx="3" fill="{accent}" opacity=".25"/>'
            f'<rect x="{x+16}" y="{y0+node_h-26}" width="{(node_w-32)//2}" height="6" rx="3" fill="{accent}" opacity=".7"/>'
            "</g>")
        if i < 2:
            lx1 = x + node_w + 4
            lx2 = x + node_w + gap - 8
            ly = y0 + node_h // 2
            parts.append(
                f'<line class="fl-line" x1="{lx1}" y1="{ly}" x2="{lx2}" y2="{ly}" '
                f'stroke="#94a3b8" stroke-width="2" marker-end="url(#flArr)"/>')
    parts.append("</svg>")
    return "".join(parts)


_PLATFORM_FLAGS = {
    "amazon": ("🇪🇺", "Amazon 欧洲站", "DE/FR/IT/ES"),
    "amazon_us": ("🇺🇸", "Amazon 美国站", "US/CA/MX"),
    "ebay": ("🌐", "eBay", "欧美全局"),
    "fruugo": ("🇪🇺", "Fruugo", "泛欧分销"),
    "walmart": ("🇺🇸", "Walmart", "US"),
    "cdiscount": ("🇫🇷", "Cdiscount", "法国"),
    "otto": ("🇩🇪", "Otto", "德国"),
    "allegro": ("🇵🇱", "Allegro", "波兰"),
    "emag": ("🇷🇴", "eMAG", "罗马尼亚"),
    "kaufland": ("🇩🇪", "Kaufland", "德/中东欧"),
    "bol": ("🇳🇱", "bol.com", "荷/比"),
    "zalando": ("👗", "Zalando", "欧洲时尚"),
    "tiktok": ("🎬", "TikTok Shop", "内容电商"),
}


# region 文案按语言翻译；zh 键为原文，zh 输出保持不变
_REGION_I18N = {
    "欧美全局": {"en": "Global (EU/US)", "de": "Global (EU/US)", "fr": "Mondial (EU/US)"},
    "泛欧分销": {"en": "pan-EU", "de": "paneuropäisch", "fr": "paneuropéen"},
    "法国": {"en": "France", "de": "Frankreich", "fr": "France"},
    "德国": {"en": "Germany", "de": "Deutschland", "fr": "Allemagne"},
    "波兰": {"en": "Poland", "de": "Polen", "fr": "Pologne"},
    "罗马尼亚": {"en": "Romania", "de": "Rumänien", "fr": "Roumanie"},
    "德/中东欧": {"en": "DE/CE Europe", "de": "DE/Mittelosteuropa", "fr": "DE/Europe centrale"},
    "荷/比": {"en": "NL/BE", "de": "NL/BE", "fr": "NL/BE"},
    "欧洲时尚": {"en": "European fashion", "de": "europ. Mode", "fr": "mode européenne"},
    "内容电商": {"en": "social commerce", "de": "Social Commerce", "fr": "social commerce"},
}


# display 名中文化片段按语言覆盖（注册表 display 含中文，注册表本身不动）
_DISPLAY_I18N = {
    "Amazon 欧洲站": {"en": "Amazon EU", "de": "Amazon EU", "fr": "Amazon UE"},
    "Amazon 美国站": {"en": "Amazon US", "de": "Amazon US", "fr": "Amazon US"},
    "Fruugo（泛欧）": {"en": "Fruugo (pan-EU)", "de": "Fruugo (paneuropäisch)", "fr": "Fruugo (paneuropéen)"},
}


def _platform_marquee(lang: str = "zh") -> str:
    """13 平台无缝滚动旗帜墙（悬停暂停），素材数据与平台注册表同源。"""
    from ..experts.platform_registry import PLATFORMS
    chips = []
    for key, (flag, name, region) in _PLATFORM_FLAGS.items():
        disp = PLATFORMS[key]["display"] if key in PLATFORMS else name
        disp = _DISPLAY_I18N.get(disp, {}).get(lang, disp)
        reg = _REGION_I18N.get(region, {}).get(lang, region)
        chips.append(f'<span class="pm-chip">{flag} {disp}<small>{reg}</small></span>')
    track = "".join(chips)
    return f'<div class="pmarquee"><div class="pm-track">{track}{track}</div></div>'


_MOCKUP_SHELL = (
    '<svg viewBox="0 0 620 430" width="100%" role="img" aria-label="{alt}" '
    'style="max-width:560px;display:block;margin:0 auto;filter:drop-shadow(0 30px 60px rgba(0,0,0,.45))">'
    '<defs>'
    '<linearGradient id="mkScanG" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#3b82f6" stop-opacity="0"/>'
    '<stop offset=".5" stop-color="#3b82f6" stop-opacity=".16"/>'
    '<stop offset="1" stop-color="#3b82f6" stop-opacity="0"/></linearGradient>'
    '<clipPath id="mkClip"><rect x="10" y="10" width="600" height="410" rx="16"/></clipPath>'
    '</defs>'
    '<g class="mk-float">'
    '<rect x="10" y="10" width="600" height="410" rx="16" fill="#ffffff"/>'
    '<rect x="10" y="10" width="600" height="44" rx="16" fill="#f1f5f9"/>'
    '<rect x="10" y="38" width="600" height="16" fill="#f1f5f9"/>'
    '<circle class="mk-dot" cx="34" cy="32" r="6" fill="#fca5a5"/>'
    '<circle class="mk-dot d2" cx="54" cy="32" r="6" fill="#fcd34d"/>'
    '<circle class="mk-dot d3" cx="74" cy="32" r="6" fill="#86efac"/>'
    '<rect x="26" y="60" width="24" height="24" rx="7" fill="#2563eb"/>'
    '<text x="38" y="78" text-anchor="middle" font-size="14" fill="#fff" font-family="Arial">🤖</text>'
    '<text x="60" y="77" font-size="14" font-weight="700" fill="#0f172a" font-family="Arial">CrossAIO — {title}</text>'
    '{body}'
    '<rect class="mk-scan" x="10" y="0" width="600" height="34" fill="url(#mkScanG)" clip-path="url(#mkClip)"/>'
    '</g>'
    '</svg>'
)


def _m_gpsr(lang: str = "zh") -> str:
    if lang == "zh":
        body = """
    <rect x="26" y="98" width="568" height="60" rx="10" fill="#fff5f5" stroke="#fecaca"/>
    <text x="44" y="122" font-size="13" font-weight="700" fill="#dc2626" font-family="Arial">⚠ 体检发现 3 个 GPSR 风险 — EU 2023/988</text>
    <text x="44" y="142" font-size="11" fill="#7f1d1d" font-family="Arial">玩具类目 · 缺欧代 · 缺德语窒息警示语 · 触发下架风险</text>
    <rect x="26" y="170" width="272" height="150" rx="10" fill="#f8fafc" stroke="#e2e8f0"/>
    <text x="42" y="194" font-size="12" font-weight="700" fill="#0f172a" font-family="Arial">检查项</text>
    <text x="42" y="218" font-size="11" fill="#059669" font-family="Arial">✓ 类目识别：EN 71 玩具指令</text>
    <text x="42" y="240" font-size="11" fill="#059669" font-family="Arial">✓ EAN 校验位通过</text>
    <text x="42" y="262" font-size="11" fill="#dc2626" font-family="Arial">✗ 欧代信息缺失</text>
    <text x="42" y="284" font-size="11" fill="#dc2626" font-family="Arial">✗ 警示语缺失（de）</text>
    <text x="42" y="306" font-size="11" fill="#dc2626" font-family="Arial">✗ 制造商信息不完整</text>
    <rect x="314" y="170" width="280" height="150" rx="10" fill="#eff6ff" stroke="#bfdbfe"/>
    <text x="330" y="194" font-size="12" font-weight="700" fill="#1d4ed8" font-family="Arial">生成的 GPSR 合规块（可粘贴）</text>
    <rect x="330" y="204" width="248" height="18" rx="4" fill="#dbeafe"/>
    <text x="338" y="217" font-size="10" fill="#1e3a8a" font-family="Arial">EU Responsible Person: CB-REP GmbH…</text>
    <rect x="330" y="228" width="248" height="18" rx="4" fill="#dbeafe"/>
    <text x="338" y="241" font-size="10" fill="#1e3a8a" font-family="Arial">Warnhinweis: Achtung! Nicht für Kinder…</text>
    <rect x="330" y="252" width="248" height="18" rx="4" fill="#dbeafe"/>
    <text x="338" y="265" font-size="10" fill="#1e3a8a" font-family="Arial">Hersteller: … · EAN: 4xxxxxxxxxxx</text>
    <rect x="330" y="282" width="110" height="24" rx="12" fill="#2563eb"/>
    <text x="385" y="298" text-anchor="middle" font-size="11" font-weight="700" fill="#fff" font-family="Arial">复制合规块</text>
    <rect x="450" y="282" width="128" height="24" rx="12" fill="#fff" stroke="#bfdbfe"/>
    <text x="514" y="298" text-anchor="middle" font-size="11" font-weight="700" fill="#1d4ed8" font-family="Arial">API 回填 13 平台</text>
    <rect x="26" y="336" width="568" height="64" rx="10" fill="#f0fdf4" stroke="#bbf7d0"/>
    <text x="44" y="362" font-size="12" font-weight="700" fill="#065f46" font-family="Arial">🛡 7x24 监控已开启</text>
    <text x="44" y="382" font-size="11" fill="#166534" font-family="Arial">规则更新自动复检 · 安全事件 15 天 Safety Gate 上报提示 · 风险日报推送</text>
    """
        return _MOCKUP_SHELL.format(alt="GPSR 合规体检报告", title="GPSR 合规引擎", body=body)

    _M_GPSR = {
        "en": dict(
            alt="GPSR compliance check report", title="GPSR compliance engine",
            risk="⚠ Check found 3 GPSR risks — EU 2023/988",
            sub="toys category · missing EU Rep · missing German choking warning · delisting risk",
            chk="Check items",
            ok1="✓ category detection: EN 71 toys directive",
            ok2="✓ EAN check digit passed",
            no1="✗ EU Rep information missing",
            no2="✗ safety warning missing (de)",
            no3="✗ manufacturer info incomplete",
            block="Generated GPSR compliance block (paste-ready)",
            copy="Copy block",
            api="API backfill · 13 platforms",
            mon="🛡 7×24 monitoring on",
            mond="auto re-check on rule updates · safety events reported to Safety Gate within 15 days · daily risk report"),
        "de": dict(
            alt="GPSR-Compliance-Prüfbericht", title="GPSR-Compliance-Engine",
            risk="⚠ Der Check fand 3 GPSR-Risiken — EU 2023/988",
            sub="Spielzeug-Kategorie · EU-Verantwortlicher fehlt · deutscher Warnhinweis fehlt · De-Listing-Risiko",
            chk="Prüfpunkte",
            ok1="✓ Kategorienennung: EN-71-Spielzeug-Richtlinie",
            ok2="✓ EAN-Prüfziffer geprüft",
            no1="✗ Angaben zum EU-Verantwortlichen fehlen",
            no2="✗ Sicherheitshinweis fehlt (de)",
            no3="✗ Herstellerangaben unvollständig",
            block="Erzeugter GPSR-Compliance-Block (einfügbar)",
            copy="Block kopieren",
            api="API-Backfill · 13 Plattformen",
            mon="🛡 7×24-Überwachung aktiv",
            mond="automatische Wiederholung bei Regel-Updates · Sicherheitsereignisse innerhalb von 15 Tagen an das Safety Gate gemeldet · täglicher Risikobericht"),
        "fr": dict(
            alt="rapport de vérification GPSR", title="moteur de conformité GPSR",
            risk="⚠ La vérification a trouvé 3 risques GPSR — EU 2023/988",
            sub="catégorie jouets · représentant UE manquant · avertissement allemand manquant · risque de déréférencement",
            chk="Points de contrôle",
            ok1="✓ détection catégorie : directive jouets EN 71",
            ok2="✓ chiffre de contrôle EAN validé",
            no1="✗ informations du représentant UE manquantes",
            no2="✗ avertissement de sécurité manquant (de)",
            no3="✗ infos fabricant incomplètes",
            block="Bloc de conformité GPSR généré (prêt à coller)",
            copy="Copier le bloc",
            api="backfill API · 13 plateformes",
            mon="🛡 surveillance 7×24 activée",
            mond="re-vérification auto lors des mises à jour de règles · signalement Safety Gate sous 15 jours · rapport de risque quotidien"),
    }
    t = _M_GPSR[lang]
    body = f"""
    <rect x="26" y="98" width="568" height="60" rx="10" fill="#fff5f5" stroke="#fecaca"/>
    <text x="44" y="122" font-size="13" font-weight="700" fill="#dc2626" font-family="Arial">{t["risk"]}</text>
    <text x="44" y="142" font-size="11" fill="#7f1d1d" font-family="Arial">{t["sub"]}</text>
    <rect x="26" y="170" width="272" height="150" rx="10" fill="#f8fafc" stroke="#e2e8f0"/>
    <text x="42" y="194" font-size="12" font-weight="700" fill="#0f172a" font-family="Arial">{t["chk"]}</text>
    <text x="42" y="218" font-size="11" fill="#059669" font-family="Arial">{t["ok1"]}</text>
    <text x="42" y="240" font-size="11" fill="#059669" font-family="Arial">{t["ok2"]}</text>
    <text x="42" y="262" font-size="11" fill="#dc2626" font-family="Arial">{t["no1"]}</text>
    <text x="42" y="284" font-size="11" fill="#dc2626" font-family="Arial">{t["no2"]}</text>
    <text x="42" y="306" font-size="11" fill="#dc2626" font-family="Arial">{t["no3"]}</text>
    <rect x="314" y="170" width="280" height="150" rx="10" fill="#eff6ff" stroke="#bfdbfe"/>
    <text x="330" y="194" font-size="12" font-weight="700" fill="#1d4ed8" font-family="Arial">{t["block"]}</text>
    <rect x="330" y="204" width="248" height="18" rx="4" fill="#dbeafe"/>
    <text x="338" y="217" font-size="10" fill="#1e3a8a" font-family="Arial">EU Responsible Person: CB-REP GmbH…</text>
    <rect x="330" y="228" width="248" height="18" rx="4" fill="#dbeafe"/>
    <text x="338" y="241" font-size="10" fill="#1e3a8a" font-family="Arial">Warnhinweis: Achtung! Nicht für Kinder…</text>
    <rect x="330" y="252" width="248" height="18" rx="4" fill="#dbeafe"/>
    <text x="338" y="265" font-size="10" fill="#1e3a8a" font-family="Arial">Hersteller: … · EAN: 4xxxxxxxxxxx</text>
    <rect x="330" y="282" width="110" height="24" rx="12" fill="#2563eb"/>
    <text x="385" y="298" text-anchor="middle" font-size="11" font-weight="700" fill="#fff" font-family="Arial">{t["copy"]}</text>
    <rect x="450" y="282" width="128" height="24" rx="12" fill="#fff" stroke="#bfdbfe"/>
    <text x="514" y="298" text-anchor="middle" font-size="11" font-weight="700" fill="#1d4ed8" font-family="Arial">{t["api"]}</text>
    <rect x="26" y="336" width="568" height="64" rx="10" fill="#f0fdf4" stroke="#bbf7d0"/>
    <text x="44" y="362" font-size="12" font-weight="700" fill="#065f46" font-family="Arial">{t["mon"]}</text>
    <text x="44" y="382" font-size="11" fill="#166534" font-family="Arial">{t["mond"]}</text>
    """
    return _MOCKUP_SHELL.format(alt=t["alt"], title=t["title"], body=body)


def _m_generator(lang: str = "zh") -> str:
    body = """
    <rect x="26" y="98" width="150" height="60" rx="10" fill="#eff6ff" stroke="#bfdbfe"/>
    <text x="101" y="124" text-anchor="middle" font-size="12" font-weight="700" fill="#1d4ed8" font-family="Arial">输入产品</text>
    <text x="101" y="144" text-anchor="middle" font-size="11" fill="#334155" font-family="Arial">Wireless Headphones</text>
    <path d="M186 128 h30" stroke="#94a3b8" stroke-width="2" marker-end="url(#arr)"/>
    <defs><marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6" fill="none" stroke="#94a3b8"/></marker></defs>
    <rect x="224" y="98" width="370" height="60" rx="10" fill="#f8fafc" stroke="#e2e8f0"/>
    <text x="240" y="122" font-size="12" font-weight="700" fill="#0f172a" font-family="Arial">平台规则自动匹配</text>
    <text x="240" y="142" font-size="11" fill="#475569" font-family="Arial">Otto ≤70 · Allegro ≤75 · Amazon ≤200 字符 · de/pl/en</text>
    <rect x="26" y="172" width="568" height="118" rx="10" fill="#fff" stroke="#e2e8f0"/>
    <text x="42" y="196" font-size="12" font-weight="700" fill="#0f172a" font-family="Arial">标题（Otto · 德语） 47/70 字符</text>
    <rect x="42" y="206" width="300" height="8" rx="4" fill="#e2e8f0"/>
    <rect x="42" y="206" width="204" height="8" rx="4" fill="#059669"/>
    <text x="42" y="234" font-size="11.5" fill="#334155" font-family="Arial">Kabellose Noise-Cancelling Kopfhörer, Bluetooth 5.3, 40h…</text>
    <text x="42" y="262" font-size="12" font-weight="700" fill="#0f172a" font-family="Arial">五点描述（5/5） · 详情 · 搜索词 已生成</text>
    <rect x="42" y="272" width="90" height="12" rx="6" fill="#f1f5f9"/><rect x="140" y="272" width="70" height="12" rx="6" fill="#f1f5f9"/><rect x="218" y="272" width="110" height="12" rx="6" fill="#f1f5f9"/>
    <rect x="26" y="304" width="272" height="42" rx="10" fill="#fff" stroke="#e2e8f0"/>
    <text x="42" y="322" font-size="11" font-weight="700" fill="#0f172a" font-family="Arial">硬校验</text>
    <text x="42" y="338" font-size="10.5" fill="#059669" font-family="Arial">✓ 字数 ✓ 语言 ✓ 结构 ✓ GPSR 内嵌</text>
    <rect x="314" y="304" width="280" height="42" rx="10" fill="#f0fdf4" stroke="#bbf7d0"/>
    <text x="330" y="322" font-size="11" font-weight="700" fill="#065f46" font-family="Arial">完整度评分 94/100</text>
    <text x="330" y="338" font-size="10.5" fill="#166534" font-family="Arial">可直接复制到卖家中心 · 16 语言可选</text>
    <text x="310" y="382" text-anchor="middle" font-size="11" fill="#94a3b8" font-family="Arial">Free 每天 5 次 · Starter 起 GPSR 合规块内嵌输出</text>
    """
    svg = _MOCKUP_SHELL.format(alt="Listing 生成器界面", title="Listing 生成器", body=body)
    return _mockup_i18n(svg, "generator", lang)


def _m_matrix(lang: str = "zh") -> str:
    tiles = ""
    data = [
        ("Amazon EU", "#FF9900", "en/de/fr/it/es"), ("Amazon US", "#FF9900", "en"),
        ("eBay", "#0064D2", "en/de/fr"), ("Allegro", "#FF5A00", "pl/cs/sk"),
        ("Otto", "#D4021D", "de"), ("Cdiscount", "#004890", "fr"),
        ("eMAG", "#005B94", "ro/hu/bg"), ("TikTok Shop", "#010101", "en/es/it"),
        ("Fruugo", "#94C11F", "泛欧 20+ 国"), ("Walmart", "#0071CE", "en"),
        ("Kaufland", "#E10911", "de/cs/sk"), ("Zalando", "#FF6900", "en→多语言"),
        ("bol.com", "#0000A4", "nl"),
    ]
    x0, y0 = 26, 172
    for i, (name, color, p_lang) in enumerate(data):
        cx = x0 + (i % 5) * 115
        cy = y0 + (i // 5) * 78
        tiles += (
            f'<rect x="{cx}" y="{cy}" width="106" height="66" rx="10" fill="#fff" stroke="#e2e8f0"/>'
            f'<rect x="{cx}" y="{cy}" width="106" height="26" rx="10" fill="{color}" opacity="0.14"/>'
            f'<circle cx="{cx+14}" cy="{cy+13}" r="4" fill="{color}"/>'
            f'<text x="{cx+24}" y="{cy+17}" font-size="10.5" font-weight="700" fill="#0f172a" font-family="Arial">{name}</text>'
            f'<text x="{cx+10}" y="{cy+45}" font-size="9.5" fill="#475569" font-family="Arial">{p_lang}</text>'
            f'<text x="{cx+10}" y="{cy+58}" font-size="9" fill="#059669" font-family="Arial">✓ 已生成</text>'
        )
    body = f"""
    <rect x="26" y="98" width="240" height="60" rx="10" fill="#eff6ff" stroke="#bfdbfe"/>
    <text x="42" y="122" font-size="12" font-weight="700" fill="#1d4ed8" font-family="Arial">输入一次产品信息</text>
    <text x="42" y="142" font-size="11" fill="#334155" font-family="Arial">标题 + 关键词 + 属性（品牌/EAN/材质）</text>
    <path d="M272 128 h30" stroke="#94a3b8" stroke-width="2"/>
    <rect x="308" y="98" width="286" height="60" rx="10" fill="#f5f3ff" stroke="#ddd6fe"/>
    <text x="324" y="122" font-size="12" font-weight="700" fill="#6d28d9" font-family="Arial">13 平台规则内置 · 16 语言自动匹配</text>
    <text x="324" y="142" font-size="11" fill="#475569" font-family="Arial">不绑店 · 独立工作台 · 结果逐平台可编辑</text>
    {tiles}
    <text x="310" y="404" text-anchor="middle" font-size="11" fill="#94a3b8" font-family="Arial">Allegro / eMAG / Cdiscount / Fruugo —— 主流工具覆盖率为零，CrossAIO 率先补齐</text>
    """
    svg = _MOCKUP_SHELL.format(alt="13 平台矩阵批量生成", title="多平台矩阵", body=body)
    return _mockup_i18n(svg, "matrix", lang)


def _m_review(lang: str = "zh") -> str:
    body = """
    <rect x="26" y="98" width="268" height="140" rx="10" fill="#fff5f5" stroke="#fecaca"/>
    <text x="42" y="122" font-size="12" font-weight="700" fill="#dc2626" font-family="Arial">⭐ 差评输入（1 星）</text>
    <text x="42" y="146" font-size="10.5" fill="#7f1d1d" font-family="Arial">"左耳三个月就断了一个角，客服</text>
    <text x="42" y="163" font-size="10.5" fill="#7f1d1d" font-family="Arial">只说重新买。充电盒也过热。"</text>
    <rect x="42" y="178" width="76" height="18" rx="9" fill="#fee2e2"/>
    <text x="80" y="191" text-anchor="middle" font-size="9.5" font-weight="700" fill="#b91c1c" font-family="Arial">主题：材质</text>
    <rect x="126" y="178" width="76" height="18" rx="9" fill="#fee2e2"/>
    <text x="164" y="191" text-anchor="middle" font-size="9.5" font-weight="700" fill="#b91c1c" font-family="Arial">主题：过热⚠</text>
    <text x="42" y="220" font-size="10" fill="#dc2626" font-family="Arial">⚠ 安全诉求 → 触发 GPSR 事件预警</text>
    <path d="M300 168 h24" stroke="#94a3b8" stroke-width="2"/>
    <rect x="330" y="98" width="264" height="140" rx="10" fill="#f0fdf4" stroke="#bbf7d0"/>
    <text x="346" y="122" font-size="12" font-weight="700" fill="#065f46" font-family="Arial">修复建议 + 五点改写</text>
    <text x="346" y="146" font-size="10.5" fill="#166534" font-family="Arial">五点② 改写：增加 "增强铰链结构，</text>
    <text x="346" y="163" font-size="10.5" fill="#166534" font-family="Arial">通过 5,000 次开合测试"</text>
    <text x="346" y="187" font-size="10.5" fill="#166534" font-family="Arial">五点④ 改写：增加 "过热保护认证"</text>
    <rect x="346" y="202" width="120" height="22" rx="11" fill="#059669"/>
    <text x="406" y="217" text-anchor="middle" font-size="10" font-weight="700" fill="#fff" font-family="Arial">生成新版本</text>
    <rect x="26" y="254" width="568" height="80" rx="10" fill="#fff" stroke="#e2e8f0"/>
    <text x="42" y="278" font-size="12" font-weight="700" fill="#0f172a" font-family="Arial">语义评分（Rufus / iZi 适配）</text>
    <rect x="42" y="292" width="120" height="16" rx="4" fill="#f1f5f9"/><rect x="170" y="292" width="120" height="16" rx="4" fill="#f1f5f9"/><rect x="298" y="292" width="120" height="16" rx="4" fill="#f1f5f9"/><rect x="426" y="292" width="120" height="16" rx="4" fill="#f1f5f9"/>
    <text x="48" y="304" font-size="9" fill="#475569" font-family="Arial">尺寸 8/10</text>
    <text x="176" y="304" font-size="9" fill="#475569" font-family="Arial">耐用性 5→8/10</text>
    <text x="304" y="304" font-size="9" fill="#475569" font-family="Arial">安全 4→9/10</text>
    <text x="432" y="304" font-size="9" fill="#475569" font-family="Arial">续航 9/10</text>
    <text x="42" y="326" font-size="10" fill="#64748b" font-family="Arial">8 类买家问题覆盖度逐项量化 · 改写后复评追踪提升</text>
    <text x="310" y="368" text-anchor="middle" font-size="11" fill="#94a3b8" font-family="Arial">8 类主题定位 · 安全类差评自动走 GPSR 合规优先流程</text>
    """
    svg = _MOCKUP_SHELL.format(alt="差评分析与五点改写", title="差评改写闭环", body=body)
    return _mockup_i18n(svg, "review", lang)


def _m_inbox(lang: str = "zh") -> str:
    body = """
    <rect x="26" y="98" width="180" height="300" rx="10" fill="#f8fafc" stroke="#e2e8f0"/>
    <text x="42" y="122" font-size="12" font-weight="700" fill="#0f172a" font-family="Arial">统一收件箱</text>
    <rect x="38" y="136" width="156" height="40" rx="8" fill="#eff6ff" stroke="#bfdbfe"/>
    <text x="48" y="152" font-size="10" font-weight="700" fill="#1d4ed8" font-family="Arial">eBay · de 🇩🇪</text>
    <text x="48" y="168" font-size="9.5" fill="#475569" font-family="Arial">Kaputt nach 2 Wochen…</text>
    <rect x="38" y="184" width="156" height="40" rx="8" fill="#fff" stroke="#e2e8f0"/>
    <text x="48" y="200" font-size="10" font-weight="700" fill="#0f172a" font-family="Arial">Allegro · pl 🇵🇱</text>
    <text x="48" y="216" font-size="9.5" fill="#475569" font-family="Arial">Gdzie jest oświadczenie…</text>
    <rect x="38" y="232" width="156" height="40" rx="8" fill="#fff5f5" stroke="#fecaca"/>
    <text x="48" y="248" font-size="10" font-weight="700" fill="#dc2626" font-family="Arial">Cdiscount · fr 🇫🇷 ⚠</text>
    <text x="48" y="264" font-size="9.5" fill="#b91c1c" font-family="Arial">Produit en feu ! — 安全事件</text>
    <rect x="38" y="280" width="156" height="40" rx="8" fill="#fff" stroke="#e2e8f0"/>
    <text x="48" y="296" font-size="10" font-weight="700" fill="#0f172a" font-family="Arial">eMAG · ro 🇷🇴</text>
    <text x="48" y="312" font-size="9.5" fill="#475569" font-family="Arial">Când sosește comanda…</text>
    <rect x="222" y="98" width="372" height="230" rx="10" fill="#fff" stroke="#e2e8f0"/>
    <rect x="240" y="116" width="230" height="34" rx="8" fill="#f1f5f9"/>
    <text x="250" y="130" font-size="9.5" fill="#0f172a" font-family="Arial">Kunde: Das Kopfhörer ist nach 2 Wochen kaputt.</text>
    <text x="250" y="144" font-size="9.5" fill="#0f172a" font-family="Arial">Was können Sie tun?</text>
    <rect x="256" y="162" width="320" height="86" rx="8" fill="#eff6ff" stroke="#bfdbfe"/>
    <rect x="266" y="172" width="132" height="18" rx="9" fill="#2563eb"/>
    <text x="332" y="185" text-anchor="middle" font-size="9" font-weight="700" fill="#fff" font-family="Arial">AI 草稿 · Art.50 已披露 ✓</text>
    <text x="266" y="206" font-size="9.5" fill="#1e3a8a" font-family="Arial">Guten Tag, es tut uns sehr leid…</text>
    <text x="266" y="222" font-size="9.5" fill="#1e3a8a" font-family="Arial">[AI Act Art.50 disclosure · DE]</text>
    <text x="266" y="238" font-size="9.5" fill="#1e3a8a" font-family="Arial">替换/退款方案 + 欧代联系方式</text>
    <rect x="256" y="282" width="104" height="24" rx="12" fill="#059669"/>
    <text x="308" y="298" text-anchor="middle" font-size="10" font-weight="700" fill="#fff" font-family="Arial">确认发送</text>
    <rect x="370" y="282" width="104" height="24" rx="12" fill="#fff" stroke="#cbd5e1"/>
    <text x="422" y="298" text-anchor="middle" font-size="10" font-weight="700" fill="#475569" font-family="Arial">编辑草稿</text>
    <rect x="222" y="340" width="372" height="58" rx="10" fill="#fff5f5" stroke="#fecaca"/>
    <text x="238" y="364" font-size="10.5" font-weight="700" fill="#dc2626" font-family="Arial">⚠ 红线拦截：fr 会话命中「安全事件」</text>
    <text x="238" y="382" font-size="9.5" fill="#b91c1c" font-family="Arial">自动切换合规优先回复 · 15 天 Safety Gate 提示 · 强制转人工</text>
    """
    svg = _MOCKUP_SHELL.format(alt="统一收件箱与 Art.50 披露", title="AI 客服 · 统一收件箱", body=body)
    return _mockup_i18n(svg, "inbox", lang)


def _m_ad(lang: str = "zh") -> str:
    body = """
    <rect x="26" y="98" width="268" height="150" rx="10" fill="#eff6ff" stroke="#bfdbfe"/>
    <text x="42" y="122" font-size="12" font-weight="700" fill="#1e40af" font-family="Arial">📣 广告标题生成（SP 广告位）</text>
    <text x="42" y="146" font-size="10.5" fill="#1e3a8a" font-family="Arial">A：Wireless Earbuds, 40H Playtime,</text>
    <text x="42" y="163" font-size="10.5" fill="#1e3a8a" font-family="Arial">IPX5 Waterproof — DE 站德语版</text>
    <text x="42" y="187" font-size="10.5" fill="#1e3a8a" font-family="Arial">B：Kabellose Ohrhörer, 40H Akku,</text>
    <text x="42" y="204" font-size="10.5" fill="#1e3a8a" font-family="Arial">Wasserdicht IPX5（A/B 变体）</text>
    <rect x="42" y="220" width="64" height="18" rx="9" fill="#dbeafe"/>
    <text x="74" y="233" text-anchor="middle" font-size="9.5" font-weight="700" fill="#1d4ed8" font-family="Arial">A/B 测试</text>
    <path d="M300 168 h24" stroke="#94a3b8" stroke-width="2"/>
    <rect x="330" y="98" width="264" height="150" rx="10" fill="#fff7ed" stroke="#fed7aa"/>
    <text x="346" y="122" font-size="12" font-weight="700" fill="#9a3412" font-family="Arial">🚫 禁用词前置拦截</text>
    <text x="346" y="146" font-size="10.5" fill="#9a3412" font-family="Arial">"Best Wireless Earbuds 2026"</text>
    <text x="346" y="166" font-size="10.5" fill="#b45309" font-family="Arial">→ best / 年份夸大 · 违反广告政策</text>
    <text x="346" y="190" font-size="10.5" fill="#9a3412" font-family="Arial">字数：标题 ≤ 50 字符 ✓</text>
    <text x="346" y="210" font-size="10.5" fill="#9a3412" font-family="Arial">联系方式 / 促销堆叠：已剔除 ✓</text>
    <rect x="346" y="222" width="118" height="20" rx="10" fill="#ea580c"/>
    <text x="405" y="236" text-anchor="middle" font-size="10" font-weight="700" fill="#fff" font-family="Arial">重新生成合规版</text>
    <rect x="26" y="264" width="568" height="76" rx="10" fill="#fff" stroke="#e2e8f0"/>
    <text x="42" y="288" font-size="12" font-weight="700" fill="#0f172a" font-family="Arial">多平台多语言输出</text>
    <rect x="42" y="300" width="84" height="22" rx="6" fill="#f1f5f9"/><rect x="134" y="300" width="84" height="22" rx="6" fill="#f1f5f9"/><rect x="226" y="300" width="84" height="22" rx="6" fill="#f1f5f9"/><rect x="318" y="300" width="84" height="22" rx="6" fill="#f1f5f9"/><rect x="410" y="300" width="84" height="22" rx="6" fill="#f1f5f9"/>
    <text x="84" y="315" text-anchor="middle" font-size="9" fill="#475569" font-family="Arial">Amazon DE</text>
    <text x="176" y="315" text-anchor="middle" font-size="9" fill="#475569" font-family="Arial">Amazon FR</text>
    <text x="268" y="315" text-anchor="middle" font-size="9" fill="#475569" font-family="Arial">Allegro PL</text>
    <text x="360" y="315" text-anchor="middle" font-size="9" fill="#475569" font-family="Arial">Otto DE</text>
    <text x="452" y="315" text-anchor="middle" font-size="9" fill="#475569" font-family="Arial">bol NL</text>
    <text x="310" y="368" text-anchor="middle" font-size="11" fill="#94a3b8" font-family="Arial">禁用词前置拦截 · 字数硬校验 · 8 市场文化画像改写</text>
    """
    svg = _MOCKUP_SHELL.format(alt="广告文案生成与禁用词拦截", title="广告文案生成", body=body)
    return _mockup_i18n(svg, "ad", lang)


def _m_watch(lang: str = "zh") -> str:
    body = """
    <rect x="26" y="98" width="568" height="52" rx="10" fill="#eff6ff" stroke="#bfdbfe"/>
    <text x="42" y="120" font-size="12" font-weight="700" fill="#1e40af" font-family="Arial">📡 今日体检 · 12 个 Listing · 2 项风险升级</text>
    <text x="42" y="138" font-size="10" fill="#1e3a8a" font-family="Arial">每日 08:00 定时运行 · 逐项比对字数 / 合规块 / 差评 / 语义评分</text>
    <rect x="26" y="162" width="184" height="120" rx="10" fill="#fff5f5" stroke="#fecaca"/>
    <text x="42" y="184" font-size="11" font-weight="800" fill="#dc2626" font-family="Arial">🔴 致命</text>
    <text x="42" y="206" font-size="10" fill="#7f1d1d" font-family="Arial">Bluetooth 耳机（DE 站）</text>
    <text x="42" y="224" font-size="10" fill="#7f1d1d" font-family="Arial">GPSR 合规块消失</text>
    <text x="42" y="246" font-size="9.5" fill="#b91c1c" font-family="Arial">→ 平台改写吞块 · 立即修复</text>
    <rect x="42" y="256" width="90" height="18" rx="9" fill="#dc2626"/>
    <text x="87" y="269" text-anchor="middle" font-size="9" font-weight="700" fill="#fff" font-family="Arial">一键修复</text>
    <rect x="218" y="162" width="184" height="120" rx="10" fill="#fff7ed" stroke="#fed7aa"/>
    <text x="234" y="184" font-size="11" font-weight="800" fill="#c2410c" font-family="Arial">🟠 高</text>
    <text x="234" y="206" font-size="10" fill="#7c2d12" font-family="Arial">充电盒（FR 站）新差评</text>
    <text x="234" y="224" font-size="10" fill="#7c2d12" font-family="Arial">"surchauffe（过热）"</text>
    <text x="234" y="246" font-size="9.5" fill="#c2410c" font-family="Arial">→ 命中事故词库 · GPSR 事件</text>
    <text x="234" y="266" font-size="9.5" fill="#c2410c" font-family="Arial">15 天 Safety Gate 窗口内</text>
    <rect x="410" y="162" width="184" height="120" rx="10" fill="#f0fdf4" stroke="#bbf7d0"/>
    <text x="426" y="184" font-size="11" font-weight="800" fill="#047857" font-family="Arial">🟢 正常 10 项</text>
    <text x="426" y="206" font-size="10" fill="#065f46" font-family="Arial">字数漂移 0 · 合规块完整</text>
    <text x="426" y="224" font-size="10" fill="#065f46" font-family="Arial">语义评分均值 82（+1）</text>
    <text x="426" y="246" font-size="9.5" fill="#047857" font-family="Arial">差评主题：无线充（非安全类）</text>
    <text x="310" y="368" text-anchor="middle" font-size="11" fill="#94a3b8" font-family="Arial">风险升级 → SMTP 邮件日报直达 · 差评主题一键转差评改写闭环</text>
    """
    svg = _MOCKUP_SHELL.format(alt="Listing 每日体检与风险分级日报", title="Listing 监控日报", body=body)
    return _mockup_i18n(svg, "watch", lang)


def _m_redline(lang: str = "zh") -> str:
    body = """
    <rect x="26" y="98" width="568" height="66" rx="10" fill="#fff5f5" stroke="#fecaca"/>
    <text x="44" y="124" font-size="13" font-weight="800" fill="#dc2626" font-family="Arial">🚨 红线层命中：人身伤害诉求（置信度 0.97）</text>
    <text x="44" y="146" font-size="11" fill="#7f1d1d" font-family="Arial">"充电时充电盒冒烟，孩子当时在旁边" — 自动回复已阻止</text>
    <rect x="26" y="180" width="170" height="90" rx="10" fill="#fff" stroke="#e2e8f0"/>
    <text x="42" y="206" font-size="11.5" font-weight="700" fill="#0f172a" font-family="Arial">1 · 拦截自动回复</text>
    <text x="42" y="228" font-size="10" fill="#475569" font-family="Arial">消息标记为安全事件</text>
    <text x="42" y="246" font-size="10" fill="#475569" font-family="Arial">不走 AI 草稿流程</text>
    <path d="M200 225 h20" stroke="#94a3b8" stroke-width="2"/>
    <rect x="224" y="180" width="170" height="90" rx="10" fill="#fff" stroke="#e2e8f0"/>
    <text x="240" y="206" font-size="11.5" font-weight="700" fill="#0f172a" font-family="Arial">2 · 安抚 + 转人工</text>
    <text x="240" y="228" font-size="10" fill="#475569" font-family="Arial">安抚话术 · 留证要点提示</text>
    <text x="240" y="246" font-size="10" fill="#475569" font-family="Arial">订单号 / 消息原文 / 截图</text>
    <path d="M398 225 h20" stroke="#94a3b8" stroke-width="2"/>
    <rect x="422" y="180" width="172" height="90" rx="10" fill="#fff" stroke="#e2e8f0"/>
    <text x="438" y="206" font-size="11.5" font-weight="700" fill="#0f172a" font-family="Arial">3 · GPSR 事件流程</text>
    <text x="438" y="228" font-size="10" fill="#475569" font-family="Arial">停售评估建议</text>
    <text x="438" y="246" font-size="10" fill="#475569" font-family="Arial">15 天 Safety Gate 提示</text>
    <rect x="26" y="288" width="568" height="56" rx="10" fill="#eff6ff" stroke="#bfdbfe"/>
    <text x="44" y="312" font-size="11.5" font-weight="700" fill="#1d4ed8" font-family="Arial">留证时间线（可审计）</text>
    <text x="44" y="332" font-size="10" fill="#1e3a8a" font-family="Arial">14:02 识别拦截 → 14:02 转人工 → 14:15 GPSR 流程开启 → 上报倒计时 D-15</text>
    <rect x="26" y="358" width="568" height="42" rx="10" fill="#f0fdf4" stroke="#bbf7d0"/>
    <text x="44" y="384" font-size="11" fill="#065f46" font-family="Arial">✓ 红线回复同样内嵌 AI Act Art.50 披露 · 合规层无死角 · 高风险 100% 转人工</text>
    """
    svg = _MOCKUP_SHELL.format(alt="安全红线拦截流程", title="政策安全红线层", body=body)
    return _mockup_i18n(svg, "redline", lang)


_MOCKUPS = {
    "gpsr": _m_gpsr,
    "generator": _m_generator,
    "matrix": _m_matrix,
    "review": _m_review,
    "inbox": _m_inbox,
    "redline": _m_redline,
    "ad": _m_ad,
    "watch": _m_watch,
}

# ---------------------------------------------------------------------------
# 共享 CSS（首页同款导航/设计语言）
# ---------------------------------------------------------------------------

_CSS = """
  :root{--ink:#0f172a;--muted:#64748b;--border:#e2e8f0;--bg:#fff;--soft:#f8fafc;
    --blue:#2563eb;--blue-light:#3b82f6;--blue-dark:#1d4ed8;--purple:#8b5cf6;--ok:#059669;--err:#dc2626}
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:Inter,"Segoe UI","Microsoft YaHei",system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--ink);line-height:1.7}
  a{text-decoration:none;color:inherit}
  nav{display:flex;justify-content:space-between;align-items:center;padding:12px 32px;max-width:1240px;margin:0 auto;position:relative;z-index:60}
  .logo{font-weight:800;font-size:19px;display:flex;align-items:center;gap:8px}
  .logo .dot{width:28px;height:28px;border-radius:8px;background:linear-gradient(135deg,var(--blue),var(--purple));display:inline-flex;align-items:center;justify-content:center;color:#fff;font-size:15px}
  .menu{display:flex;gap:6px}
  .navitem{position:relative}
  .navitem>a{display:flex;align-items:center;gap:5px;font-size:14.5px;font-weight:600;color:var(--ink);padding:12px 14px;border-radius:8px;cursor:pointer}
  .navitem>a.solo::after{display:none}
  .navitem>a::after{content:"";width:7px;height:7px;border-right:1.6px solid var(--muted);border-bottom:1.6px solid var(--muted);transform:rotate(45deg) translateY(-2px);transition:transform .15s}
  .navitem:hover>a{background:#f1f5f9}
  .navitem:hover>a::after{transform:rotate(-135deg) translateY(-1px)}
  .navitem.active>a{color:var(--blue)}
  .dropdown{position:absolute;top:100%;left:8px;min-width:280px;background:#fff;border-radius:12px;
    box-shadow:0 18px 50px rgba(15,23,42,.16);padding:8px;opacity:0;visibility:hidden;transform:translateY(8px);transition:.18s}
  .navitem:hover .dropdown{opacity:1;visibility:visible;transform:translateY(0)}
  .dropdown a{display:flex;justify-content:space-between;align-items:center;font-size:13.5px;font-weight:600;color:#334155;padding:11px 14px;border-radius:8px}
  .dropdown a:hover{background:#eff6ff;color:var(--blue)}
  .dropdown a.on{background:#eff6ff;color:var(--blue)}
  .dropdown a::after{content:"›";color:#cbd5e1;font-size:16px}
  .dropdown a small{display:block;font-weight:400;font-size:11.5px;color:var(--muted)}
  nav .right{display:flex;gap:14px;align-items:center}
  .login-link{font-size:14px;color:var(--muted)}
  .login-link:hover{color:var(--ink)}
  .pill-nav{background:var(--blue);color:#fff;border-radius:999px;padding:9px 20px;font-size:13.5px;font-weight:700;cursor:pointer;border:none}
  .pill-nav:hover{background:var(--blue-dark)}
  .pill-nav.ghost{background:transparent;color:var(--ink);border:1.5px solid var(--border)}
  .pill-nav.ghost:hover{border-color:var(--blue);color:var(--blue)}

  .hero-wrap{background:radial-gradient(1100px 600px at 78% 30%,rgba(124,58,237,.45),transparent 62%),
       radial-gradient(900px 500px at 10% 100%,rgba(29,78,216,.35),transparent 55%),
       linear-gradient(115deg,#0a0f2e 0%,#141040 48%,#3b1a86 100%)}
  .hero{max-width:1240px;margin:0 auto;padding:64px 32px 80px;display:grid;grid-template-columns:1fr 1fr;gap:44px;align-items:center;color:#fff}
  .eyebrow{display:inline-flex;align-items:center;gap:8px;font-size:12.5px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#c4b5fd;margin-bottom:16px;background:rgba(139,92,246,.16);padding:6px 14px;border-radius:999px}
  .hero h1{font-size:40px;line-height:1.22;font-weight:800;letter-spacing:-.01em;margin-bottom:16px}
  .hero h1 em{font-style:normal;color:#a5b4fc}
  .hero p.sub{font-size:15.5px;color:#d3d9ea;max-width:520px;margin-bottom:26px}
  .hero p.sub b{color:#fff}
  .cta-row{display:flex;gap:14px;flex-wrap:wrap}
  .pill-blue{background:var(--blue-light);color:#fff;border-radius:999px;padding:13px 30px;font-size:15px;font-weight:700;cursor:pointer;border:none;box-shadow:0 10px 28px rgba(59,130,246,.45);display:inline-block}
  .pill-blue:hover{background:var(--blue-dark)}
  .pill-ghost{background:transparent;color:#fff;border:1.5px solid rgba(255,255,255,.55);border-radius:999px;padding:12px 28px;font-size:15px;font-weight:600;cursor:pointer;display:inline-block}
  .pill-ghost:hover{border-color:#fff;background:rgba(255,255,255,.07)}
  .hero .tiny{margin-top:18px;font-size:12.5px;color:#9aa6c4}
  .mockup-cell{min-width:0}

  section{max-width:1100px;margin:0 auto;padding:56px 24px}
  .sec-head{margin-bottom:28px}
  .sec-eyebrow{font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--blue);margin-bottom:8px}
  .sec-title{font-size:28px;font-weight:800;letter-spacing:-.01em;margin-bottom:8px}
  .sec-sub{color:var(--muted);font-size:14.5px}

  .danger-band{background:#fff5f5;border:1px solid #fecaca;border-radius:16px;padding:26px 28px}
  .danger-band h2{color:var(--err);font-size:20px;font-weight:800;margin-bottom:14px}
  .danger-band ul{margin-left:20px}
  .danger-band li{font-size:14px;color:#7f1d1d;padding:4px 0}

  .capgroups{display:grid;grid-template-columns:1fr 1fr;gap:20px}
  .capgroup{background:#fff;border:1px solid var(--border);border-radius:14px;padding:22px 24px;box-shadow:0 6px 24px rgba(15,23,42,.05)}
  .capgroup h3{font-size:15px;font-weight:800;margin-bottom:12px;display:flex;align-items:center;gap:8px}
  .capgroup h3::before{content:"";width:8px;height:8px;border-radius:2px;background:var(--blue)}
  .capgroup.g2 h3::before{background:#0e7490}
  .capgroup.g3 h3::before{background:var(--purple)}
  .cap{padding:10px 0;border-top:1px dashed var(--border)}
  .cap:first-of-type{border-top:none}
  .cap b{display:block;font-size:14px;margin-bottom:2px}
  .cap span{font-size:12.5px;color:var(--muted)}

  .steps{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
  .step{background:var(--soft);border:1px solid var(--border);border-radius:14px;padding:24px 22px}
  .step .no{width:32px;height:32px;border-radius:50%;background:var(--blue);color:#fff;font-weight:800;display:flex;align-items:center;justify-content:center;margin-bottom:12px}
  .step h3{font-size:15px;margin-bottom:6px}
  .step p{font-size:13px;color:var(--muted)}

  .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;text-align:center}
  .stat .n{font-size:32px;font-weight:800;color:var(--blue)}
  .stat .l{font-size:12.5px;color:var(--muted)}

  /* ---- dynamic assets: keyframes & animations (mockup / flow diagram / stat cards / platform marquee) ---- */
  @keyframes cb-float{0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}
  @keyframes cb-pulse{0%,100%{opacity:1}50%{opacity:.35}}
  @keyframes cb-scan{0%{transform:translateY(64px);opacity:0}12%{opacity:.55}88%{opacity:.55}100%{transform:translateY(392px);opacity:0}}
  @keyframes cb-dash{to{stroke-dashoffset:-26}}
  @keyframes cb-fadeup{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
  @keyframes cb-grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
  @keyframes cb-shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}
  @keyframes cb-marquee{from{transform:translateX(0)}to{transform:translateX(-50%)}}
  .mk-float{animation:cb-float 6s ease-in-out infinite}
  .mk-dot{animation:cb-pulse 1.6s ease-in-out infinite}
  .mk-dot.d2{animation-delay:.3s}.mk-dot.d3{animation-delay:.6s}
  .mk-scan{animation:cb-scan 4.5s ease-in-out infinite;pointer-events:none}
  .fl-node{animation:cb-fadeup .6s ease-out both}
  .fl-node.n2{animation-delay:.35s}.fl-node.n3{animation-delay:.7s}
  .fl-line{stroke-dasharray:7 6;animation:cb-dash 1.1s linear infinite}
  .fl-arrow{animation:cb-fadeup .5s ease-out both;animation-delay:.5s}
  .stat{animation:cb-fadeup .6s ease-out both}
  .stat:nth-child(2){animation-delay:.15s}.stat:nth-child(3){animation-delay:.3s}.stat:nth-child(4){animation-delay:.45s}
  .stat .n{background:linear-gradient(90deg,var(--blue),var(--purple),var(--blue));background-size:200% 100%;
    -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;animation:cb-shimmer 4s linear infinite}
  .pm-track{display:flex;gap:14px;width:max-content;animation:cb-marquee 28s linear infinite}
  .pmarquee{overflow:hidden;position:relative;padding:6px 0;
    -webkit-mask-image:linear-gradient(90deg,transparent,#000 8%,#000 92%,transparent);
    mask-image:linear-gradient(90deg,transparent,#000 8%,#000 92%,transparent)}
  .pmarquee:hover .pm-track{animation-play-state:paused}
  .pm-chip{display:inline-flex;align-items:center;gap:7px;white-space:nowrap;border:1px solid var(--border);
    border-radius:999px;padding:8px 16px;font-size:13px;font-weight:600;color:#334155;background:#fff}
  .pm-chip small{color:var(--muted);font-weight:400}
  @media (prefers-reduced-motion: reduce){
    .mk-float,.mk-dot,.mk-scan,.fl-node,.fl-arrow,.stat,.pm-track,.stat .n{animation:none}
  }

  .tier{background:linear-gradient(135deg,#eff6ff,#f5f3ff);border:1px solid #bfdbfe;border-radius:16px;padding:26px 30px;display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap}
  .tier p{font-size:14.5px;font-weight:600;color:#1e3a8a}
  .tier a{background:var(--blue);color:#fff;border-radius:999px;padding:11px 26px;font-size:14px;font-weight:700}
  .tier a:hover{background:var(--blue-dark)}

  .faq{max-width:820px}
  .faq details{border:1px solid var(--border);border-radius:12px;margin-bottom:12px;background:#fff;overflow:hidden}
  .faq summary{padding:15px 20px;font-size:14.5px;font-weight:700;cursor:pointer;list-style:none}
  .faq summary::after{content:"+";float:right;color:var(--muted);font-weight:400}
  .faq details[open] summary::after{content:"–"}
  .faq .a{padding:0 20px 15px;font-size:13.5px;color:var(--muted)}
  .faq .a a{color:var(--blue);font-weight:600}

  .cta-band{background:linear-gradient(115deg,#0a0f2e,#3b1a86);border-radius:20px;max-width:1100px;margin:0 auto 64px;padding:48px 40px;text-align:center;color:#fff}
  .cta-band h2{font-size:26px;font-weight:800;margin-bottom:10px}
  .cta-band p{color:#c7d0e8;margin-bottom:22px;font-size:14.5px}

  .x-links{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;max-width:1100px;margin:0 auto;padding:0 24px 56px}
  .x-link{background:#fff;border:1px solid var(--border);border-radius:14px;padding:18px 20px;font-weight:800;font-size:14.5px;transition:.15s}
  .x-link:hover{border-color:var(--blue);box-shadow:0 8px 26px rgba(37,99,235,.10);transform:translateY(-2px)}
  .x-link small{display:block;font-weight:400;font-size:12px;color:var(--muted);margin-top:4px}
  .x-links-title{max-width:1100px;margin:0 auto;padding:0 24px 14px;font-size:15px;font-weight:800;color:var(--muted)}

  footer{border-top:1px solid var(--border);background:var(--soft);padding:32px 24px;text-align:center;font-size:13px;color:var(--muted)}
  footer .cols{display:flex;gap:28px;justify-content:center;flex-wrap:wrap;margin-bottom:12px}
  footer a:hover{color:var(--blue)}

  @media(max-width:980px){
    .hero{grid-template-columns:1fr;padding:48px 24px 64px}
    .capgroups{grid-template-columns:1fr}
    .steps{grid-template-columns:1fr}
    .stats{grid-template-columns:repeat(2,1fr)}
    .x-links{grid-template-columns:1fr}
    .menu{display:none}
  }
"""




def _page(slug: str, lang: str = "zh") -> str:
    if lang != "zh":
        return _page_i18n(slug, lang)
    f = FEATURES[slug]
    others = [s for s in _FEATURE_ORDER if s != slug]

    pains_html = "".join(f"<li>{_esc(p)}</li>" for p in f["pains"])
    caps_html = "".join(
        f'<div class="capgroup {g["color"]}"><h3>{_esc(g["group"])}</h3>' +
        "".join(f'<div class="cap"><b>{_esc(n)}</b><span>{_esc(d)}</span></div>' for n, d in g["items"]) +
        "</div>"
        for g in f["caps"])
    steps_html = "".join(
        f'<div class="step"><div class="no">{i+1}</div><h3>{_esc(t)}</h3><p>{_esc(d)}</p></div>'
        for i, (t, d) in enumerate(f["steps"]))
    stats_html = "".join(
        f'<div class="stat"><div class="n">{_esc(n)}</div><div class="l">{_esc(l)}</div></div>'
        for n, l in f["stats"])
    faqs_html = "".join(
        f'<details><summary>{_esc(q)}</summary><div class="a">{a}</div></details>'
        for q, a in f["faqs"])
    related_html = "".join(
        f'<a class="x-link" href="/features/{s}">{_esc(name)}<small>CrossAIO 产品能力 · 独立功能页</small></a>'
        for s, name in [(o, FEATURES[o]["icon"] + " " + FEATURES[o]["name"]) for o in others])
    rules_links = "".join(
        f'<a class="x-link" href="/rules/{p}">{_PLATFORM_SHORT[p]}<small>平台原生 GPSR 规则页</small></a>'
        for p in ("allegro", "emag", "cdiscount", "otto"))
    nav = site_nav("features", slug)
    mockup = _MOCKUPS[f["mockup"]]()

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(f['title'])}</title>
<meta name="description" content="{_esc(f['meta_desc'])}">
<style>{_CSS}</style>
</head>
<body>
{nav}
<div class="hero-wrap">
  <div class="hero">
    <div>
      <div class="eyebrow">✦ {_esc(f['eyebrow'])}</div>
      <h1>{f['h1']}</h1>
      <p class="sub">{f['sub']}</p>
      <div class="cta-row">
        <a href="/signup"><button class="pill-blue">免费开始</button></a>
        <a href="/app?tab={_WORKBENCH_TAB.get(slug, 'desc')}"><button class="pill-ghost">🚀 在工作台中使用 →</button></a>
      </div>
      <p class="tiny">{_esc(f['hero_note'])}</p>
    </div>
    <div class="mockup-cell">{mockup}</div>
  </div>
</div>

<section>
  <div class="danger-band">
    <h2>🚨 {_esc(f['pain_title'])}</h2>
    <ul>{pains_html}</ul>
  </div>
</section>

<section style="padding-top:8px">
  <div class="sec-head">
    <div class="sec-eyebrow">功能拆解</div>
    <h2 class="sec-title">{_esc(f['icon'])} {_esc(f['name'])} 能做什么</h2>
    <p class="sec-sub">按类目分组，每项都对着一个竞品空位</p>
  </div>
  <div class="capgroups">{caps_html}</div>
</section>

<section style="padding-top:8px">
  <div class="sec-head">
    <div class="sec-eyebrow">工作原理</div>
    <h2 class="sec-title">三步开始</h2>
  </div>
  <div class="steps">{steps_html}</div>
  <div style="margin-top:28px">{_flow_svg(f["steps"])}</div>
</section>

<section style="padding-top:8px">
  <div class="stats">{stats_html}</div>
</section>

<section style="padding-top:8px">
  <div class="sec-head">
    <div class="sec-eyebrow">覆盖范围</div>
    <h2 class="sec-title">一次配置 · 13 平台同步生效</h2>
    <p class="sec-sub">悬停可暂停滚动 · 点击左侧导航「覆盖平台」查看各平台规则详情</p>
  </div>
  {_platform_marquee()}
</section>

<section style="padding-top:8px">
  <div class="tier">
    <p>💰 {_esc(f['tier_line'])}</p>
    <a href="/pricing">查看完整定价 →</a>
  </div>
</section>

<section style="padding-top:8px">
  <div class="sec-head">
    <div class="sec-eyebrow">常见问题</div>
    <h2 class="sec-title">关于{_esc(f['name'])}</h2>
  </div>
  <div class="faq">{faqs_html}</div>
</section>

<div class="cta-band">
  <h2>{_esc(f['icon'])} 现在就体验{_esc(f['name'])}</h2>
  <p>免费注册即用 · 无需信用卡 · 无需绑定店铺</p>
  <a href="/signup"><button class="pill-blue">免费开始 →</button></a>
  <a href="/app?tab={_WORKBENCH_TAB.get(slug, 'desc')}" style="margin-left:10px"><button class="pill-ghost">🚀 在工作台中使用</button></a>
</div>

<div class="x-links-title">继续了解其他产品能力</div>
<div class="x-links">{related_html}</div>
<div class="x-links-title">相关平台原生规则页</div>
<div class="x-links" style="padding-top:0">{rules_links}</div>

<footer>
  <div class="cols">
    <a href="/">首页</a><a href="/features/gpsr">产品能力</a><a href="/rules">规则速查</a><a href="/pricing">定价</a>
    <a href="/gpsr-check">免费体检</a><a href="/skills">开源 Skills</a><a href="/signin">登录</a>
  </div>
  <div>CrossAIO — 欧洲全平台 Listing 质量 + 合规引擎 · © 2026</div>
</footer>
<script>
(function(){{
  try{{
    var API = "/api/v1";
    fetch(API+"/analytics/track",{{method:"POST",headers:{{"Content-Type":"application/json"}},
      body:JSON.stringify({{event_type:"landing_view", platform:null, meta:{{page:"feature", slug:"{slug}"}}}}}})}}).catch(function(){{}});
  }}catch(e){{}}
}})();
</script>
</body>
</html>"""


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_PLATFORM_SHORT = {
    "allegro": "🇵🇱 Allegro 规则 →",
    "emag": "🇷🇴 eMAG 规则 →",
    "cdiscount": "🇫🇷 Cdiscount 规则 →",
    "otto": "🇩🇪 Otto 规则 →",
}


def _page_i18n(slug: str, lang: str) -> str:
    """产品能力落地页翻译版（en/de/fr）。

    结构与 zh `_page` 完全对齐；页面框架文案取自 CHROME_XX，数据取自
    FEATURES_XX，内部链接加语言前缀，<head> 注入 hreflang，导航后注入切换器，
    页尾注入 lang 偏好脚本。mockup 走 `_MOCKUPS[name](lang)` 做文本替换。
    """
    feats = _FEATURES_LANG[lang]
    chrome = _CHROME_LANG[lang]
    f = feats[slug]
    p = _LANG_PREFIX[lang]
    base = f"/features/{slug}"
    others = [s for s in _FEATURE_ORDER if s != slug]
    tab = _WORKBENCH_TAB.get(slug, "desc")

    pains_html = "".join(f"<li>{_esc(pp)}</li>" for pp in f["pains"])
    caps_html = "".join(
        f'<div class="capgroup {g["color"]}"><h3>{_esc(g["group"])}</h3>' +
        "".join(f'<div class="cap"><b>{_esc(n)}</b><span>{_esc(d)}</span></div>' for n, d in g["items"]) +
        "</div>"
        for g in f["caps"])
    steps_html = "".join(
        f'<div class="step"><div class="no">{i+1}</div><h3>{_esc(t)}</h3><p>{_esc(d)}</p></div>'
        for i, (t, d) in enumerate(f["steps"]))
    stats_html = "".join(
        f'<div class="stat"><div class="n">{_esc(n)}</div><div class="l">{_esc(l)}</div></div>'
        for n, l in f["stats"])
    faqs_html = "".join(
        f'<details><summary>{_esc(q)}</summary><div class="a">{a}</div></details>'
        for q, a in f["faqs"])
    related_html = "".join(
        f'<a class="x-link" href="{p}/features/{s}">{_esc(feats[s]["icon"] + " " + feats[s]["name"])}'
        f'<small>{_esc(chrome["rel_small"])}</small></a>'
        for s in others)
    rules_links = "".join(
        f'<a class="x-link" href="{p}/rules/{pl}">{_esc(chrome["platform_short"][pl])}'
        f'<small>{_esc(chrome["rules_small"])}</small></a>'
        for pl in ("allegro", "emag", "cdiscount", "otto"))
    nav = site_nav("features", slug, lang=lang)
    switcher = _switcher_feature(base, lang)
    mockup = _MOCKUPS[f["mockup"]](lang)

    caps_title = _esc(chrome["sec_caps_title"].format(icon=f["icon"], name=f["name"]))
    faq_title = _esc(chrome["sec_faq_title"].format(name=f["name"]))
    band_title = _esc(chrome["cta_band_title"].format(icon=f["icon"], name=f["name"]))

    return f"""<!DOCTYPE html>
<html lang="{_LANG_HTML[lang]}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(f['title'])}</title>
<meta name="description" content="{_esc(f['meta_desc'])}">
{_hreflang_feature(base, lang)}
<style>{_CSS}</style>
</head>
<body>
{nav}
{switcher}
<div class="hero-wrap">
  <div class="hero">
    <div>
      <div class="eyebrow">✦ {_esc(f['eyebrow'])}</div>
      <h1>{f['h1']}</h1>
      <p class="sub">{f['sub']}</p>
      <div class="cta-row">
        <a href="{p}/signup"><button class="pill-blue">{_esc(chrome['cta_start'])}</button></a>
        <a href="{p}/app?tab={tab}"><button class="pill-ghost">{_esc(chrome['cta_workbench'])}</button></a>
      </div>
      <p class="tiny">{_esc(f['hero_note'])}</p>
    </div>
    <div class="mockup-cell">{mockup}</div>
  </div>
</div>

<section>
  <div class="danger-band">
    <h2>🚨 {_esc(f['pain_title'])}</h2>
    <ul>{pains_html}</ul>
  </div>
</section>

<section style="padding-top:8px">
  <div class="sec-head">
    <div class="sec-eyebrow">{_esc(chrome['sec_caps_eyebrow'])}</div>
    <h2 class="sec-title">{caps_title}</h2>
    <p class="sec-sub">{_esc(chrome['sec_caps_sub'])}</p>
  </div>
  <div class="capgroups">{caps_html}</div>
</section>

<section style="padding-top:8px">
  <div class="sec-head">
    <div class="sec-eyebrow">{_esc(chrome['sec_steps_eyebrow'])}</div>
    <h2 class="sec-title">{_esc(chrome['sec_steps_title'])}</h2>
  </div>
  <div class="steps">{steps_html}</div>
  <div style="margin-top:28px">{_flow_svg(f["steps"], lang)}</div>
</section>

<section style="padding-top:8px">
  <div class="stats">{stats_html}</div>
</section>

<section style="padding-top:8px">
  <div class="sec-head">
    <div class="sec-eyebrow">{_esc(chrome['sec_cover_eyebrow'])}</div>
    <h2 class="sec-title">{_esc(chrome['sec_cover_title'])}</h2>
    <p class="sec-sub">{_esc(chrome['sec_cover_sub'])}</p>
  </div>
  {_platform_marquee(lang)}
</section>

<section style="padding-top:8px">
  <div class="tier">
    <p>💰 {_esc(f['tier_line'])}</p>
    <a href="{p}/pricing">{_esc(chrome['tier_cta'])}</a>
  </div>
</section>

<section style="padding-top:8px">
  <div class="sec-head">
    <div class="sec-eyebrow">{_esc(chrome['sec_faq_eyebrow'])}</div>
    <h2 class="sec-title">{faq_title}</h2>
  </div>
  <div class="faq">{faqs_html}</div>
</section>

<div class="cta-band">
  <h2>{band_title}</h2>
  <p>{_esc(chrome['cta_band_sub'])}</p>
  <a href="{p}/signup"><button class="pill-blue">{_esc(chrome['cta_band_start'])}</button></a>
  <a href="{p}/app?tab={tab}" style="margin-left:10px"><button class="pill-ghost">{_esc(chrome['cta_band_workbench'])}</button></a>
</div>

<div class="x-links-title">{_esc(chrome['x_related_title'])}</div>
<div class="x-links">{related_html}</div>
<div class="x-links-title">{_esc(chrome['x_rules_title'])}</div>
<div class="x-links" style="padding-top:0">{rules_links}</div>

<footer>
  <div class="cols">
    <a href="{p}/">{_esc(chrome['footer_home'])}</a><a href="{p}/features">{_esc(chrome['footer_features'])}</a><a href="{p}/rules">{_esc(chrome['footer_rules'])}</a><a href="{p}/pricing">{_esc(chrome['footer_pricing'])}</a>
    <a href="{p}/gpsr-check">{_esc(chrome['footer_check'])}</a><a href="{p}/skills">{_esc(chrome['footer_skills'])}</a><a href="{p}/signin">{_esc(chrome['footer_signin'])}</a>
  </div>
  <div>{_esc(chrome['footer_tag'])}</div>
</footer>
<script>
(function(){{
  try{{
    var API = "/api/v1";
    fetch(API+"/analytics/track",{{method:"POST",headers:{{"Content-Type":"application/json"}},
      body:JSON.stringify({{event_type:"landing_view", platform:null, meta:{{page:"feature", slug:"{slug}"}}}})}}).catch(function(){{}});
  }}catch(e){{}}
}})();
</script>
{_LANG_SCRIPT}
</body>
</html>"""


def _index_lang(lang: str) -> str:
    """产品能力总览翻译版（en/de/fr）。"""
    chrome = _CHROME_LANG[lang]
    feats = _FEATURES_LANG[lang]
    p = _LANG_PREFIX[lang]
    base = "/features"
    cards = "".join(
        f'<a class="x-link" href="{p}/features/{s}">{_esc(feats[s]["icon"])} {_esc(feats[s]["name"])}'
        f'<small>{_esc(feats[s]["eyebrow"])}</small></a>'
        for s in _FEATURE_ORDER)
    return f"""<!DOCTYPE html>
<html lang="{_LANG_HTML[lang]}">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(chrome['index_title'])}</title>
<meta name="description" content="{_esc(chrome['index_meta'])}">
{_hreflang_feature(base, lang)}
<style>{_CSS}</style></head>
<body>
{site_nav("features", lang=lang)}
{_switcher_feature(base, lang)}
<section style="padding-top:56px">
  <div class="sec-head">
    <div class="sec-eyebrow">{_esc(chrome['index_eyebrow'])}</div>
    <h2 class="sec-title">{_esc(chrome['index_h2'])}</h2>
    <p class="sec-sub">{_esc(chrome['index_sub'])}</p>
  </div>
  <div class="x-links" style="padding:0">{cards}</div>
</section>
<footer>
  <div class="cols"><a href="{p}/">{_esc(chrome['footer_home'])}</a><a href="{p}/rules">{_esc(chrome['footer_rules'])}</a><a href="{p}/pricing">{_esc(chrome['footer_pricing'])}</a><a href="{p}/gpsr-check">{_esc(chrome['footer_check'])}</a></div>
  <div>{_esc(chrome['footer_tag'])}</div>
</footer>
{_LANG_SCRIPT}
</body></html>"""


@router.get("/features", response_class=HTMLResponse, include_in_schema=False)
def features_index():
    """产品能力总览 — 直接列出 6 个落地页（也充当站点地图页）。"""
    cards = "".join(
        f'<a class="x-link" href="/features/{s}">{_esc(FEATURES[s]["icon"])} {_esc(FEATURES[s]["name"])}'
        f'<small>{_esc(FEATURES[s]["eyebrow"])}</small></a>'
        for s in _FEATURE_ORDER)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>产品能力总览 — 6 大功能独立落地页 | CrossAIO</title>
<meta name="description" content="CrossAIO 产品能力：GPSR 合规引擎、Listing 生成器、多平台矩阵、差评改写闭环、AI 客服 + 统一收件箱、政策安全红线层。每个能力一个独立页面。">
<style>{_CSS}</style></head>
<body>
{site_nav("features")}
<section style="padding-top:56px">
  <div class="sec-head">
    <div class="sec-eyebrow">产品能力</div>
    <h2 class="sec-title">六大能力，六个独立页面</h2>
    <p class="sec-sub">每个能力都有完整的痛点分析、功能拆解、工作原理与定价入口</p>
  </div>
  <div class="x-links" style="padding:0">{cards}</div>
</section>
<footer>
  <div class="cols"><a href="/">首页</a><a href="/rules">规则速查</a><a href="/pricing">定价</a><a href="/gpsr-check">免费体检</a></div>
  <div>CrossAIO · © 2026</div>
</footer>
</body></html>"""


@router.get("/features/{slug}", response_class=HTMLResponse, include_in_schema=False)
def feature_page(slug: str):
    """产品能力落地页（动态渲染，数据源 FEATURES 字典）。"""
    if slug not in FEATURES:
        return RedirectResponse("/features", status_code=302)
    return HTMLResponse(_page(slug))


@router.get("/{lang}/features", response_class=HTMLResponse, include_in_schema=False)
def features_index_lang(lang: str):
    """产品能力总览翻译版（en/de/fr）；非法语言 404。"""
    if lang not in _LANGS:
        return HTMLResponse("Not Found", status_code=404)
    return HTMLResponse(_index_lang(lang))


@router.get("/{lang}/features/{slug}", response_class=HTMLResponse, include_in_schema=False)
def feature_page_lang(lang: str, slug: str):
    """产品能力落地页翻译版（en/de/fr）；非法语言 404，未知 slug 回退总览。"""
    if lang not in _LANGS:
        return HTMLResponse("Not Found", status_code=404)
    if slug not in FEATURES:
        return RedirectResponse(f"/{lang}/features", status_code=302)
    return HTMLResponse(_page(slug, lang=lang))
