"""全站共享导航 — 首页同款多页式导航，固定注入每个落地页。

多页式导航结构（与 home.html 完全一致）：
  产品能力 dropdown（/features/* 6 页 + 总览）
  覆盖平台 dropdown（/rules/* 6 页 + 速查表）
  免费工具 dropdown（体检 / 速查表 / 开源 Skills）
  定价 solo 链接 + 右侧 登录/工作台/免费注册
active 参数控制当前区块高亮；active_item 控制当前落地页在 dropdown 中高亮。
lang 参数（默认 "zh"）选择导航文案与链接前缀：
  - zh：与历史版本逐字节等价（中文文案，无前缀）
  - en/de/fr：文案按 GLOSSARY 翻译；有翻译版本的目标加语言前缀，
    /features/* 与 /rules/{allegro,...} 无翻译版本，保持指向中文页。
"""
from __future__ import annotations

FEATURE_ITEMS = [
    ("gpsr", "/features/gpsr", "🛡️", "GPSR 合规引擎", "CE 类目 → 警示语 → 合规块 → 回填"),
    ("listing-generator", "/features/listing-generator", "📦", "Listing 生成器", "四件套 + 字数硬校验 + 评分"),
    ("matrix", "/features/matrix", "🌍", "多平台矩阵", "一次输入 → 12 平台批量本地化"),
    ("review-rewrite", "/features/review-rewrite", "📈", "差评改写闭环", "主题定位 → 五点修复 + 语义评分"),
    ("ai-service", "/features/ai-service", "💬", "AI 客服 + Art.50", "AI Act 披露内嵌 + eBay 接入"),
    ("safety-redline", "/features/safety-redline", "🚨", "政策安全红线层", "威胁/勒索识别 → 转人工留证"),
    ("inbox", "/features/inbox", "📥", "统一收件箱", "12 平台消息一处管 · 母语回复"),
    ("ad-copy", "/features/ad-copy", "📣", "广告文案生成", "禁用词前置拦截 + A/B 变体"),
    ("listing-watch", "/features/listing-watch", "📡", "Listing 监控日报", "每日自动体检 · 风险升级即报"),
]

PLATFORM_ITEMS = [
    ("allegro", "/rules/allegro", "🇵🇱", "Allegro 规则详情", "波兰语政策 + UOKiK 监管"),
    ("emag", "/rules/emag", "🇷🇴", "eMAG 规则详情", "罗马尼亚语政策 + ANPC 监管"),
    ("cdiscount", "/rules/cdiscount", "🇫🇷", "Cdiscount 规则详情", "法语政策（Loi Toubon）"),
    ("otto", "/rules/otto", "🇩🇪", "Otto 规则详情", "德语政策 + ProdSG"),
    ("kaufland", "/rules/kaufland", "🇩🇪", "Kaufland 规则详情", "德/捷/斯四国站点"),
    ("bol", "/rules/bol", "🇳🇱", "bol.com 规则详情", "荷兰语政策 + ACM 监管"),
]

TOOL_ITEMS = [
    ("/compliance-check", "✅", "一键合规体检", "体检 → 欧代标注 → 技术文件清单，30 秒出报告"),
    ("/gpsr-check", "🛡️", "GPSR 合规体检", "免注册 30 秒，只报问题不收费"),
    ("/rules", "📋", "平台规则速查表", "12 平台字数/语言/GPSR 要点"),
    ("/skills", "🎁", "开源 Skills", "GPSR 检查器 + 规则库，MIT 免费"),
]

# ---------------------------------------------------------------------------
# 三语文案（术语表口径；CrossAIO / GPSR / Art.50 / eBay / UOKiK / ANPC / ProdSG /
# Loi Toubon / ACM / MIT 等专有词不翻译；12 平台数量与 30 秒等数值保留）
# ---------------------------------------------------------------------------

NAV_I18N = {
    "zh": {
        "features": "产品能力",
        "platforms": "覆盖平台",
        "tools": "免费工具",
        "pricing": "定价",
        "signin": "登录",
        "signup": "免费注册",
        "feature_overview_label": "产品能力总览",
        "feature_overview_sub": "六大能力 · 每个能力一个独立页面",
        "platforms_index_label": "全部 12 平台速查表",
        "platforms_index_sub": "字数 / 语言 / GPSR 要点",
    },
    "en": {
        "features": "Capabilities",
        "platforms": "Platforms",
        "tools": "Free tools",
        "pricing": "Pricing",
        "signin": "Sign in",
        "signup": "Sign up free",
        "feature_overview_label": "Capabilities overview",
        "feature_overview_sub": "Six core capabilities · one standalone page each",
        "platforms_index_label": "Rules reference — all 12 platforms",
        "platforms_index_sub": "Characters / languages / GPSR essentials",
    },
    "de": {
        "features": "Produktfunktionen",
        "platforms": "Plattformen",
        "tools": "Kostenlose Tools",
        "pricing": "Preise",
        "signin": "Anmelden",
        "signup": "Kostenlos registrieren",
        "feature_overview_label": "Funktionsübersicht",
        "feature_overview_sub": "Sechs Kernfunktionen · je eine eigene Seite",
        "platforms_index_label": "Regelübersicht — alle 12 Plattformen",
        "platforms_index_sub": "Zeichen / Sprachen / GPSR-Wesentliches",
    },
    "fr": {
        "features": "Fonctionnalités",
        "platforms": "Plateformes",
        "tools": "Outils gratuits",
        "pricing": "Tarifs",
        "signin": "Connexion",
        "signup": "Inscription gratuite",
        "feature_overview_label": "Aperçu des fonctionnalités",
        "feature_overview_sub": "Six fonctionnalités clés · chacune sa page dédiée",
        "platforms_index_label": "Référentiel de règles — les 12 plateformes",
        "platforms_index_sub": "Caractères / langues / points clés GPSR",
    },
}

# 顺序与 FEATURE_ITEMS 一致：每条 (label, sub)
FEATURE_I18N = {
    "en": [
        ("GPSR compliance engine", "CE categories → safety warnings → compliance blocks → backfill"),
        ("Listing generator", "Title / bullet points / description / backend terms + strict character limits + scoring"),
        ("Multi-platform matrix", "One input → batch localization for 12 platforms"),
        ("Review rewriting loop", "Issue theme detection → bullet fixes + semantic score"),
        ("AI customer service + Art.50", "AI Act disclosure embedded + eBay integration"),
        ("Policy safety red-line layer", "Threat/extortion detection → hand off to a human, logged"),
        ("Unified inbox", "Messages from 12 platforms in one place · replies in buyers' language"),
        ("Ad copy generator", "Pre-block banned words + A/B variants"),
        ("Listing monitoring daily report", "Daily automated check · instant alert on risk escalation"),
    ],
    "de": [
        ("GPSR-Compliance-Engine", "CE-Kategorien → Sicherheitshinweise → Compliance-Blöcke → Rückschreiben"),
        ("Listing-Generator", "Titel / Bulletpoints / Beschreibung / Backend-Suchbegriffe + harte Zeichenlimits + Bewertung"),
        ("Multi-Plattform-Matrix", "Eine Eingabe → Stapel-Lokalisierung für 12 Plattformen"),
        ("Bewertungs-Umschreibungs-Kreislauf", "Themenerkennung → Bulletpoint-Fixes + semantische Bewertung"),
        ("KI-Kundenservice + Art.50", "AI-Act-Offenlegung eingebettet + eBay-Anbindung"),
        ("Sicherheits-Rotlinien-Ebene", "Drohungs-/Erpressungserkennung → an einen Menschen übergeben, protokolliert"),
        ("Zentrales Postfach", "Messages von 12 Plattformen an einem Ort · Antworten in der Muttersprache"),
        ("Anzeigentext-Generator", "Sperrwörter vorab blockieren + A/B-Varianten"),
        ("Täglicher Listing-Monitoring-Bericht", "Täglicher automatischer Check · sofortige Meldung bei Risikoanstieg"),
    ],
    "fr": [
        ("Moteur de conformité GPSR", "Catégories CE → avertissements de sécurité → blocs de conformité → backfill"),
        ("Générateur de listings", "Titre / puces / description / mots-clés back-end + limites strictes de caractères + évaluation"),
        ("Matrice multi-plateformes", "Une saisie → localisation en masse pour 12 plateformes"),
        ("Boucle de réécriture d'avis", "Identification du thème → correctifs de puces + score sémantique"),
        ("Service client IA + Art.50", "Divulgation selon l'AI Act intégrée + intégration eBay"),
        ("Couche de lignes rouges de sécurité", "Détection de menaces/chantage → transfert à un agent humain, traçable"),
        ("Boîte de réception unifiée", "Messages de 12 plateformes au même endroit · réponses dans la langue maternelle"),
        ("Générateur de textes publicitaires", "Blocage préalable des mots interdits + variantes A/B"),
        ("Rapport de surveillance quotidien des listings", "Vérification automatique quotidienne · alerte immédiate en cas de montée du risque"),
    ],
}

# 顺序与 PLATFORM_ITEMS 一致：每条 (label, sub)
PLATFORM_I18N = {
    "en": [
        ("Allegro rules detail", "Polish policy + UOKiK oversight"),
        ("eMAG rules detail", "Romanian policy + ANPC oversight"),
        ("Cdiscount rules detail", "French policy (Loi Toubon)"),
        ("Otto rules detail", "German policy + ProdSG"),
        ("Kaufland rules detail", "DE / CZ / SK / PL marketplaces"),
        ("bol.com rules detail", "Dutch policy + ACM oversight"),
    ],
    "de": [
        ("Allegro-Regeln im Detail", "Polnische Richtlinien + UOKiK-Aufsicht"),
        ("eMAG-Regeln im Detail", "Rumänische Richtlinien + ANPC-Aufsicht"),
        ("Cdiscount-Regeln im Detail", "Französische Richtlinien (Loi Toubon)"),
        ("Otto-Regeln im Detail", "Deutsche Richtlinien + ProdSG"),
        ("Kaufland-Regeln im Detail", "DE / CZ / SK / PL Marktplätze"),
        ("bol.com-Regeln im Detail", "Niederländische Richtlinien + ACM-Aufsicht"),
    ],
    "fr": [
        ("Détail des règles Allegro", "Règles polonaises + surveillance UOKiK"),
        ("Détail des règles eMAG", "Règles roumaines + surveillance ANPC"),
        ("Détail des règles Cdiscount", "Règles françaises (Loi Toubon)"),
        ("Détail des règles Otto", "Règles allemandes + ProdSG"),
        ("Détail des règles Kaufland", "Marketplaces DE / CZ / SK / PL"),
        ("Détail des règles bol.com", "Règles néerlandaises + surveillance ACM"),
    ],
}

# 顺序与 TOOL_ITEMS 一致：每条 (label, sub)
TOOL_I18N = {
    "en": [
        ("One-click compliance check", "Check → EU Rep marking → technical file checklist, report in 30 seconds"),
        ("GPSR compliance check", "No sign-up, 30 seconds — issues only, free"),
        ("Platforms rules reference", "12 platforms: character limits / languages / GPSR essentials"),
        ("Open-source Skills", "GPSR checker + rule library, free MIT"),
    ],
    "de": [
        ("Compliance-Check mit einem Klick", "Check → EU-Verantwortlichen-Kennzeichnung → Checkliste technischer Unterlagen, Bericht in 30 Sekunden"),
        ("GPSR-Compliance-Check", "Ohne Registrierung, 30 Sekunden — nur Probleme, kostenlos"),
        ("Plattform-Regelübersicht", "12 Plattformen: Zeichenlimits / Sprachen / GPSR-Wesentliches"),
        ("Open-Source-Skills", "GPSR-Prüfer + Regelsammlung, kostenlos MIT"),
    ],
    "fr": [
        ("Vérification de conformité en un clic", "Vérification → marquage du représentant UE → liste de contrôle de la documentation technique, rapport en 30 secondes"),
        ("Vérification de conformité GPSR", "Sans inscription, 30 secondes — seulement les problèmes, gratuit"),
        ("Référentiel de règles des plateformes", "12 plateformes : limites de caractères / langues / points clés GPSR"),
        ("Skills open source", "Vérificateur GPSR + bibliothèque de règles, gratuit MIT"),
    ],
}

NAV_CSS = """
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
  @media(max-width:980px){.menu{display:none}}
"""


def _dd_link(href: str, icon: str, label: str, sub: str, key: str = "", active_item: str = "") -> str:
    on = ' class="on"' if key and key == active_item else ""
    return (f'<a href="{href}"{on}><span>{icon} {label}'
            f'<small>{sub}</small></span></a>')


def site_nav(active: str = "", active_item: str = "", lang: str = "zh", switcher: str = "") -> str:
    """渲染首页同款多页式导航。

    active: 当前区块（"features" / "platforms" / "tools" / "pricing"）
    active_item: 当前落地页 key（feature slug 或 platform 代码），dropdown 中高亮
    lang: "zh"（默认，输出与历史版本逐字节等价）/ "en" / "de" / "fr"
    """
    p = "" if lang == "zh" else f"/{lang}"
    nav = NAV_I18N.get(lang, NAV_I18N["zh"])
    feat_tr = FEATURE_I18N.get(lang)
    plat_tr = PLATFORM_I18N.get(lang)
    tool_tr = TOOL_I18N.get(lang)

    # 有翻译版本的目标加前缀；/features/* 与 /rules/{platform} 已有翻译，lang 版加前缀
    logo_href = "/"
    pricing_href = f"{p}/pricing" if p else "/pricing"
    signin_href = f"{p}/signin" if p else "/signin"
    signup_href = f"{p}/signup" if p else "/signup"
    rules_index_href = f"{p}/rules" if p else "/rules"

    feats = ""
    for i, (key, href, icon, label, sub) in enumerate(FEATURE_ITEMS):
        if feat_tr is not None:
            label, sub = feat_tr[i]
        feats += _dd_link((p + href) if p else href, icon, label, sub, key, active_item)
    feats += _dd_link((p + "/features") if p else "/features", "🗂️", nav["feature_overview_label"], nav["feature_overview_sub"],
                      "features-index", active_item)

    platforms = ""
    for i, (key, href, icon, label, sub) in enumerate(PLATFORM_ITEMS):
        if plat_tr is not None:
            label, sub = plat_tr[i]
        platforms += _dd_link((p + href) if p else href, icon, label, sub, key, active_item)
    platforms += _dd_link(rules_index_href, "📋", nav["platforms_index_label"],
                           nav["platforms_index_sub"], "rules-index", active_item)

    tools = ""
    for i, (href, icon, label, sub) in enumerate(TOOL_ITEMS):
        if tool_tr is not None:
            label, sub = tool_tr[i]
        tools += _dd_link((p + href) if p else href, icon, label, sub)

    def active_cls(section: str) -> str:
        return " active" if section == active else ""

    # 品牌商标统一指向站根：href="/" 已能覆盖 localhost 与 IP 两种入口，
    # 这里再把属性改成“当前域名 + /”，保证右击/悬停看到的也是绝对地址。
    brand_script = (
        '<script id="cx-brand-root">/* 品牌商标统一指向站根（跟随当前域名）*/(function(){try{'
        'var o=location.origin+"/";'
        "var l=document.querySelectorAll('a.logo,a.cx-logo,a[class*=\"brand\"]');"
        'for(var i=0;i<l.length;i++){if(l[i].textContent.indexOf("CrossAIO")>=0){l[i].setAttribute("href",o);}}'
        '}catch(e){}})();</script>'
    )

    nav_style = (
        '<style id="cx-nav-fixed">/* 全站导航栏统一固定（吸顶）*/'
        'nav{position:-webkit-sticky;position:sticky;top:0;z-index:1000;'
        'background:#fff;box-shadow:0 1px 0 rgba(15,23,42,.07)}</style>'
    )

    return f"""{nav_style}<nav>
  <a class="logo" href="{logo_href}"><span class="dot">🤖</span>CrossAIO</a>
  <div class="menu">
    <div class="navitem{active_cls("features")}">
      <a>{nav["features"]}</a>
      <div class="dropdown">{feats}</div>
    </div>
    <div class="navitem{active_cls("platforms")}">
      <a>{nav["platforms"]}</a>
      <div class="dropdown">{platforms}</div>
    </div>
    <div class="navitem{active_cls("tools")}">
      <a>{nav["tools"]}</a>
      <div class="dropdown">{tools}</div>
    </div>
    <div class="navitem{active_cls("pricing")}"><a class="solo" href="{pricing_href}">{nav["pricing"]}</a></div>
  </div>
  <div class="right">
    {switcher}
    <a class="login-link" href="{signin_href}">{nav["signin"]}</a>
    <a href="{signup_href}"><button class="pill-nav">{nav["signup"]}</button></a>
  </div>
</nav>{brand_script}"""
