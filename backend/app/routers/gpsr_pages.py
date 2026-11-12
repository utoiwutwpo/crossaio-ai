"""GPSR 体检中心多页化 — 原 /gpsr-check 单页版面拆成 6 个独立落地页。

多页式导航结构（H10 架构）：
  /gpsr-check              体检主页（Hero 轨道动画 + AI 对话卡 + 免注册体检表单）
  /gpsr-check/features     功能拆解（五大能力板块 + 动画流程图 + 扫描光效 mockup）
  /gpsr-check/platforms    12 平台覆盖（无缝滚动旗帜墙 + 平台字标卡）
  /gpsr-check/compare      竞品对比（绑店型工具 vs CrossAIO）
  /gpsr-check/pricing      定价（免费体检 vs Starter 解锁合规块）
  /gpsr-check/faq          FAQ

每个落地页固定注入首页同款共享导航（site_nav，单一数据源）+ 本地分页胶囊条，
页间交叉链接成环。动态素材复用 feature_pages 的 _flow_svg / _platform_marquee /
_MOCKUP_SHELL（扫描光效 mockup）与全量动效 CSS。

多语言：zh（默认，无 URL 前缀）/ en / de / fr（/en/ /de/ /fr/ 前缀镜像路由）。
zh 输出与历史逐字节一致（仅按冻结规范增量注入切换器 / hreflang / 偏好脚本）。
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ..config import settings
from .feature_pages import (_CSS as FP_CSS, _MOCKUPS, _esc, _flow_svg,
                            _platform_marquee)
from .site_nav import NAV_CSS, site_nav

router = APIRouter()

# ---------------------------------------------------------------------------
# 多语言基础设施（zh 默认无前缀；en/de/fr 加语言前缀）
# ---------------------------------------------------------------------------
LANGS = ("zh", "en", "de", "fr")
_LANG_HTML = {"zh": "zh-CN", "en": "en", "de": "de", "fr": "fr"}
_PREFIX = {"zh": "", "en": "/en", "de": "/de", "fr": "/fr"}


def _lp(path: str, lang: str) -> str:
    """给有翻译版本的内部链接加语言前缀；/features*、/api/*、锚点、外链不加。"""
    if lang == "zh":
        return path
    if (path.startswith("/api/") or path.startswith("#") or path.startswith("http")
            or path.startswith("/features")):
        return path
    return _PREFIX[lang] + path


# ---------------------------------------------------------------------------
# 分页注册表（单一数据源：胶囊条 / 交叉链接 / 主页入口卡全部由此生成）
# ---------------------------------------------------------------------------
PAGES = [
    ("home", "/gpsr-check", "🛡️", "体检主页", "30 秒免注册 GPSR 合规体检"),
    ("features", "/gpsr-check/features", "⚙️", "功能拆解", "五大能力逐个看透"),
    ("platforms", "/gpsr-check/platforms", "🌍", "12 平台覆盖", "字数/语言/合规规则内置"),
    ("compare", "/gpsr-check/compare", "⚖️", "竞品对比", "不绑店，不烧钱，直击合规"),
    ("pricing", "/gpsr-check/pricing", "💰", "定价", "体检免费 · 修复 €29/月起"),
    ("faq", "/gpsr-check/faq", "❓", "FAQ", "常见问题一次讲清"),
]

_PAGES_I18N = {
    "en": [
        ("home", "/en/gpsr-check", "🛡️", "Check Center", "30-second no-signup GPSR check"),
        ("features", "/en/gpsr-check/features", "⚙️", "Features explained", "five core capabilities, one by one"),
        ("platforms", "/en/gpsr-check/platforms", "🌍", "12 platforms", "limits / languages / rules built in"),
        ("compare", "/en/gpsr-check/compare", "⚖️", "Comparison", "no store, no waste, straight to compliance"),
        ("pricing", "/en/gpsr-check/pricing", "💰", "Pricing", "check free · fixes from €29/month"),
        ("faq", "/en/gpsr-check/faq", "❓", "FAQ", "all FAQs answered in one place"),
    ],
    "de": [
        ("home", "/de/gpsr-check", "🛡️", "Check-Center", "30-Sekunden-GPSR-Check ohne Registrierung"),
        ("features", "/de/gpsr-check/features", "⚙️", "Funktionen im Detail", "fünf Kernfunktionen im Überblick"),
        ("platforms", "/de/gpsr-check/platforms", "🌍", "12 Plattformen", "Limits / Sprachen / Regeln integriert"),
        ("compare", "/de/gpsr-check/compare", "⚖️", "Vergleich", "kein Shop, keine Kosten, direkt zur Konformität"),
        ("pricing", "/de/gpsr-check/pricing", "💰", "Preise", "Check kostenlos · Fixes ab €29/Monat"),
        ("faq", "/de/gpsr-check/faq", "❓", "FAQ", "alle FAQs auf einen Blick"),
    ],
    "fr": [
        ("home", "/fr/gpsr-check", "🛡️", "Centre de vérification", "vérification GPSR en 30 s sans inscription"),
        ("features", "/fr/gpsr-check/features", "⚙️", "Fonctionnalités", "cinq fonctionnalités clés détaillées"),
        ("platforms", "/fr/gpsr-check/platforms", "🌍", "12 plateformes", "limites / langues / règles intégrées"),
        ("compare", "/fr/gpsr-check/compare", "⚖️", "Comparaison", "sans boutique, sans dépense, droit à la conformité"),
        ("pricing", "/fr/gpsr-check/pricing", "💰", "Tarifs", "vérif gratuite · correctifs dès €29/mois"),
        ("faq", "/fr/gpsr-check/faq", "❓", "FAQ", "toutes les FAQ expliquées clairement"),
    ],
}


def _pages(lang: str = "zh"):
    return PAGES if lang == "zh" else _PAGES_I18N[lang]


def _gnav(active: str, lang: str = "zh") -> str:
    """本地分页胶囊条：6 个分页互链，当前页高亮。"""
    links = "".join(
        f'<a class="glink{" on" if key == active else ""}" href="{href}">'
        f'{icon} {label}</a>'
        for key, href, icon, label, _ in _pages(lang))
    return f'<div class="gnav"><div class="gnav-inner">{links}</div></div>'


_XLINKS_TITLE = {
    "zh": "继续了解体检中心",
    "en": "keep exploring the Check Center",
    "de": "mehr zum Check Center",
    "fr": "en savoir plus sur le centre de vérification",
}


def _xlinks(exclude: str, lang: str = "zh") -> str:
    """分页交叉链接（H10：页尾互通），排除当前页。"""
    cards = "".join(
        f'<a class="x-link" href="{href}">{icon} {label}'
        f'<small>{sub}</small></a>'
        for key, href, icon, label, sub in _pages(lang) if key != exclude)
    return f'<div class="x-links-title">{_XLINKS_TITLE[lang]}</div><div class="x-links">{cards}</div>'


_FOOTER = """
<footer>
  <div class="cols">
    <a href="/">首页</a><a href="/features">产品能力</a><a href="/rules">规则速查</a>
    <a href="/gpsr-check">免费体检</a><a href="/compliance-check">一键合规体检</a>
    <a href="/pricing">定价</a><a href="/skills">开源 Skills</a><a href="/signin">登录</a>
  </div>
  <div>CrossAIO — 欧洲全平台 Listing 质量 + 合规引擎 · © 2026<br>
  报告为工程辅助建议，不构成法律意见；具体合规要求以欧盟官方文本为准。</div>
</footer>"""

_FOOTER_I18N = {
    "en": """
<footer>
  <div class="cols">
    <a href="/en/">Home</a><a href="/features">Capabilities</a><a href="/en/rules">Rules reference</a>
    <a href="/en/gpsr-check">free compliance check</a><a href="/en/compliance-check">one-click compliance check</a>
    <a href="/en/pricing">pricing</a><a href="/en/skills">open-source Skills</a><a href="/en/signin">sign in</a>
  </div>
  <div>CrossAIO — the all-Europe platform Listing quality + compliance engine · © 2026<br>
  Reports are engineering assistance, not legal advice; final compliance decisions should follow official EU texts.</div>
</footer>""",
    "de": """
<footer>
  <div class="cols">
    <a href="/de/">Startseite</a><a href="/features">Produktfunktionen</a><a href="/de/rules">Regelübersicht</a>
    <a href="/de/gpsr-check">kostenloser Compliance-Check</a><a href="/de/compliance-check">Compliance-Check mit einem Klick</a>
    <a href="/de/pricing">Preise</a><a href="/de/skills">Open-Source-Skills</a><a href="/de/signin">Anmelden</a>
  </div>
  <div>CrossAIO — Europas Listing-Qualitäts- und Compliance-Engine für alle Plattformen · © 2026<br>
  Berichte sind technische Hilfestellung, keine Rechtsberatung; maßgeblich sind die offiziellen EU-Texte.</div>
</footer>""",
    "fr": """
<footer>
  <div class="cols">
    <a href="/fr/">Accueil</a><a href="/features">Fonctionnalités</a><a href="/fr/rules">référentiel de règles</a>
    <a href="/fr/gpsr-check">vérification de conformité gratuite</a><a href="/fr/compliance-check">vérification de conformité en un clic</a>
    <a href="/fr/pricing">tarifs</a><a href="/fr/skills">Skills open source</a><a href="/fr/signin">connexion</a>
  </div>
  <div>CrossAIO — moteur de qualité de listings et de conformité pour toutes les plateformes européennes · © 2026<br>
  Les rapports sont une assistance technique et non un avis juridique ; les textes officiels de l'UE font foi.</div>
</footer>""",
}


def _footer(lang: str = "zh") -> str:
    return _FOOTER if lang == "zh" else _FOOTER_I18N[lang]


def _track(slug: str) -> str:
    return f"""<script>
(function(){{
  try{{
    var API = "/api/v1";
    fetch(API+"/analytics/track",{{method:"POST",headers:{{"Content-Type":"application/json"}},
      body:JSON.stringify({{event_type:"landing_view", platform:null, meta:{{page:"gpsr-hub", slug:"{slug}"}}}})}}).catch(function(){{}});
  }}catch(e){{}}
}})();
</script>"""


def _hreflang(active: str, lang: str) -> str:
    """<head> 内 5 行 hreflang；中文路径无前缀，x-default 指向中文版。"""
    base = "/gpsr-check" if active == "home" else f"/gpsr-check/{active}"
    b = settings.public_url
    return (
        f'<link rel="alternate" hreflang="zh" href="{b}{base}">\n'
        f'<link rel="alternate" hreflang="en" href="{b}/en{base}">\n'
        f'<link rel="alternate" hreflang="de" href="{b}/de{base}">\n'
        f'<link rel="alternate" hreflang="fr" href="{b}/fr{base}">\n'
        f'<link rel="alternate" hreflang="x-default" href="{b}{base}">'
    )


def _switcher(active: str, lang: str) -> str:
    """语言切换器：🌐 图标 + 原生下拉（英文第一、中文最后）。"""
    base = "/gpsr-check" if active == "home" else f"/gpsr-check/{active}"
    paths = {"zh": base, "en": "/en" + base, "de": "/de" + base, "fr": "/fr" + base}
    full = {"en": "English", "de": "Deutsch", "fr": "Français", "zh": "中文"}
    opts = "".join(
        f'<option value="{paths[code]}" data-lang="{code}"{" selected" if code == lang else ""}>{full[code]}</option>'
        for code in ("en", "de", "fr", "zh"))
    return ('<div class="lang-switch" role="navigation" aria-label="Language" '
            'style="display:inline-flex;gap:3px;align-items:center;padding:5px 12px;border:1px solid #cbd5e1;'
            'border-radius:999px;background:#fff;color:#0f172a;font-size:13px">'
            '🌐<select onchange="location.href=this.value" '
            'style="border:none;background:transparent;font-size:13px;color:#0f172a;outline:none;cursor:pointer;font-weight:700">'
            + opts + '</select></div>')


_LANG_SCRIPT = ('<script>(function(){try{localStorage.setItem("crossaio_lang",'
                'document.documentElement.lang||"zh")}catch(e){}})();</script>')


def _shell(active: str, title: str, meta_desc: str, body: str, lang: str = "zh") -> str:
    """页面骨架：共享导航 + 切换器 + 胶囊条 + 内容 + 交叉链接 + footer。"""
    return f"""<!DOCTYPE html>
<html lang="{_LANG_HTML[lang]}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(title)}</title>
<meta name="description" content="{_esc(meta_desc)}">
{_hreflang(active, lang)}
<style>{FP_CSS}</style>
<style>{NAV_CSS}</style>
<style>{_GPSR_CSS}</style>
</head>
<body>
{site_nav("tools", lang=lang, switcher=_switcher(active, lang))}
{_gnav(active, lang)}
{body}
{_xlinks(active, lang)}
{_footer(lang)}
{_track(active)}
{_LANG_SCRIPT}
</body>
</html>"""


# ---------------------------------------------------------------------------
# GPSR 中心特有样式（topbar / 轨道动画 / AI 对话卡 / 表单 / 平台字标卡 /
# 对比表 / 定价卡 / 胶囊条；基础排版与动效复用 feature_pages._CSS）
# ---------------------------------------------------------------------------
_GPSR_CSS = """
  .topbar{background:var(--bar,#1a5cf0);color:#fff;text-align:center;font-size:13.5px;padding:9px 16px}
  .topbar a{color:#fff;text-decoration:underline;text-underline-offset:3px;font-weight:700}

  .aiact-banner{background:linear-gradient(120deg,#0b1030,#251a5e);color:#fff;border-radius:14px;max-width:1240px;margin:18px auto 0;padding:18px 24px;display:flex;gap:14px;align-items:flex-start}
  .aiact-banner .ic{font-size:26px;line-height:1}
  .aiact-banner b{color:#a78bfa}
  .aiact-banner p{font-size:13.5px;color:#cbd5e1;margin:0;line-height:1.7}
  .aiact-banner a{color:#93c5fd;font-weight:600}

  .gnav{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.93);backdrop-filter:blur(8px);border-bottom:1px solid var(--border)}
  .gnav-inner{max-width:1240px;margin:0 auto;padding:10px 24px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
  .glink{font-size:13.5px;font-weight:600;color:var(--muted);padding:8px 16px;border-radius:999px;transition:.15s}
  .glink:hover{background:#f1f5f9;color:var(--ink)}
  .glink.on{background:var(--blue);color:#fff}
  .glink.on:hover{background:var(--blue-dark)}

  .hero-wrap{position:relative;overflow:hidden}
  .orbits{position:absolute;inset:0;pointer-events:none;z-index:1}
  .orbit{position:absolute;top:50%;right:-180px;width:760px;height:760px;margin-top:-380px;border:1px solid rgba(255,255,255,.10);border-radius:50%}
  .orbit.o2{width:560px;height:560px;margin-top:-280px;right:-80px}
  .orbit.o3{width:380px;height:380px;margin-top:-190px;right:20px}
  .spin{position:absolute;inset:0;animation:rot linear infinite}
  .orbit.o1 .spin{animation-duration:26s}
  .orbit.o2 .spin{animation-duration:18s;animation-direction:reverse}
  .orbit.o3 .spin{animation-duration:12s}
  .spin i{position:absolute;top:-5px;left:50%;width:10px;height:10px;border-radius:50%}
  .orbit.o1 .spin i{background:#4ade80;box-shadow:0 0 18px 4px rgba(74,222,128,.65)}
  .orbit.o2 .spin i{background:#60a5fa;box-shadow:0 0 18px 4px rgba(96,165,250,.65)}
  .orbit.o3 .spin i{background:#c084fc;box-shadow:0 0 16px 4px rgba(192,132,252,.7)}
  @keyframes rot{to{transform:rotate(360deg)}}
  .hero .eyebrow{color:#c4b5fd}
  .hero h1 em{font-style:normal;color:#a5b4fc}
  .hero .tiny b{color:#e2e8f0}

  .chat{background:#fff;border-radius:16px;color:var(--ink);width:100%;max-width:400px;margin-left:auto;
    box-shadow:0 30px 80px rgba(0,0,0,.5);font-size:13px;overflow:hidden;animation:cb-float 5s ease-in-out infinite}
  .chat .head{display:flex;align-items:center;gap:8px;padding:12px 16px;border-bottom:1px solid var(--border)}
  .chat .head .cdot{width:22px;height:22px;border-radius:6px;background:linear-gradient(135deg,var(--blue),var(--purple));display:inline-flex;align-items:center;justify-content:center;font-size:12px}
  .chat .head b{font-size:13.5px}
  .chat .head .win{margin-left:auto;color:#94a3b8;font-size:12px;letter-spacing:3px}
  .chat .cbody{padding:14px 16px 16px;min-height:280px}
  .chat .greet{font-size:14px;margin-bottom:4px}
  .chat .hint-q{font-size:12px;color:var(--muted);margin-bottom:10px}
  .chips{display:flex;flex-direction:column;gap:8px;margin-bottom:12px}
  .chip{border:1px solid var(--border);border-radius:10px;padding:9px 12px;font-size:12.5px;color:#334155;cursor:pointer;transition:.15s;background:#fff}
  .chip:hover{border-color:var(--blue);color:var(--blue);background:#eff6ff}
  .bubble{background:#eef4ff;border-radius:12px 12px 12px 4px;padding:11px 13px;font-size:12.5px;color:#1e3a8a;line-height:1.6}
  .bubble b{color:#123c7d}
  .bubble .tag{display:inline-block;background:#fee2e2;color:var(--err);border-radius:6px;padding:1px 8px;font-size:11px;font-weight:700;margin:4px 4px 0 0}
  .bubble .tag.ok{background:#dcfce7;color:var(--ok)}
  .typing{display:inline-flex;gap:4px;padding:10px 12px}
  .typing i{width:6px;height:6px;border-radius:50%;background:#93a8d8;animation:blink 1.2s infinite}
  .typing i:nth-child(2){animation-delay:.2s}.typing i:nth-child(3){animation-delay:.4s}
  @keyframes blink{0%,80%,100%{opacity:.25}40%{opacity:1}}
  .fade-in{animation:cb-fadeup .5s ease both}
  .chat .foot{border-top:1px solid var(--border);padding:10px 16px;display:flex;gap:8px;font-size:11px;color:#94a3b8}
  .chat .foot span{border:1px solid var(--border);border-radius:999px;padding:3px 10px}

  .guides{max-width:1240px;margin:-52px auto 0;padding:0 24px;position:relative;z-index:5;display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
  .gcard{background:#fff;border-radius:14px;box-shadow:0 12px 40px rgba(15,23,42,.12);overflow:hidden;transition:transform .18s;animation:cb-fadeup .6s ease-out both}
  .gcard:nth-child(2){animation-delay:.15s}.gcard:nth-child(3){animation-delay:.3s}
  .gcard:hover{transform:translateY(-4px)}
  .gcard .thumb{height:140px;display:flex;align-items:center;justify-content:center;font-size:42px}
  .gcard .gbody{padding:18px 20px 20px}
  .gcard h3{font-size:16px;font-weight:700;margin-bottom:6px}
  .gcard p{font-size:13px;color:var(--muted);margin-bottom:12px}
  .gcard a{font-size:13px;color:var(--blue);font-weight:600}

  .hero-solo{max-width:880px;margin:0 auto;padding:52px 24px 10px}
  .hero-solo .eyebrow{color:var(--blue)}
  .hero-solo h1{font-size:34px;line-height:1.25;font-weight:800;letter-spacing:-.01em;margin-bottom:14px;color:var(--ink)}
  .hero-solo p.sub{font-size:15.5px;color:var(--muted);margin-bottom:8px}

  #check .panel{max-width:680px;margin:0 auto;background:var(--soft);border:1px solid var(--border);border-radius:20px;padding:36px}
  label{display:block;font-size:13px;font-weight:600;margin:14px 0 6px}
  input,select{width:100%;padding:11px 14px;border:1px solid var(--border);border-radius:10px;font-size:14px;background:#fff;color:var(--ink)}
  input:focus,select:focus{outline:2px solid var(--blue);border-color:transparent}
  .msg{padding:12px 16px;border-radius:10px;font-size:14px;margin-top:16px}
  .msg.err{background:#fef2f2;color:var(--err);border:1px solid #fecaca}
  .hint{font-size:12px;color:var(--muted);margin-top:6px}
  table{width:100%;border-collapse:collapse;font-size:14px;margin-top:12px}
  th,td{border-bottom:1px solid var(--border);padding:10px 8px;text-align:left;vertical-align:top}
  th{color:var(--muted);font-weight:600;font-size:13px}
  .badge{display:inline-block;background:#eef2ff;color:var(--blue);border-radius:999px;padding:2px 12px;font-size:12px;font-weight:600;margin:0 6px 6px 0}
  .aiact-note{background:#eef2ff;border:1px solid #c7d2fe;color:#1e3a8a;border-radius:10px;padding:11px 14px;font-size:13px;margin-top:14px;line-height:1.7}
  .aiact-note b{color:#1d4ed8}

  .fblock{display:grid;grid-template-columns:1.05fr .95fr;gap:52px;align-items:center;padding:36px 0;border-bottom:1px solid var(--border)}
  .fblock h3{font-size:23px;font-weight:800;line-height:1.35;margin-bottom:16px}
  .fblock ul{list-style:none;margin-bottom:20px}
  .fblock li{padding:7px 0 7px 30px;position:relative;font-size:14px}
  .fblock li::before{content:"✓";position:absolute;left:0;top:7px;color:var(--ok);font-weight:800}
  .fblock li span{color:var(--muted)}
  .fvisual{background:linear-gradient(160deg,#eff6ff,#f5f3ff);border-radius:18px;padding:24px;display:flex;flex-direction:column;gap:12px;animation:cb-fadeup .6s ease-out both}
  .fcard{background:#fff;border-radius:12px;padding:13px 18px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 6px 18px rgba(30,27,75,.07);font-size:13px}
  .fcard .k{color:var(--muted);font-size:12px}
  .fcard .v{font-weight:700;font-size:15px}
  .fcard .v.blue{color:var(--blue)}.fcard .v.up{color:var(--ok)}.fcard .v.bad{color:var(--err)}

  .sites{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
  .site{border:1px solid var(--border);border-radius:12px;padding:18px 20px;display:flex;justify-content:space-between;align-items:center;background:#fff;transition:.15s;animation:cb-fadeup .6s ease-out both}
  .site:hover{border-color:var(--blue-light,#3b82f6);box-shadow:0 8px 24px rgba(37,99,235,.10);transform:translateY(-2px)}
  .site .mark{flex:0 0 auto;display:flex;align-items:center;line-height:0}
  .site .mark .mark-img{height:22px;width:auto;object-fit:contain;display:block}
  .site .meta{font-size:12px;color:var(--muted);text-align:right;line-height:1.5}
  .site .meta b{display:block;font-size:13px;color:var(--ink)}
  .mark-note{font-size:11px;color:#94a3b8;text-align:center;margin-top:14px}

  .compare .nowin{color:var(--err);font-weight:600}
  .compare .win{color:var(--ok);font-weight:600}

  .pricing-card{background:radial-gradient(600px 300px at 90% 0%,rgba(139,92,246,.5),transparent 60%),linear-gradient(120deg,#0b1030,#251a5e);border-radius:24px;color:#fff;text-align:center;padding:56px 32px;animation:cb-fadeup .6s ease-out both}
  .pricing-card h2{font-size:30px;font-weight:800;margin-bottom:10px}
  .pricing-card .price{font-size:44px;font-weight:800;color:#a78bfa;margin:14px 0 6px}
  .pricing-card .price small{font-size:15px;color:#94a3b8;font-weight:400}
  .pricing-card p{color:#cbd5e1;font-size:14px}
  .pricing-card .pill-blue{margin-top:22px}
  .ptiers{display:grid;grid-template-columns:1fr 1fr;gap:20px;max-width:880px;margin:26px auto 0}
  .ptier{border:1px solid var(--border);border-radius:16px;padding:24px 26px;background:#fff}
  .ptier.hot{border-color:var(--blue);box-shadow:0 10px 30px rgba(37,99,235,.12)}
  .ptier h3{font-size:17px;font-weight:800;margin-bottom:8px}
  .ptier .pp{font-size:26px;font-weight:800;color:var(--blue);margin-bottom:10px}
  .ptier ul{list-style:none}
  .ptier li{padding:5px 0 5px 26px;position:relative;font-size:13.5px}
  .ptier li::before{content:"✓";position:absolute;left:0;color:var(--ok);font-weight:800}
  .ptier li.no::before{content:"✗";color:var(--err)}

  @media (max-width:960px){
    .hero{grid-template-columns:1fr;padding:56px 24px 72px}
    .chat{margin:0 auto}
    .guides{grid-template-columns:1fr}
    .fblock{grid-template-columns:1fr;gap:26px}
    .sites{grid-template-columns:1fr}
    .ptiers{grid-template-columns:1fr}
    .orbits{display:none}
  }

  /* ===== CrossAIO redesign: shared glass / glow / tech-layer shell ===== */
  .hero{position:relative;z-index:2}
  /* tech layers (grid + glow blobs + rising particles) */
  .hero-grid{position:absolute;inset:0;z-index:1;pointer-events:none;opacity:.5;
    background-image:linear-gradient(rgba(255,255,255,.05) 1px,transparent 1px),
    linear-gradient(90deg,rgba(255,255,255,.05) 1px,transparent 1px);
    background-size:44px 44px;
    -webkit-mask-image:radial-gradient(ellipse 75% 65% at 50% 40%,#000 30%,transparent 75%);
    mask-image:radial-gradient(ellipse 75% 65% at 50% 40%,#000 30%,transparent 75%)}
  .hero-glow{position:absolute;inset:0;z-index:1;pointer-events:none}
  .hero-glow i{position:absolute;border-radius:50%;filter:blur(70px);opacity:.5;animation:glowpulse 9s ease-in-out infinite}
  .hero-glow i.g1{width:420px;height:420px;left:52%;top:-90px;background:radial-gradient(circle,rgba(139,92,246,.55),transparent 70%)}
  .hero-glow i.g2{width:360px;height:360px;right:-80px;bottom:-120px;background:radial-gradient(circle,rgba(59,130,246,.5),transparent 70%);animation-delay:3s}
  @keyframes glowpulse{0%,100%{opacity:.45}50%{opacity:.75}}
  .particles{position:absolute;inset:0;z-index:1;pointer-events:none}
  .particles i{position:absolute;width:5px;height:5px;border-radius:50%;background:#93c5fd;opacity:0;animation:ptw 7s linear infinite}
  .particles i:nth-child(2){width:4px;height:4px;background:#c4b5fd;animation-delay:1.1s;animation-duration:9s}
  .particles i:nth-child(3){width:6px;height:6px;background:#a5b4fc;animation-delay:2.2s;animation-duration:6s}
  .particles i:nth-child(4){width:4px;height:4px;background:#93c5fd;animation-delay:3.3s;animation-duration:8s}
  .particles i:nth-child(5){width:5px;height:5px;background:#c4b5fd;animation-delay:.6s;animation-duration:10s}
  .particles i:nth-child(6){width:3px;height:3px;background:#a5b4fc;animation-delay:1.8s;animation-duration:7s}
  .particles i:nth-child(7){width:5px;height:5px;background:#93c5fd;animation-delay:2.9s;animation-duration:9s}
  .particles i:nth-child(8){width:4px;height:4px;background:#c4b5fd;animation-delay:4s;animation-duration:6.5s}
  .particles i:nth-child(9){width:5px;height:5px;background:#a5b4fc;animation-delay:.9s;animation-duration:8.5s}
  @keyframes ptw{
    0%{transform:translateY(0);opacity:0}
    8%{opacity:.85}
    85%{opacity:.5}
    100%{transform:translateY(-60vh);opacity:0}
  }

  /* gradient glowing CTA + shine sweep */
  .pill-blue{background:linear-gradient(90deg,var(--blue-light),var(--violet));
    box-shadow:0 12px 32px rgba(124,58,237,.5);position:relative;overflow:hidden;transition:.2s}
  .pill-blue:hover{background:linear-gradient(90deg,var(--blue-light),var(--violet));
    transform:translateY(-2px);box-shadow:0 16px 40px rgba(124,58,237,.62)}
  .pill-blue::after{content:"";position:absolute;top:0;left:-100%;width:100%;height:100%;
    background:linear-gradient(90deg,transparent,rgba(255,255,255,.22),transparent);
    animation:shine 3.2s ease-in-out infinite}
  @keyframes shine{0%{left:-100%}55%,100%{left:100%}}
  .pill-ghost{transition:.2s;backdrop-filter:blur(6px)}
  .pill-ghost:hover{transform:translateY(-2px);background:rgba(255,255,255,.12)}

  /* stat cards: glass card + border glow on hover */
  .stats .stat{background:#fff;border:1px solid var(--border);border-radius:16px;padding:26px 18px;
    box-shadow:0 8px 28px rgba(15,23,42,.06)}
  .stats .stat:hover{box-shadow:0 16px 40px rgba(37,99,235,.14);border-color:#bfdbfe}

  /* guides cards: glass lift */
  .guides .gcard{background:rgba(255,255,255,.85);backdrop-filter:blur(10px);border:1px solid var(--border)}
  .guides .gcard:hover{transform:translateY(-5px);box-shadow:0 20px 46px rgba(15,23,42,.14);border-color:#bfdbfe}

  /* danger band: warning glass card with ⚠ markers */
  .danger-band{background:linear-gradient(135deg,#fff5f5,#fff1f2);border:1px solid #fecaca;
    border-left:4px solid var(--err);border-radius:18px;box-shadow:0 12px 36px rgba(220,38,38,.10)}
  .danger-band ul{list-style:none;margin-left:0}
  .danger-band li{list-style:none;position:relative;padding-left:26px}
  .danger-band li::before{content:"⚠";position:absolute;left:0;top:4px;color:var(--err);font-weight:700}

  /* tier band: glowing gradient */
  .tier{background:linear-gradient(135deg,#eff6ff,#f5f3ff);border:1px solid #c4b5fd;
    box-shadow:0 10px 30px rgba(139,92,246,.14)}
  .tier a{background:linear-gradient(90deg,var(--blue-light),var(--violet));
    box-shadow:0 8px 20px rgba(124,58,237,.35)}
  .tier a:hover{background:linear-gradient(90deg,var(--blue-light),var(--violet));filter:brightness(1.08)}

  /* check form: glass card + focus glow ring */
  #check .panel{background:rgba(255,255,255,.92);backdrop-filter:blur(10px);
    border:1px solid var(--border);box-shadow:0 24px 60px rgba(15,23,42,.10)}
  input:focus,select:focus{outline:none;border-color:var(--blue);box-shadow:0 0 0 4px rgba(59,130,246,.15)}

  /* compare table: highlight the CrossAIO column */
  .compare table{background:#fff;border:1px solid var(--border);border-radius:16px;
    box-shadow:0 10px 30px rgba(15,23,42,.06);overflow:hidden}
  .compare table th:nth-child(3),.compare table td:nth-child(3){background:rgba(5,150,105,.06);
    border-left:1px solid #d1fae5}

  /* pricing tiers: glass cards */
  .ptier{background:rgba(255,255,255,.92);backdrop-filter:blur(10px);
    box-shadow:0 10px 30px rgba(15,23,42,.06);transition:.25s}
  .ptier:hover{transform:translateY(-4px);box-shadow:0 20px 46px rgba(15,23,42,.12)}
  .ptier.hot{border-color:var(--blue);box-shadow:0 18px 50px rgba(37,99,235,.18)}

  /* CTA band: dark grid texture + glow */
  .cta-band{position:relative;overflow:hidden;box-shadow:0 24px 60px rgba(15,10,60,.4)}
  .cta-band::before{content:"";position:absolute;inset:0;pointer-events:none;
    background-image:linear-gradient(rgba(255,255,255,.05) 1px,transparent 1px),
    linear-gradient(90deg,rgba(255,255,255,.05) 1px,transparent 1px);
    background-size:40px 40px}
  .cta-band h2,.cta-band p,.cta-band a{position:relative}

  /* FAQ cards */
  .faq details{transition:.2s}
  .faq details:hover{border-color:#bfdbfe;box-shadow:0 8px 26px rgba(37,99,235,.08)}

  /* gnav pill bar: subtle glass */
  .gnav{box-shadow:0 1px 0 rgba(15,23,42,.03)}
  .glink{transition:.15s}

  @media (prefers-reduced-motion: reduce){
    .spin,.typing i,.chat,.gcard,.fvisual,.site,.pricing-card,
    .particles i,.hero-glow i,.pill-blue::after{animation:none}
  }
"""

# ---------------------------------------------------------------------------
# 主页 JS（AI 对话动画 + 游客体检表单 + UTM 埋点）— 纯字符串避免 f-string 花括号
# zh 为历史原文；en/de/fr 同逻辑、同 API 端点、同事件名，仅翻译显示文案
# ---------------------------------------------------------------------------
_HOME_JS = """
const API = "/api/v1";
const RISK = {high:"🔴 高风险（CE 类目）", medium:"🟡 中风险", low:"🟢 低风险"};

// ---- 落地页曝光 + UTM 记忆（失败静默） ----
(function(){
  try{
    const q = new URLSearchParams(location.search);
    const utm = {};
    ["utm_source","utm_medium","utm_campaign"].forEach(k=>{ if(q.get(k)) utm[k]=q.get(k); });
    if(Object.keys(utm).length) localStorage.setItem("cb_utm", JSON.stringify(utm));
    fetch(API+"/analytics/track",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({event_type:"landing_view", platform:null, ...utm})}).catch(()=>{});
  }catch(e){}
})();
function esc(s){return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;");}

// ---- AI 对话动画（循环播放） ----
const CHAT_STEPS = [
  {html:`<div class="bubble fade-in"><b>CrossAIO：</b>你的「Baby Monitor」在 Otto 检出 GPSR 风险：<br>
    <span class="tag">缺德语警示语</span><span class="tag">缺欧代信息</span><span class="tag ok">产品标识 ✓</span><br>
    正在生成德语合规块…</div>`, delay:600},
  {html:`<div class="bubble fade-in" style="margin-top:8px"><b>✅ 已生成修复：</b>Georg-Büchner-Str. 8, 65439 …（欧代占位）+ "Warnhinweis: Nicht für Kinder unter 3 Jahren…" — 可直接粘贴进 listing。</div>`, delay:2600},
];
let chatTimer = setInterval(playChat, 9000);
async function playChat(){
  const box = document.getElementById("chatMsgs");
  if(!box) return;
  box.innerHTML = `<div class="typing fade-in"><i></i><i></i><i></i></div>`;
  await new Promise(r=>setTimeout(r,1100));
  box.innerHTML = "";
  for(const step of CHAT_STEPS){
    box.insertAdjacentHTML("beforeend", step.html);
    await new Promise(r=>setTimeout(r, step.delay));
  }
}
playChat();

// ---- 游客体检：免注册直接查 ----
const btnGo = document.getElementById("btnGo");
if(btnGo) btnGo.onclick = async () => {
  const out = document.getElementById("out");
  const name = document.getElementById("g_name").value.trim();
  const asin = document.getElementById("g_asin").value.trim().toUpperCase();
  const kws = document.getElementById("g_kw").value.split(",").map(s=>s.trim()).filter(Boolean);
  if(!name || !kws.length) return out.innerHTML = `<div class="msg err">请填写产品标题和关键词</div>`;
  if(asin && !/^[A-Z0-9]{10}$/.test(asin)) return out.innerHTML = `<div class="msg err">ASIN 须为 10 位字母/数字</div>`;
  btnGo.disabled = true; btnGo.textContent = "体检中…";
  try{
    const r = await fetch(API+"/products/gpsr/check-guest", {method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({product_name:name, keywords:kws, platform:document.getElementById("g_platform").value, asin:asin||null})});
    const d = await r.json();
    if(!r.ok) throw new Error(d.detail || "体检失败，请稍后再试");
    const checklist = d.checklist.map(c=>`<tr><td>${c.required?"必查":"建议"}</td><td><b>${esc(c.name)}</b><br><span class="hint">${esc(c.detail)}</span></td></tr>`).join("");
    out.innerHTML = `<div class="msg" style="background:#fff;border:1px solid var(--border)">
      ${asin?`<span class="badge">ASIN: ${esc(asin)}</span>`:""}
      <span class="badge">${RISK[d.risk_level]||d.risk_level}</span>
      <span class="badge">${esc(d.matched_categories)}</span>
      <span class="badge">警示语语言：${d.required_languages.map(l=>l.toUpperCase()).join(" / ")}</span>
      ${d.ce_directives.length?`<p style="margin-top:8px"><b>适用指令：</b>${d.ce_directives.map(esc).join("；")}</p>`:""}
      <table><tr><th style="width:60px">级别</th><th>检查项</th></tr>${checklist}</table>
      ${d.upsell_note?`<div class="msg err" style="margin-top:12px">${esc(d.upsell_note)}<br>
        <a href="/signup" style="color:var(--blue);font-weight:600">注册账号 / 升级解锁合规块 →</a></div>`:""}
      <div class="aiact-note">⚖️ <b>AI Act 合规缺口提醒：</b>本体检只覆盖 GPSR 产品安全。若你用 AI 客服接待买家，EU AI Act Art.50（2026-08-02 生效）要求每条回复明确告知「正在与 AI 对话」，违者最高罚 €1500 万或全球营收 3%。CrossAIO 的 AI 客服已原生内嵌当地语言告知 + 机器可读标记，同类工具几乎零内建。<a href="/gpsr-check/pricing" style="color:#1d4ed8;font-weight:600">看合规护城河 →</a></div>
    </div>`;
  }catch(e){ out.innerHTML = `<div class="msg err">${esc(e.message)}</div>`; }
  btnGo.disabled = false; btnGo.textContent = "开始免费体检 →";
};
"""

_HOME_JS_I18N = {
    "en": """
const API = "/api/v1";
const RISK = {high:"🔴 High risk (CE category)", medium:"🟡 Medium risk", low:"🟢 Low risk"};

// ---- landing view + UTM memory (silent on failure) ----
(function(){
  try{
    const q = new URLSearchParams(location.search);
    const utm = {};
    ["utm_source","utm_medium","utm_campaign"].forEach(k=>{ if(q.get(k)) utm[k]=q.get(k); });
    if(Object.keys(utm).length) localStorage.setItem("cb_utm", JSON.stringify(utm));
    fetch(API+"/analytics/track",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({event_type:"landing_view", platform:null, ...utm})}).catch(()=>{});
  }catch(e){}
})();
function esc(s){return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;");}

// ---- AI chat animation (loops) ----
const CHAT_STEPS = [
  {html:`<div class="bubble fade-in"><b>CrossAIO:</b> your "Baby Monitor" shows GPSR risks on Otto:<br>
    <span class="tag">missing German safety warning</span><span class="tag">missing EU Rep information</span><span class="tag ok">product marking ✓</span><br>
    generating the German compliance block…</div>`, delay:600},
  {html:`<div class="bubble fade-in" style="margin-top:8px"><b>✅ Fix generated:</b> Georg-Büchner-Str. 8, 65439 … (EU Rep placeholder) + "Warnhinweis: Nicht für Kinder unter 3 Jahren…" — ready to paste into your listing.</div>`, delay:2600},
];
let chatTimer = setInterval(playChat, 9000);
async function playChat(){
  const box = document.getElementById("chatMsgs");
  if(!box) return;
  box.innerHTML = `<div class="typing fade-in"><i></i><i></i><i></i></div>`;
  await new Promise(r=>setTimeout(r,1100));
  box.innerHTML = "";
  for(const step of CHAT_STEPS){
    box.insertAdjacentHTML("beforeend", step.html);
    await new Promise(r=>setTimeout(r, step.delay));
  }
}
playChat();

// ---- guest check: no sign-up needed ----
const btnGo = document.getElementById("btnGo");
if(btnGo) btnGo.onclick = async () => {
  const out = document.getElementById("out");
  const name = document.getElementById("g_name").value.trim();
  const asin = document.getElementById("g_asin").value.trim().toUpperCase();
  const kws = document.getElementById("g_kw").value.split(",").map(s=>s.trim()).filter(Boolean);
  if(!name || !kws.length) return out.innerHTML = `<div class="msg err">Please enter a product title and keywords</div>`;
  if(asin && !/^[A-Z0-9]{10}$/.test(asin)) return out.innerHTML = `<div class="msg err">ASIN must be 10 letters/digits</div>`;
  btnGo.disabled = true; btnGo.textContent = "checking…";
  try{
    const r = await fetch(API+"/products/gpsr/check-guest", {method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({product_name:name, keywords:kws, platform:document.getElementById("g_platform").value, asin:asin||null})});
    const d = await r.json();
    if(!r.ok) throw new Error(d.detail || "Check failed, please try again later");
    const checklist = d.checklist.map(c=>`<tr><td>${c.required?"Mandatory":"Recommended"}</td><td><b>${esc(c.name)}</b><br><span class="hint">${esc(c.detail)}</span></td></tr>`).join("");
    out.innerHTML = `<div class="msg" style="background:#fff;border:1px solid var(--border)">
      ${asin?`<span class="badge">ASIN: ${esc(asin)}</span>`:""}
      <span class="badge">${RISK[d.risk_level]||d.risk_level}</span>
      <span class="badge">${esc(d.matched_categories)}</span>
      <span class="badge">Warning language: ${d.required_languages.map(l=>l.toUpperCase()).join(" / ")}</span>
      ${d.ce_directives.length?`<p style="margin-top:8px"><b>Applicable directives:</b> ${d.ce_directives.map(esc).join("; ")}</p>`:""}
      <table><tr><th style="width:60px">Level</th><th>Check item</th></tr>${checklist}</table>
      ${d.upsell_note?`<div class="msg err" style="margin-top:12px">${esc(d.upsell_note)}<br>
        <a href="/en/signup" style="color:var(--blue);font-weight:600">Create an account / upgrade to unlock compliance blocks →</a></div>`:""}
      <div class="aiact-note">⚖️ <b>AI Act compliance gap reminder:</b> this check covers only GPSR product safety. If you use AI customer service for buyers, EU AI Act Art.50 (effective 2026-08-02) requires every reply to disclose clearly "you are chatting with an AI"; non-compliance is fined up to €15 million or 3% of global revenue. CrossAIO's AI customer service natively embeds local-language disclosure + a machine-readable marker — almost none of the comparable tools have this built in. <a href="/en/gpsr-check/pricing" style="color:#1d4ed8;font-weight:600">see the compliance moat →</a></div>
    </div>`;
  }catch(e){ out.innerHTML = `<div class="msg err">${esc(e.message)}</div>`; }
  btnGo.disabled = false; btnGo.textContent = "Start your free check →";
};
""",
    "de": """
const API = "/api/v1";
const RISK = {high:"🔴 Hohes Risiko (CE-Kategorie)", medium:"🟡 Mittleres Risiko", low:"🟢 Geringes Risiko"};

// ---- Landing-View + UTM-Merkung (bei Fehler still) ----
(function(){
  try{
    const q = new URLSearchParams(location.search);
    const utm = {};
    ["utm_source","utm_medium","utm_campaign"].forEach(k=>{ if(q.get(k)) utm[k]=q.get(k); });
    if(Object.keys(utm).length) localStorage.setItem("cb_utm", JSON.stringify(utm));
    fetch(API+"/analytics/track",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({event_type:"landing_view", platform:null, ...utm})}).catch(()=>{});
  }catch(e){}
})();
function esc(s){return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;");}

// ---- KI-Chat-Animation (läuft in Schleife) ----
const CHAT_STEPS = [
  {html:`<div class="bubble fade-in"><b>CrossAIO:</b> dein „Baby Monitor" zeigt auf Otto GPSR-Risiken:<br>
    <span class="tag">deutscher Sicherheitshinweis fehlt</span><span class="tag">Angaben zum EU-Verantwortlichen fehlen</span><span class="tag ok">Produktkennzeichnung ✓</span><br>
    deutscher Compliance-Block wird generiert…</div>`, delay:600},
  {html:`<div class="bubble fade-in" style="margin-top:8px"><b>✅ Fix generiert:</b> Georg-Büchner-Str. 8, 65439 … (EU-Verantwortlicher-Platzhalter) + "Warnhinweis: Nicht für Kinder unter 3 Jahren…" — direkt in dein Listing einfügbar.</div>`, delay:2600},
];
let chatTimer = setInterval(playChat, 9000);
async function playChat(){
  const box = document.getElementById("chatMsgs");
  if(!box) return;
  box.innerHTML = `<div class="typing fade-in"><i></i><i></i><i></i></div>`;
  await new Promise(r=>setTimeout(r,1100));
  box.innerHTML = "";
  for(const step of CHAT_STEPS){
    box.insertAdjacentHTML("beforeend", step.html);
    await new Promise(r=>setTimeout(r, step.delay));
  }
}
playChat();

// ---- Gast-Check: ohne Registrierung direkt prüfen ----
const btnGo = document.getElementById("btnGo");
if(btnGo) btnGo.onclick = async () => {
  const out = document.getElementById("out");
  const name = document.getElementById("g_name").value.trim();
  const asin = document.getElementById("g_asin").value.trim().toUpperCase();
  const kws = document.getElementById("g_kw").value.split(",").map(s=>s.trim()).filter(Boolean);
  if(!name || !kws.length) return out.innerHTML = `<div class="msg err">Bitte Produkttitel und Keywords angeben</div>`;
  if(asin && !/^[A-Z0-9]{10}$/.test(asin)) return out.innerHTML = `<div class="msg err">ASIN muss aus 10 Buchstaben/Ziffern bestehen</div>`;
  btnGo.disabled = true; btnGo.textContent = "wird geprüft…";
  try{
    const r = await fetch(API+"/products/gpsr/check-guest", {method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({product_name:name, keywords:kws, platform:document.getElementById("g_platform").value, asin:asin||null})});
    const d = await r.json();
    if(!r.ok) throw new Error(d.detail || "Prüfung fehlgeschlagen, bitte später erneut versuchen");
    const checklist = d.checklist.map(c=>`<tr><td>${c.required?"Pflicht":"Empfohlen"}</td><td><b>${esc(c.name)}</b><br><span class="hint">${esc(c.detail)}</span></td></tr>`).join("");
    out.innerHTML = `<div class="msg" style="background:#fff;border:1px solid var(--border)">
      ${asin?`<span class="badge">ASIN: ${esc(asin)}</span>`:""}
      <span class="badge">${RISK[d.risk_level]||d.risk_level}</span>
      <span class="badge">${esc(d.matched_categories)}</span>
      <span class="badge">Hinweissprache: ${d.required_languages.map(l=>l.toUpperCase()).join(" / ")}</span>
      ${d.ce_directives.length?`<p style="margin-top:8px"><b>Anwendbare Richtlinien:</b> ${d.ce_directives.map(esc).join("; ")}</p>`:""}
      <table><tr><th style="width:60px">Stufe</th><th>Prüfpunkt</th></tr>${checklist}</table>
      ${d.upsell_note?`<div class="msg err" style="margin-top:12px">${esc(d.upsell_note)}<br>
        <a href="/de/signup" style="color:var(--blue);font-weight:600">Konto erstellen / upgraden, um Compliance-Blöcke freizuschalten →</a></div>`:""}
      <div class="aiact-note">⚖️ <b>Hinweis zur AI-Act-Offenlegungslücke:</b> dieser Check deckt nur die GPSR-Produktsicherheit ab. Wenn du Käufer mit KI-Kundenservice betreibst, schreibt der EU AI Act Art.50 (gültig ab 2026-08-02) vor, jede Antwort klar als „Sie chatten mit einer KI" zu kennzeichnen — bei Verstoß drohen Bußgelder bis zu €15 Mio. oder 3 % des weltweiten Umsatzes. CrossAIOs KI-Kundenservice blendet die Landessprachen-Offenlegung + maschinenlesbare Kennzeichnung bereits nativ ein — kaum ein vergleichbares Tool bietet das integriert. <a href="/de/gpsr-check/pricing" style="color:#1d4ed8;font-weight:600">Compliance-Vorsprung ansehen →</a></div>
    </div>`;
  }catch(e){ out.innerHTML = `<div class="msg err">${esc(e.message)}</div>`; }
  btnGo.disabled = false; btnGo.textContent = "Kostenlosen Check starten →";
};
""",
    "fr": """
const API = "/api/v1";
const RISK = {high:"🔴 Risque élevé (catégorie CE)", medium:"🟡 Risque moyen", low:"🟢 Risque faible"};

// ---- vue de landing + mémoire UTM (silencieux en cas d'échec) ----
(function(){
  try{
    const q = new URLSearchParams(location.search);
    const utm = {};
    ["utm_source","utm_medium","utm_campaign"].forEach(k=>{ if(q.get(k)) utm[k]=q.get(k); });
    if(Object.keys(utm).length) localStorage.setItem("cb_utm", JSON.stringify(utm));
    fetch(API+"/analytics/track",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({event_type:"landing_view", platform:null, ...utm})}).catch(()=>{});
  }catch(e){}
})();
function esc(s){return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;");}

// ---- animation du chat IA (en boucle) ----
const CHAT_STEPS = [
  {html:`<div class="bubble fade-in"><b>CrossAIO :</b> votre « Baby Monitor » présente des risques GPSR sur Otto :<br>
    <span class="tag">avertissement de sécurité allemand manquant</span><span class="tag">informations du représentant UE manquantes</span><span class="tag ok">marquage du produit ✓</span><br>
    génération du bloc de conformité allemand…</div>`, delay:600},
  {html:`<div class="bubble fade-in" style="margin-top:8px"><b>✅ Correctif généré :</b> Georg-Büchner-Str. 8, 65439 … (représentant UE, valeur factice) + "Warnhinweis: Nicht für Kinder unter 3 Jahren…" — prêt à coller dans votre listing.</div>`, delay:2600},
];
let chatTimer = setInterval(playChat, 9000);
async function playChat(){
  const box = document.getElementById("chatMsgs");
  if(!box) return;
  box.innerHTML = `<div class="typing fade-in"><i></i><i></i><i></i></div>`;
  await new Promise(r=>setTimeout(r,1100));
  box.innerHTML = "";
  for(const step of CHAT_STEPS){
    box.insertAdjacentHTML("beforeend", step.html);
    await new Promise(r=>setTimeout(r, step.delay));
  }
}
playChat();

// ---- vérification invité : sans inscription ----
const btnGo = document.getElementById("btnGo");
if(btnGo) btnGo.onclick = async () => {
  const out = document.getElementById("out");
  const name = document.getElementById("g_name").value.trim();
  const asin = document.getElementById("g_asin").value.trim().toUpperCase();
  const kws = document.getElementById("g_kw").value.split(",").map(s=>s.trim()).filter(Boolean);
  if(!name || !kws.length) return out.innerHTML = `<div class="msg err">Veuillez saisir un titre et des mots-clés</div>`;
  if(asin && !/^[A-Z0-9]{10}$/.test(asin)) return out.innerHTML = `<div class="msg err">L'ASIN doit contenir 10 lettres/chiffres</div>`;
  btnGo.disabled = true; btnGo.textContent = "vérification en cours…";
  try{
    const r = await fetch(API+"/products/gpsr/check-guest", {method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({product_name:name, keywords:kws, platform:document.getElementById("g_platform").value, asin:asin||null})});
    const d = await r.json();
    if(!r.ok) throw new Error(d.detail || "Échec de la vérification, réessayez plus tard");
    const checklist = d.checklist.map(c=>`<tr><td>${c.required?"Obligatoire":"Recommandé"}</td><td><b>${esc(c.name)}</b><br><span class="hint">${esc(c.detail)}</span></td></tr>`).join("");
    out.innerHTML = `<div class="msg" style="background:#fff;border:1px solid var(--border)">
      ${asin?`<span class="badge">ASIN : ${esc(asin)}</span>`:""}
      <span class="badge">${RISK[d.risk_level]||d.risk_level}</span>
      <span class="badge">${esc(d.matched_categories)}</span>
      <span class="badge">Langue des avertissements : ${d.required_languages.map(l=>l.toUpperCase()).join(" / ")}</span>
      ${d.ce_directives.length?`<p style="margin-top:8px"><b>Directives applicables :</b> ${d.ce_directives.map(esc).join(" ; ")}</p>`:""}
      <table><tr><th style="width:60px">Niveau</th><th>Point de contrôle</th></tr>${checklist}</table>
      ${d.upsell_note?`<div class="msg err" style="margin-top:12px">${esc(d.upsell_note)}<br>
        <a href="/fr/signup" style="color:var(--blue);font-weight:600">Créer un compte / passer à un forfait supérieur pour débloquer les blocs de conformité →</a></div>`:""}
      <div class="aiact-note">⚖️ <b>Rappel sur l'écart de conformité AI Act :</b> cette vérification couvre uniquement la sécurité des produits GPSR. Si vous utilisez un service client IA pour les acheteurs, l'EU AI Act Art.50 (en vigueur depuis le 2026-08-02) impose de signaler clairement « vous discutez avec une IA » dans chaque réponse — sous peine d'amende jusqu'à 15 M€ ou 3 % du chiffre d'affaires mondial. Le service client IA de CrossAIO intègre nativement la divulgation en langue locale + un marqueur lisible par machine — quasi aucun outil comparable ne l'intègre. <a href="/fr/gpsr-check/pricing" style="color:#1d4ed8;font-weight:600">voir l'avantage conformité →</a></div>
    </div>`;
  }catch(e){ out.innerHTML = `<div class="msg err">${esc(e.message)}</div>`; }
  btnGo.disabled = false; btnGo.textContent = "Lancer la vérification gratuite →";
};
"""
}


def _home_js(lang: str = "zh") -> str:
    return _HOME_JS if lang == "zh" else _HOME_JS_I18N[lang]


_AIACT_BANNER = """
<div class="aiact-banner">
  <span class="ic">⚖️</span>
  <p><b>EU AI Act Art.50 已生效（2026-08-02）：</b>用 AI 客服接待买家的卖家，必须明确告知「您正在与 AI 对话」，违者最高罚 €1500 万或全球营收 3%。CrossAIO 的 AI 客服已<b>原生内嵌</b>当地语言告知 + 机器可读标记——同类工具（Responso / eDesk 等）几乎零内建。 <a href="/gpsr-check/pricing">看合规护城河 →</a></p>
</div>"""

_AIACT_BANNER_I18N = {
    "en": """
<div class="aiact-banner">
  <span class="ic">⚖️</span>
  <p><b>EU AI Act Art.50 is in effect (2026-08-02):</b> sellers who use AI customer service for buyers must clearly disclose "you are chatting with an AI"; non-compliance is fined up to €15 million or 3% of global revenue. CrossAIO's AI customer service <b>natively embeds</b> local-language disclosure + a machine-readable marker — comparable tools (Responso / eDesk, etc.) almost none have this built in. <a href="/en/gpsr-check/pricing">see the compliance moat →</a></p>
</div>""",
    "de": """
<div class="aiact-banner">
  <span class="ic">⚖️</span>
  <p><b>EU AI Act Art.50 ist in Kraft (2026-08-02):</b> Verkäufer, die KI-Kundenservice für Käufer einsetzen, müssen klar „Sie chatten mit einer KI" offenlegen — bei Verstoß drohen Bußgelder bis zu €15 Mio. oder 3 % des weltweiten Umsatzes. CrossAIOs KI-Kundenservice <b>blendet die Landessprachen-Offenlegung + maschinenlesbare Kennzeichnung bereits nativ ein</b> — vergleichbare Tools (Responso / eDesk u. a.) bieten das kaum integriert. <a href="/de/gpsr-check/pricing">Compliance-Vorsprung ansehen →</a></p>
</div>""",
    "fr": """
<div class="aiact-banner">
  <span class="ic">⚖️</span>
  <p><b>L'EU AI Act Art.50 est en vigueur (2026-08-02) :</b> les vendeurs qui utilisent un service client IA pour les acheteurs doivent signaler clairement « vous discutez avec une IA » ; non-conformité passible d'amende jusqu'à 15 M€ ou 3 % du chiffre d'affaires mondial. Le service client IA de CrossAIO <b>intègre nativement</b> la divulgation en langue locale + un marqueur lisible par machine — les outils comparables (Responso / eDesk, etc.) l'intègrent quasi aucunement. <a href="/fr/gpsr-check/pricing">voir l'avantage conformité →</a></p>
</div>""",
}


def _aiact_banner(lang: str = "zh") -> str:
    return _AIACT_BANNER if lang == "zh" else _AIACT_BANNER_I18N[lang]

_PLATFORM_MARKS = {
    "amazon": ('<img class="mark-img" src="/img/logos/amazon.svg" alt="Amazon" />',
               "欧洲站 + 美国站", "英/德/法/意/西 等 9 国 + 🇺🇸 美国 · en"),
    "ebay": ('<img class="mark-img" src="/img/logos/ebay.svg" alt="eBay" />',
             "eBay", "英/德/法/意/西 · en"),
    "allegro": ('<img class="mark-img" src="/img/logos/allegro.svg" alt="Allegro" />',
                "Allegro", "🇵🇱 波兰/捷克/匈牙利 · pl"),
    "otto": ('<img class="mark-img" src="/img/logos/otto.svg" alt="Otto" />',
             "Otto", "🇩🇪 德国 · de"),
    "cdiscount": ('<img class="mark-img" src="/img/logos/cdiscount.png" alt="Cdiscount" />',
                  "Cdiscount", "🇫🇷 法国 · fr"),
    "emag": ('<img class="mark-img" src="/img/logos/emag.svg" alt="eMAG" />',
             "eMAG", "🇷🇴 罗马尼亚/匈/保 · ro"),
    "tiktok": ('<img class="mark-img" src="/img/logos/tiktok.svg" alt="TikTok Shop" />',
               "TikTok Shop", "🇬🇧🇺🇸 英美 + 🇪🇸🇮🇹🇩🇪🇫🇷 欧盟 · en"),
    "fruugo": ('<svg viewBox="0 0 106 40" width="100" height="38" role="img" aria-label="Fruugo"><text x="0" y="27" font-family="Arial,Helvetica,sans-serif" font-weight="800" font-size="27" letter-spacing="-0.5"><tspan fill="#94C11F">fru</tspan><tspan fill="#5FA02E">ugo</tspan></text></svg>',
               "Fruugo", "泛欧 20+ 国 · en"),
    "walmart": ('<img class="mark-img" src="/img/logos/walmart.svg" alt="Walmart" />',
                "Walmart", "🇺🇸 美国 · en"),
    "kaufland": ('<img class="mark-img" src="/img/logos/kaufland.svg" alt="Kaufland" />',
                 "Kaufland", "🇩🇪 德/奥/捷/斯 · de"),
    "zalando": ('<img class="mark-img" src="/img/logos/zalando.svg" alt="Zalando" />',
                "Zalando", "🇪🇺 欧洲时尚 · en→多语言"),
    "bol": ('<svg viewBox="0 0 130 40" width="118" height="36" role="img" aria-label="bol.com"><text x="0" y="28" font-family="Arial,Helvetica,sans-serif" font-weight="800" font-size="26" fill="#0000A4">bol.</text><text x="58" y="28" font-family="Arial,Helvetica,sans-serif" font-weight="800" font-size="26" fill="#F29B00">com</text></svg>',
            "bol.com", "🇳🇱 荷兰/比利时 · nl"),
}

# 平台字标卡的 (name, meta) 按语言翻译；mark 始终复用 _PLATFORM_MARKS（官方 logo 图片，fruugo/bol 无 logo 保留内联 SVG 字标）
_PLATFORM_META_I18N = {
    "en": {
        "amazon": ("Amazon EU + US", "UK/DE/FR/IT/ES & 9 more + 🇺🇸 US · en"),
        "ebay": ("eBay", "UK/DE/FR/IT/ES · en"),
        "allegro": ("Allegro", "🇵🇱 PL/CZ/HU · pl"),
        "otto": ("Otto", "🇩🇪 Germany · de"),
        "cdiscount": ("Cdiscount", "🇫🇷 France · fr"),
        "emag": ("eMAG", "🇷🇴 RO/HU/BG · ro"),
        "tiktok": ("TikTok Shop", "🇬🇧🇺🇸 UK/US + 🇪🇸🇮🇹🇩🇪🇫🇷 EU · en"),
        "fruugo": ("Fruugo", "pan-EU 20+ countries · en"),
        "walmart": ("Walmart", "🇺🇸 US · en"),
        "kaufland": ("Kaufland", "🇩🇪 DE/AT/CZ/SK · de"),
        "zalando": ("Zalando", "🇪🇺 European fashion · en→multi"),
        "bol": ("bol.com", "🇳🇱 NL/BE · nl"),
    },
    "de": {
        "amazon": ("Amazon EU + US", "EN/DE/FR/IT/ES u. 9 weitere + 🇺🇸 USA · en"),
        "ebay": ("eBay", "EN/DE/FR/IT/ES · en"),
        "allegro": ("Allegro", "🇵🇱 PL/CZ/HU · pl"),
        "otto": ("Otto", "🇩🇪 Deutschland · de"),
        "cdiscount": ("Cdiscount", "🇫🇷 Frankreich · fr"),
        "emag": ("eMAG", "🇷🇴 RO/HU/BG · ro"),
        "tiktok": ("TikTok Shop", "🇬🇧🇺🇸 UK/US + 🇪🇸🇮🇹🇩🇪🇫🇷 EU · en"),
        "fruugo": ("Fruugo", "paneuropäisch 20+ Länder · en"),
        "walmart": ("Walmart", "🇺🇸 USA · en"),
        "kaufland": ("Kaufland", "🇩🇪 DE/AT/CZ/SK · de"),
        "zalando": ("Zalando", "🇪🇺 europäische Mode · en→mehrsprachig"),
        "bol": ("bol.com", "🇳🇱 NL/BE · nl"),
    },
    "fr": {
        "amazon": ("Amazon EU + US", "UK/DE/FR/IT/ES et 9 de plus + 🇺🇸 US · en"),
        "ebay": ("eBay", "UK/DE/FR/IT/ES · en"),
        "allegro": ("Allegro", "🇵🇱 PL/CZ/HU · pl"),
        "otto": ("Otto", "🇩🇪 Allemagne · de"),
        "cdiscount": ("Cdiscount", "🇫🇷 France · fr"),
        "emag": ("eMAG", "🇷🇴 RO/HU/BG · ro"),
        "tiktok": ("TikTok Shop", "🇬🇧🇺🇸 UK/US + 🇪🇸🇮🇹🇩🇪🇫🇷 UE · en"),
        "fruugo": ("Fruugo", "paneuropéen 20+ pays · en"),
        "walmart": ("Walmart", "🇺🇸 US · en"),
        "kaufland": ("Kaufland", "🇩🇪 DE/AT/CZ/SK · de"),
        "zalando": ("Zalando", "🇪🇺 mode européenne · en→multi"),
        "bol": ("bol.com", "🇳🇱 NL/BE · nl"),
    },
}

# 五大功能板块数据（原单页 5 个 tab → 5 个独立板块）
_FBLOCKS = [
    ("p1", "🛡️", "GPSR 合规引擎：<br>缺一项就被下架，先查再上", [
        "7 大 CE 类目规则库自动识别 <span>— 玩具 / 无线电 / 电子 / PPE / 母婴 / 食品接触 / 化妆品</span>",
        "当地语言安全警示语自动生成 <span>— 7 语言内置，可粘贴进 listing</span>",
        "GPSR 法定检查清单逐项核对 <span>— 欧代 / 产品标识 / CE 标识 / 说明书</span>",
        "体检免费且<span>免注册</span>，不消耗生成额度",
    ], [
        (("风险等级", '<span class="v bad">🔴 高风险（CE 类目）</span>', "⚠️"),
         ("适用指令", '<span class="v">EN 71 + GPSD</span>', "玩具"),
         ("警示语语言", '<span class="v blue">PL 波兰语</span>', "Allegro"),
         ("欧代信息", '<span class="v bad">缺失</span>', "必查"),
         ("合规块生成", '<span class="v up">Starter 解锁</span>', "€29/月")),
    ]),
    ("p2", "📦", "产品描述生成：<br>5 秒出一套合规 listing", [
        "标题 / 五点描述 / 详情页 / 后台搜索词一次生成",
        "每平台按各自字数硬限制校验 <span>— 超限自动改写</span>",
        "平台合规校验 + 优化评分 <span>— 上架前就知道会不会被压</span>",
        "16 种语言 <span>— 覆盖欧洲主要市场</span>",
    ], [
        (("标题字符", '<span class="v blue">187 / 200</span>', "Amazon EU"),
         ("五点描述", '<span class="v">5 条 ✓</span>', "含关键词"),
         ("平台合规", '<span class="v up">✅ 通过</span>', "0 违规"),
         ("优化评分", '<span class="v up">92 / 100</span>', "语义覆盖 8/8")),
    ]),
    ("p3", "🌍", "欧洲多平台矩阵：<br>一次输入，12 平台批量本地化", [
        "Amazon EU + US / eBay / Allegro / Otto / Cdiscount / eMAG / TikTok Shop / Fruugo / Walmart / Kaufland / Zalando / bol.com",
        "语言按平台自动匹配 <span>— Allegro→波兰语、Otto→德语、Cdiscount→法语</span>",
        "单平台失败不影响其余平台，逐平台计数",
        "<b>No Shopify required</b> <span>— 独立工作台注册即用</span>",
    ], [
        (("Allegro 🇵🇱", '<span class="v blue">pl</span>', "75 字符硬限"),
         ("Otto 🇩🇪", '<span class="v blue">de</span>', "纯德语站"),
         ("eMAG 🇷🇴", '<span class="v blue">ro</span>', "150 字符"),
         ("Fruugo 🇪🇺", '<span class="v blue">en</span>', "泛欧主目录")),
    ]),
    ("p4", "💬", "AI 客服：<br>7×24 自动回复买家消息", [
        "意图自动分类 <span>— 物流 / 退货 / 投诉 / 售前咨询</span>",
        "情绪检测，高风险负面自动建议转人工",
        "物流查询自动提取订单号",
        "客服成本从 €2000+/月 <span>降到一杯咖啡价</span>",
    ], [
        (("买家消息", '<span class="v">"Where is my order?"</span>', "EN"),
         ("意图识别", '<span class="v blue">物流查询</span>', "置信 0.95"),
         ("订单号提取", '<span class="v">#402-188</span>', "✓"),
         ("情绪", '<span class="v up">平稳</span>', "无需转人工")),
    ]),
    ("p5", "📣", "广告文案：<br>按平台字数硬限制一次生成", [
        "Facebook / Google / TikTok 三平台适配",
        "主文案、标题、描述、CTA、话题标签全配齐",
        "字数硬校验 <span>— 不会被平台截断</span>",
        "站外投流不用反复琢磨文案格式",
    ], [
        (("Facebook", '<span class="v">主文案 118 字</span>', "限 125 ✓"),
         ("Google", '<span class="v">标题 28 字</span>', "限 30 ✓"),
         ("TikTok", '<span class="v">文案 + 5 标签</span>', "限 100 ✓")),
    ]),
]

_FBLOCKS_EN = [
    ("p1", "🛡️", "GPSR compliance engine:<br>one missing item can get your listing delisted — check before you list", [
        "auto-detects 7 CE category rule sets <span>— toys / radio equipment / electronics / PPE / baby products / food-contact / cosmetics</span>",
        "auto-generates local-language safety warnings <span>— 7 languages built in, ready to paste into your listing</span>",
        "checks the GPSR legal checklist item by item <span>— EU Rep / product marking / CE marking / instructions</span>",
        "the check is free and <span>needs no sign-up</span>, no generation credits consumed",
    ], [
        (("Risk level", '<span class="v bad">🔴 High risk (CE)</span>', "⚠️"),
         ("Directives", '<span class="v">EN 71 + GPSD</span>', "toys"),
         ("Warning lang", '<span class="v blue">PL Polish</span>', "Allegro"),
         ("EU Rep info", '<span class="v bad">missing</span>', "Mandatory"),
         ("Compliance block", '<span class="v up">Starter unlock</span>', "€29/month")),
    ]),
    ("p2", "📦", "Product description generator:<br>a compliant listing in 5 seconds", [
        "title / bullet points / description / backend search terms, generated all at once",
        "validates each platform's strict character limits <span>— auto-rewrite when over the limit</span>",
        "platform compliance validation + optimization score <span>— know before you list if it gets suppressed</span>",
        "16 languages <span>— covering major European markets</span>",
    ], [
        (("Title chars", '<span class="v blue">187 / 200</span>', "Amazon EU"),
         ("Bullet points", '<span class="v">5 ✓</span>', "with keywords"),
         ("Platform check", '<span class="v up">✅ passed</span>', "0 violations"),
         ("Optimization", '<span class="v up">92 / 100</span>', "semantic coverage 8/8")),
    ]),
    ("p3", "🌍", "Multi-platform matrix:<br>one input, 12 platforms batch-localized", [
        "Amazon EU + US / eBay / Allegro / Otto / Cdiscount / eMAG / TikTok Shop / Fruugo / Walmart / Kaufland / Zalando / bol.com",
        "language auto-matched per platform <span>— Allegro→Polish, Otto→German, Cdiscount→French</span>",
        "one platform failing doesn't block the others, counted platform by platform",
        "<b>No Shopify required</b> <span>— standalone workbench, sign up and start instantly</span>",
    ], [
        (("Allegro 🇵🇱", '<span class="v blue">pl</span>', "75-char hard limit"),
         ("Otto 🇩🇪", '<span class="v blue">de</span>', "German-only"),
         ("eMAG 🇷🇴", '<span class="v blue">ro</span>', "150 chars"),
         ("Fruugo 🇪🇺", '<span class="v blue">en</span>', "pan-EU catalog")),
    ]),
    ("p4", "💬", "AI customer service:<br>auto-replies to buyer messages 7×24", [
        "intent classification <span>— shipping / returns / complaints / pre-sales</span>",
        "sentiment detection, high-risk negatives auto-suggest hand off to a human",
        "auto-extracts order numbers from shipping queries",
        "service cost from €2000+/month <span>down to the price of a coffee</span>",
    ], [
        (("Buyer msg", '<span class="v">"Where is my order?"</span>', "EN"),
         ("Intent", '<span class="v blue">shipping query</span>', "conf. 0.95"),
         ("Order no.", '<span class="v">#402-188</span>', "✓"),
         ("Sentiment", '<span class="v up">calm</span>', "no handoff needed")),
    ]),
    ("p5", "📣", "Ad copy generator:<br>generated in one pass, per platform limits", [
        "Facebook / Google / TikTok, three platforms adapted",
        "main copy, title, description, CTA, hashtags all included",
        "strict character validation <span>— never truncated by the platform</span>",
        "off-platform ad campaigns, no more tuning copy formats by hand",
    ], [
        (("Facebook", '<span class="v">main copy 118</span>', "limit 125 ✓"),
         ("Google", '<span class="v">title 28</span>', "limit 30 ✓"),
         ("TikTok", '<span class="v">copy + 5 tags</span>', "limit 100 ✓")),
    ]),
]

_FBLOCKS_DE = [
    ("p1", "🛡️", "GPSR-Compliance-Engine:<br>ein fehlender Punkt kann zum De-Listing führen — erst prüfen, dann listen", [
        "erkennt 7 CE-Kategorie-Regelwerke automatisch <span>— Spielzeug / Funkgeräte / Elektronik / PPE / Babyprodukte / Lebensmittelkontakt / Kosmetik</span>",
        "erzeugt Sicherheitshinweise in Landessprache automatisch <span>— 7 Sprachen integriert, direkt ins Listing einfügbar</span>",
        "prüft die GPSR-Gesetz-Checkliste Punkt für Punkt <span>— EU-Verantwortlicher / Produktkennzeichnung / CE-Kennzeichnung / Anleitung</span>",
        "der Check ist kostenlos und <span>ohne Registrierung</span>, verbraucht kein Generierungskontingent",
    ], [
        (("Risikostufe", '<span class="v bad">🔴 Hohes Risiko (CE)</span>', "⚠️"),
         ("Richtlinien", '<span class="v">EN 71 + GPSD</span>', "Spielzeug"),
         ("Hinweissprache", '<span class="v blue">PL Polnisch</span>', "Allegro"),
         ("EU-Verantw.", '<span class="v bad">fehlt</span>', "Pflicht"),
         ("Compliance-Block", '<span class="v up">Starter schaltet frei</span>', "€29/Monat")),
    ]),
    ("p2", "📦", "Produktbeschreibungs-Generator:<br>ein konformes Listing in 5 Sekunden", [
        "Titel / Bulletpoints / Beschreibung / Backend-Suchbegriffe auf einmal generieren",
        "prüft die harten Zeichenlimits jeder Plattform <span>— automatisches Umschreiben bei Überschreitung</span>",
        "Plattform-Konformitätsprüfung + Optimierungs-Score <span>— vor dem Listing wissen, ob es gedrückt wird</span>",
        "16 Sprachen <span>— deckt die wichtigsten europäischen Märkte ab</span>",
    ], [
        (("Titelzeichen", '<span class="v blue">187 / 200</span>', "Amazon EU"),
         ("Bulletpoints", '<span class="v">5 ✓</span>', "mit Keywords"),
         ("Plattform-Check", '<span class="v up">✅ bestanden</span>', "0 Verstöße"),
         ("Optimierung", '<span class="v up">92 / 100</span>', "semantische Abdeckung 8/8")),
    ]),
    ("p3", "🌍", "Multi-Plattform-Matrix:<br>eine Eingabe, 12 Plattformen Stapel-Lokalisierung", [
        "Amazon EU + US / eBay / Allegro / Otto / Cdiscount / eMAG / TikTok Shop / Fruugo / Walmart / Kaufland / Zalando / bol.com",
        "Sprache je Plattform automatisch zugeordnet <span>— Allegro→Polnisch, Otto→Deutsch, Cdiscount→Französisch</span>",
        "ein Plattformfehler blockiert die anderen nicht, zählt je Plattform",
        "<b>No Shopify required</b> <span>— eigenständige Workbench, Registrierung und sofort loslegen</span>",
    ], [
        (("Allegro 🇵🇱", '<span class="v blue">pl</span>', "75-Zeichen-Hartlimit"),
         ("Otto 🇩🇪", '<span class="v blue">de</span>', "reiner Deutsch-Stand"),
         ("eMAG 🇷🇴", '<span class="v blue">ro</span>', "150 Zeichen"),
         ("Fruugo 🇪🇺", '<span class="v blue">en</span>', "paneuropäischer Katalog")),
    ]),
    ("p4", "💬", "KI-Kundenservice:<br>beantwortet Käufernachrichten 7×24 automatisch", [
        "Absichtserkennung automatisch <span>— Versand / Retouren / Beschwerden / Vorverkauf</span>",
        "Stimmungsanalyse, bei hochriskantem Negativempfehlung an einen Menschen zu übergeben",
        "extrahiert Bestellnummern aus Versandanfragen automatisch",
        "Servicekosten von €2000+/Monat <span>runter auf Kaffeepreis</span>",
    ], [
        (("Käufer-Nachr.", '<span class="v">"Where is my order?"</span>', "EN"),
         ("Absicht", '<span class="v blue">Versand-Anfrage</span>', "Konf. 0.95"),
         ("Bestellnr.", '<span class="v">#402-188</span>', "✓"),
         ("Stimmung", '<span class="v up">ruhig</span>', "keine Übergabe nötig")),
    ]),
    ("p5", "📣", "Anzeigen-Texte:<br>auf einmal, je Plattform-Hartlimit erzeugt", [
        "Facebook / Google / TikTok, drei Plattformen angepasst",
        "Haupttext, Titel, Beschreibung, CTA, Hashtags komplett",
        "harte Zeichenprüfung <span>— nie von der Plattform abgeschnitten</span>",
        "externe Werbekampagnen, ohne ständiges Tüfteln am Anzeigenformat",
    ], [
        (("Facebook", '<span class="v">Haupttext 118</span>', "Limit 125 ✓"),
         ("Google", '<span class="v">Titel 28</span>', "Limit 30 ✓"),
         ("TikTok", '<span class="v">Text + 5 Tags</span>', "Limit 100 ✓")),
    ]),
]

_FBLOCKS_FR = [
    ("p1", "🛡️", "Moteur de conformité GPSR :<br>un élément manquant peut entraîner le déréférencement — vérifiez avant de mettre en ligne", [
        "détecte automatiquement 7 ensembles de règles CE <span>— jouets / équipement radio / électronique / EPI / puériculture / contact alimentaire / cosmétiques</span>",
        "génère automatiquement les avertissements de sécurité en langue locale <span>— 7 langues intégrées, prêts à coller dans votre listing</span>",
        "vérifie point par point la liste de contrôle légale GPSR <span>— représentant UE / marquage du produit / marquage CE / notice</span>",
        "la vérification est gratuite et <span>sans inscription</span>, sans consommation de crédits de génération",
    ], [
        (("Niveau de risque", '<span class="v bad">🔴 Risque élevé (CE)</span>', "⚠️"),
         ("Directives", '<span class="v">EN 71 + GPSD</span>', "jouets"),
         ("Langue avert.", '<span class="v blue">PL polonais</span>', "Allegro"),
         ("Infos repr. UE", '<span class="v bad">manquant</span>', "Obligatoire"),
         ("Bloc conformité", '<span class="v up">Starter débloque</span>', "€29/mois")),
    ]),
    ("p2", "📦", "Générateur de descriptions produit :<br>un listing conforme en 5 secondes", [
        "titre / puces / description / termes de recherche back-end, générés en une seule fois",
        "valide les limites strictes de caractères de chaque plateforme <span>— réécriture automatique en cas de dépassement</span>",
        "validation de conformité plateforme + score d'optimisation <span>— savoir avant la mise en ligne si c'est supprimé</span>",
        "16 langues <span>— couvrant les principaux marchés européens</span>",
    ], [
        (("Caractères titre", '<span class="v blue">187 / 200</span>', "Amazon EU"),
         ("Puces", '<span class="v">5 ✓</span>', "avec mots-clés"),
         ("Conformité plateforme", '<span class="v up">✅ ok</span>', "0 infraction"),
         ("Optimisation", '<span class="v up">92 / 100</span>', "couverture sémantique 8/8")),
    ]),
    ("p3", "🌍", "Matrice multi-plateformes :<br>une saisie, 12 plateformes localisées en masse", [
        "Amazon EU + US / eBay / Allegro / Otto / Cdiscount / eMAG / TikTok Shop / Fruugo / Walmart / Kaufland / Zalando / bol.com",
        "langue adaptée automatiquement par plateforme <span>— Allegro→polonais, Otto→allemand, Cdiscount→français</span>",
        "l'échec d'une plateforme ne bloque pas les autres, compté plateforme par plateforme",
        "<b>No Shopify required</b> <span>— espace de travail autonome, inscription et démarrage immédiat</span>",
    ], [
        (("Allegro 🇵🇱", '<span class="v blue">pl</span>', "limite stricte 75 car."),
         ("Otto 🇩🇪", '<span class="v blue">de</span>', "exclusif allemand"),
         ("eMAG 🇷🇴", '<span class="v blue">ro</span>', "150 car."),
         ("Fruugo 🇪🇺", '<span class="v blue">en</span>', "catalogue paneuropéen")),
    ]),
    ("p4", "💬", "Service client IA :<br>répond aux messages acheteurs 7×24 automatiquement", [
        "classification de l'intention <span>— livraison / retours / réclamations / pré-vente</span>",
        "détection du sentiment, les négatifs à risque suggèrent le transfert à un agent humain",
        "extrait automatiquement les numéros de commande des requêtes livraison",
        "coût du service de €2000+/mois <span>jusqu'au prix d'un café</span>",
    ], [
        (("Message acheteur", '<span class="v">"Where is my order?"</span>', "EN"),
         ("Intention", '<span class="v blue">requête livraison</span>', "conf. 0.95"),
         ("N° commande", '<span class="v">#402-188</span>', "✓"),
         ("Sentiment", '<span class="v up">calme</span>', "pas de transfert")),
    ]),
    ("p5", "📣", "Textes publicitaires :<br>générés en une fois, selon les limites par plateforme", [
        "Facebook / Google / TikTok, trois plateformes adaptées",
        "texte principal, titre, description, CTA, hashtags tout inclus",
        "validation stricte des caractères <span>— jamais tronqué par la plateforme</span>",
        "campagnes externes, sans retravailler sans cesse le format des textes",
    ], [
        (("Facebook", '<span class="v">texte principal 118</span>', "limite 125 ✓"),
         ("Google", '<span class="v">titre 28</span>', "limite 30 ✓"),
         ("TikTok", '<span class="v">texte + 5 tags</span>', "limite 100 ✓")),
    ]),
]

_FBLOCKS_I18N = {"en": _FBLOCKS_EN, "de": _FBLOCKS_DE, "fr": _FBLOCKS_FR}


def _fblocks(lang: str = "zh"):
    return _FBLOCKS if lang == "zh" else _FBLOCKS_I18N[lang]

_FAQS = [
    ("体检需要注册吗？", "不需要。打开页面直接填产品信息即可体检，游客每天可免费查 3 次。注册免费账号后可保存体检历史、继续用文案生成等功能。"),
    ("GPSR 是什么？什么时候开始强制？", "EU 2023/988《通用产品安全法规》，2024 年 12 月 13 日起适用。要求在线销售的产品展示欧盟责任人信息、当地语言安全信息，CE 类目须有 CE 标识。缺失可被平台下架。"),
    ("体检真的免费吗？会消耗生成额度吗？", "免费，且不消耗任何生成额度。体检给出完整风险报告；可粘贴的合规块需 Starter 及以上套餐解锁。"),
    ("我需要绑定我的店铺吗？", "不需要。CrossAIO 是独立工作台，No Shopify required——这是我们和 Marqetir 等绑店型工具的核心区别。"),
    ("输入 ASIN 会自动抓取我的 listing 吗？", "目前不会。ASIN 仅用于记录关联，判定基于你填写的标题与关键词。我们不抓取、不存储你的 Amazon 后台数据。"),
    ("报告能替代合规咨询吗？", "不能。报告是工程辅助建议，帮助你快速定位缺口；最终合规判定请以欧盟官方文本与认证机构意见为准。"),
]

_FAQS_I18N = {
    "en": [
        ("Do I need an account to run a check?", "No. Open the page, enter your product info and check away — guests get 3 free checks per day. With a free account you can save your check history and use copy generation and more."),
        ("What is GPSR and when does it become mandatory?", "EU 2023/988, the General Product Safety Regulation, applies since 13 December 2024. Products sold online must display the EU Responsible Person's information and safety information in the local language; CE categories need CE marking. Missing items can lead to delisting."),
        ("Is the check really free? Does it use generation credits?", "Free, and it consumes no generation credits. The check produces a full risk report; paste-ready compliance blocks require Starter or above."),
        ("Do I need to connect my store?", "No. CrossAIO is a standalone workbench, No Shopify required — the key difference from store-connected tools like Marqetir."),
        ("Does entering an ASIN auto-scrape my listing?", "Not at this time. The ASIN is a linked record only; the check is based on the title and keywords you enter. We don't scrape or store your Amazon backend data."),
        ("Can the report replace compliance consulting?", "No. It helps you quickly identify the gaps; final compliance decisions rest on official EU texts and accredited bodies."),
    ],
    "de": [
        ("Brauche ich ein Konto für den Check?", "Nein. Seite öffnen, Produktdaten eingeben und direkt prüfen — Gäste erhalten 3 kostenlose Prüfungen pro Tag. Mit einem kostenlosen Konto kannst du deine Prüfhistorie speichern und u. a. Textgenerierung nutzen."),
        ("Was ist die GPSR und ab wann ist sie Pflicht?", "EU 2023/988, die allgemeine Produktsicherheitsverordnung, gilt seit dem 13. Dezember 2024. Online verkaufte Produkte müssen Angaben zum EU-Verantwortlichen und Sicherheitsinformationen in der Landessprache anzeigen; CE-Kategorien benötigen die CE-Kennzeichnung. Fehlende Angaben können zum De-Listing führen."),
        ("Ist der Check wirklich kostenlos? Verbraucht er Generierungskontingent?", "Kostenlos, und er verbraucht kein Generierungskontingent. Der Check erstellt einen vollständigen Risikobericht; einfügbare Compliance-Blöcke erfordern den Tarif Starter oder höher."),
        ("Muss ich meinen Shop anbinden?", "Nein. CrossAIO ist eine eigenständige Workbench, No Shopify required — das ist der Kernunterschied zu Shop-bindenden Tools wie Marqetir."),
        ("Übernimmt die Eingabe einer ASIN automatisch mein Listing?", "Derzeit nicht. Die ASIN dient nur als Verknüpfungsdatensatz; die Prüfung basiert auf Titel und Keywords, die du eingibst. Wir erfassen und speichern keine Amazon-Backend-Daten."),
        ("Kann der Bericht eine Compliance-Beratung ersetzen?", "Nein. Er hilft dir, Lücken schnell zu erkennen; maßgeblich für die finale Beurteilung sind offizielle EU-Texte und zugelassene Stellen."),
    ],
    "fr": [
        ("Faut-il un compte pour effectuer une vérification ?", "Non. Ouvrez la page, saisissez les informations sur votre produit et lancez la vérification — les visiteurs ont droit à 3 vérifications gratuites par jour. Avec un compte gratuit, vous pouvez enregistrer l'historique et utiliser la génération de textes, etc."),
        ("Qu'est-ce que le GPSR et quand devient-il obligatoire ?", "L'EU 2023/988, le règlement sur la sécurité générale des produits, est applicable depuis le 13 décembre 2024. Les produits vendus en ligne doivent afficher les informations du représentant UE et les informations de sécurité dans la langue locale ; les catégories CE nécessitent le marquage CE. Des éléments manquants peuvent entraîner le déréférencement."),
        ("La vérification est-elle vraiment gratuite ? Consomme-t-elle des crédits de génération ?", "Gratuite, et elle ne consomme aucun crédit de génération. La vérification fournit un rapport de risque complet ; les blocs de conformité prêts à coller nécessitent le forfait Starter ou supérieur."),
        ("Dois-je connecter ma boutique ?", "Non. CrossAIO est un espace de travail autonome, No Shopify required — c'est la différence clé avec des outils liés à la boutique comme Marqetir."),
        ("Saisir un ASIN récupère-t-il automatiquement mon listing ?", "Pas pour le moment. L'ASIN n'est qu'un simple enregistrement de liaison ; la vérification s'appuie sur le titre et les mots-clés saisis. Nous ne récupérons ni ne stockons vos données Amazon."),
        ("Le rapport peut-il remplacer un conseil en conformité ?", "Non. Il vous aide à identifier rapidement les écarts ; la décision finale relève des textes officiels de l'UE et des organismes agréés."),
    ],
}


def _faqs(lang: str = "zh"):
    return _FAQS if lang == "zh" else _FAQS_I18N[lang]


def _stats_band(items) -> str:
    cells = "".join(f'<div class="stat"><div class="n">{_esc(n)}</div><div class="l">{_esc(l)}</div></div>'
                    for n, l in items)
    return f'<section style="padding-top:8px"><div class="stats">{cells}</div></section>'


def _faq_block(faqs) -> str:
    cells = "".join(f'<details><summary>{_esc(q)}</summary><div class="a">{_esc(a)}</div></details>'
                    for q, a in faqs)
    return f'<div class="faq" style="max-width:880px;margin:0 auto">{cells}</div>'


_CTA_SUB = {
    "zh": "免费注册即用 · 无需信用卡 · 无需绑定店铺 · No Shopify required",
    "en": "sign up free and start instantly · no credit card required · no store connection required · No Shopify required",
    "de": "kostenlos registrieren und sofort loslegen · keine Kreditkarte nötig · keine Shop-Anbindung nötig · No Shopify required",
    "fr": "inscription gratuite, démarrage immédiat · sans carte bancaire · sans connexion de boutique · No Shopify required",
}
_CTA_GHOST = {"zh": "免费注册", "en": "Sign up free", "de": "Kostenlos registrieren", "fr": "Inscription gratuite"}


def _cta_band(title: str, primary_href: str, primary_label: str, lang: str = "zh") -> str:
    return f"""
<div class="cta-band">
  <h2>{title}</h2>
  <p>{_CTA_SUB[lang]}</p>
  <a href="{primary_href}"><button class="pill-blue">{primary_label} →</button></a>
  <a href="{_lp('/signup', lang)}" style="margin-left:10px"><button class="pill-ghost">{_CTA_GHOST[lang]}</button></a>
</div>"""


# ---------------------------------------------------------------------------
# 六个分页（zh 分支为历史原文逐字保留；en/de/fr 为译文）
# ---------------------------------------------------------------------------

def _home(lang: str = "zh") -> str:
    if lang != "zh":
        return _home_t(lang)
    cards = """
<div class="guides">
  <div class="gcard">
    <div class="thumb" style="background:linear-gradient(150deg,#eff6ff,#dbeafe)">🛡️</div>
    <div class="gbody"><h3>GPSR 合规自查手册</h3><p>EU 2023/988 已强制执行。哪些产品要 CE、要哪些语言的警示语，一篇讲清。</p><a href="#check">免费体检 30 秒自查 →</a></div>
  </div>
  <div class="gcard">
    <div class="thumb" style="background:linear-gradient(150deg,#f5f3ff,#ede9fe)">🌍</div>
    <div class="gbody"><h3>12 平台入驻与本地化指南</h3><p>Allegro 要波兰语、Otto 要德语——每平台的标题字数、语言与规则速查。</p><a href="/gpsr-check/platforms">查看平台覆盖 →</a></div>
  </div>
  <div class="gcard">
    <div class="thumb" style="background:linear-gradient(150deg,#f0fdf4,#dcfce7)">🤖</div>
    <div class="gbody"><h3>AI 文案与客服使用手册</h3><p>产品描述、五点描述、搜索词、买家消息自动回复、三平台广告文案一次生成。</p><a href="/gpsr-check/features">看功能拆解 →</a></div>
  </div>
</div>"""
    body = f"""
<div class="topbar">🎓 免费 GPSR 自查手册已上线 — 缺一项合规就下架 <a href="#check">→ 立即免费体检</a></div>
{_AIACT_BANNER}

<div class="hero-wrap">
  <div class="orbits">
    <div class="orbit o1"><div class="spin"><i></i></div></div>
    <div class="orbit o2"><div class="spin"><i></i></div></div>
    <div class="orbit o3"><div class="spin"><i></i></div></div>
  </div>
  <div class="hero">
    <div>
      <div class="eyebrow">🤖 CrossAIO · 欧洲合规引擎</div>
      <h1>一个 AI 助手，帮你的<br>欧洲生意<em>合规增长。</em></h1>
      <p class="sub">像运营专员一样盯着你的 listing：自动体检 GPSR 合规、指出下架风险、生成修复文案——7×24 不休息。</p>
      <div class="cta-row">
        <a href="/signup"><button class="pill-blue">免费注册</button></a>
        <a href="/gpsr-check/features"><button class="pill-ghost">了解更多</button></a>
      </div>
      <p class="tiny">✓ 体检<b>免注册</b>直接查 &nbsp;·&nbsp; ✓ <b>No Shopify required</b> &nbsp;·&nbsp; ✓ 覆盖 13 大平台（欧洲 12 + 美国站）</p>
    </div>
    <div class="chat">
      <div class="head"><span class="cdot">🤖</span><b>CrossAIO</b><span class="win">▢ ⋮ ✕</span></div>
      <div class="cbody">
        <div class="greet"><b>👋 Hi！</b></div>
        <div class="hint-q">你可以让我做这些：</div>
        <div class="chips">
          <div class="chip" onclick="location.href='#check'">🛡️ 体检我的玩具 listing</div>
          <div class="chip" onclick="location.href='#check'">🔍 找出缺德语警示语的产品</div>
          <div class="chip" onclick="location.href='/gpsr-check/features'">📈 一次生成 12 个平台的 listing</div>
        </div>
        <div id="chatMsgs"></div>
      </div>
      <div class="foot"><span>🛡️ 合规</span><span>📦 Listing</span><span>🌍 12 平台</span></div>
    </div>
  </div>
</div>

{cards}

<section id="check">
  <div class="sec-head">
    <div class="sec-eyebrow">免费 · 免注册 · 无需信用卡 · 不消耗额度</div>
    <h2 class="sec-title">30 秒 GPSR 合规体检</h2>
    <p class="sec-sub">输入产品，立即获得风险等级、适用指令与法定检查清单。无需注册登录，直接查。</p>
  </div>
  <div class="panel">
    <label>Amazon ASIN（可选，10 位）</label><input id="g_asin" placeholder="B0C1234XYZ" maxlength="10" style="text-transform:uppercase">
    <label>产品标题 *</label><input id="g_name" placeholder="例如：Kids Building Blocks Toy">
    <label>核心关键词（逗号分隔）*</label><input id="g_kw" placeholder="例如：toy, puzzle, kids">
    <label>主要平台</label>
    <select id="g_platform">
      <option value="amazon">Amazon 欧洲站 + 美国站</option><option value="ebay">eBay</option>
      <option value="cdiscount">Cdiscount（法国）</option><option value="otto">Otto（德国）</option>
      <option value="allegro">Allegro（波兰）</option><option value="emag">eMAG（罗马尼亚）</option>
      <option value="tiktok">TikTok Shop（欧美）</option><option value="walmart">Walmart（美国）</option>
      <option value="fruugo">Fruugo（泛欧）</option><option value="kaufland">Kaufland（德/中东欧）</option>
      <option value="zalando">Zalando（欧洲时尚）</option><option value="bol">bol.com（荷/比）</option>
    </select>
    <button class="pill-blue" id="btnGo" style="width:100%;margin-top:22px">开始免费体检 →</button>
    <div class="hint" style="text-align:center;margin-top:10px">游客每天可免费体检 3 次 · 注册账号可保存历史并解锁合规块</div>
    <div id="out"></div>
  </div>
</section>

<section style="padding-top:8px">
  <div class="danger-band">
    <h2>🚨 GPSR 不合规的真实代价</h2>
    <ul>
      <li>缺欧代 / 缺当地语言警示语 → 平台直接屏蔽搜索、失购物车、强制下架</li>
      <li>2025 年 Safety Gate 超过 4000 条警报，27 国协同执法，CE 类目是重灾区</li>
      <li>2024–2025 约 15%–20% 中小卖家因合规门槛退出欧洲市场</li>
      <li>用 AI 客服却未做 Art.50 身份告知 → 最高罚 €1500 万或全球营收 3%</li>
    </ul>
  </div>
</section>

{_stats_band([("9", "欧洲主流平台覆盖"), ("7", "CE 类目规则库"), ("7", "当地语言警示语内置"), ("16", "listing 生成语言")])}

<section style="padding-top:8px">
  <div class="tier">
    <p>💰 体检只报问题。修复交给 AI —— Starter €29/月解锁可粘贴合规块</p>
    <a href="/gpsr-check/pricing">看定价 →</a>
  </div>
</section>

<section style="padding-top:8px">
  <div class="sec-head">
    <div class="sec-eyebrow">常见问题</div>
    <h2 class="sec-title">FAQ 精选</h2>
  </div>
  {_faq_block(_FAQS[:3])}
  <p style="text-align:center;margin-top:18px"><a href="/gpsr-check/faq" style="color:var(--blue);font-weight:700">查看全部 6 条 FAQ →</a></p>
</section>
"""
    html = _shell("home", "免费 GPSR 合规体检 — 你的欧洲 listing 会被下架吗？| CrossAIO",
                  "EU 2023/988 GPSR 已强制执行。30 秒检查你的产品是否缺欧盟责任人（欧代）、当地语言安全警示语、CE 标识——缺一项平台就会下架。免注册、免费、无需信用卡、无需绑定店铺。",
                  body, lang)
    return html.replace("</body>", f"<script>{_HOME_JS}</script>\n</body>")


_HOME_T = {
    "en": dict(
        topbar="🎓 The free GPSR self-check guide is live — one compliance gap can get you delisted <a href=\"#check\">→ start your free check now</a>",
        eyebrow="🤖 CrossAIO · the European compliance engine",
        h1='One AI assistant to grow your<br>European business <em>compliantly.</em>',
        sub="Works like a dedicated operations specialist watching your listing: auto GPSR compliance checks, flags delisting risks, generates fix copy — around the clock, 7×24.",
        cta1="Sign up free", cta2="Learn more",
        tiny='✓ check <b>no sign-up</b> · ✓ <b>No Shopify required</b> · ✓ covers 12 platforms (12 European + US)',
        greet="👋 Hi!", hintq="You can ask me to:",
        chip1="🛡️ check my toy listing", chip2="🔍 find products missing German warnings", chip3="📈 generate listings for 12 platforms at once",
        foot1="🛡️ Compliance", foot2="📦 Listing", foot3="🌍 12 platforms",
        c1h="GPSR self-check guide",
        c1p="EU 2023/988 is in force. Which products need CE, which languages need warnings — explained in one guide.",
        c1a="free check · 30-second self-check →",
        c2h="12-platform marketplace entry & localization guide",
        c2p="Allegro needs Polish, Otto needs German — per-platform title limits, languages and rules reference.",
        c2a="see platform coverage →",
        c3h="AI copy & service handbook",
        c3p="Product description, bullet points, search terms, auto-replies to buyers, three-platform ad copy, all generated at once.",
        c3a="features explained →",
        cheek="free · no sign-up · no credit card · no credits consumed",
        ctitle="30-second GPSR compliance check",
        csub="enter your product to instantly get the risk level, applicable directives and the legal checklist. No account needed — check right away.",
        l_asin="Amazon ASIN (optional, 10 chars)",
        l_name="Product title *", ph_name="e.g. Kids Building Blocks Toy",
        l_kw="Key keywords (comma-separated) *", ph_kw="e.g. toy, puzzle, kids",
        l_plat="Main platform",
        opt_amazon="Amazon EU + US marketplace", opt_ebay="eBay",
        opt_cdiscount="Cdiscount (France)", opt_otto="Otto (Germany)",
        opt_allegro="Allegro (Poland)", opt_emag="eMAG (Romania)",
        opt_tiktok="TikTok Shop (UK/US/EU)", opt_walmart="Walmart (US)",
        opt_fruugo="Fruugo (pan-EU)", opt_kaufland="Kaufland (DE/CE Europe)",
        opt_zalando="Zalando (European fashion)", opt_bol="bol.com (NL/BE)",
        btn="Start your free check →",
        hint="guests can run 3 free checks per day · create an account to save history and unlock compliance blocks",
        dh="🚨 The real cost of non-compliance",
        dl1="missing EU Rep / missing local-language warnings → platform suppresses from search, lose the Buy Box, forced delisting",
        dl2="in 2025 the Safety Gate issued over 4000 alerts, coordinated enforcement across 27 countries, CE categories are the heavily affected category",
        dl3="2024–2025 about 15%–20% of small and mid-size sellers left the European market due to compliance barriers",
        dl4="using AI customer service without Art.50 disclosure → fined up to €15 million or 3% of global revenue",
        stats=[("9", "major European platforms covered"), ("7", "CE category rule sets"), ("7", "local-language warnings built in"), ("16", "listing generation languages")],
        tier="💰 the check only reports issues. Let AI fix it — Starter €29/month unlocks paste-ready compliance blocks",
        tier_a="see full pricing →",
        feyebrow="FAQ", ftitle="FAQ highlights",
        faq_a="see all 6 FAQs →",
        title="Free GPSR compliance check — will your European listing get delisted? | CrossAIO",
        meta="EU 2023/988 GPSR is in force. Check in 30 seconds whether your product is missing the EU Responsible Person (EU Rep), local-language safety warnings, or CE marking — one missing item and the platform delists. No sign-up, free, no credit card, no store connection."),
    "de": dict(
        topbar="🎓 Die kostenlose GPSR-Selbstcheck-Anleitung ist verfügbar — eine Compliance-Lücke kann zum De-Listing führen <a href=\"#check\">→ kostenlosen Check jetzt starten</a>",
        eyebrow="🤖 CrossAIO · die europäische Compliance-Engine",
        h1="Ein KI-Assistent für dein<br>europäisches Geschäft — <em>konformes Wachstum.</em>",
        sub="Arbeitet wie ein eigener Operations-Experte, der dein Listing überwacht: automatischer GPSR-Compliance-Check, Hinweis auf De-Listing-Risiken, Generierung von Fix-Texten — rund um die Uhr, 7×24.",
        cta1="Kostenlos registrieren", cta2="Mehr erfahren",
        tiny='✓ Check <b>ohne Registrierung</b> · ✓ <b>No Shopify required</b> · ✓ deckt 12 Plattformen ab (12 europäische + US)',
        greet="👋 Hi!", hintq="Du kannst mich Folgendes fragen:",
        chip1="🛡️ mein Spielzeug-Listing prüfen", chip2="🔍 Produkte ohne deutsche Hinweise finden", chip3="📈 Listings für 12 Plattformen auf einmal generieren",
        foot1="🛡️ Compliance", foot2="📦 Listing", foot3="🌍 12 Plattformen",
        c1h="GPSR-Selbstcheck-Anleitung",
        c1p="EU 2023/988 ist in Kraft. Welche Produkte CE brauchen, welche Sprachen Hinweise benötigen — alles in einer Anleitung erklärt.",
        c1a="kostenloser Check · 30-Sekunden-Selbstcheck →",
        c2h="13-Plattformen-Marktplatz-Einstieg & Lokalisierungs-Guide",
        c2p="Allegro braucht Polnisch, Otto braucht Deutsch — je Plattform Titel-Limits, Sprachen und Regelübersicht.",
        c2a="Plattform-Abdeckung ansehen →",
        c3h="KI-Text- und Service-Handbuch",
        c3p="Produktbeschreibung, Bulletpoints, Suchbegriffe, automatische Antworten auf Käufernachrichten, Anzeigen für 3 Plattformen auf einmal.",
        c3a="Funktionen im Detail →",
        cheek="kostenlos · ohne Registrierung · keine Kreditkarte · ohne Kontingentverbrauch",
        ctitle="30-Sekunden-GPSR-Compliance-Check",
        csub="Produkt eingeben und sofort Risikostufe, anwendbare Richtlinien und gesetzliche Checkliste erhalten. Ohne Konto — sofort prüfen.",
        l_asin="Amazon ASIN (optional, 10 Zeichen)",
        l_name="Produkttitel *", ph_name="z. B. Kids Building Blocks Toy",
        l_kw="Schlüssel-Keywords (durch Komma getrennt) *", ph_kw="z. B. toy, puzzle, kids",
        l_plat="Hauptplattform",
        opt_amazon="Amazon-Marktplatz Europa + USA", opt_ebay="eBay",
        opt_cdiscount="Cdiscount (Frankreich)", opt_otto="Otto (Deutschland)",
        opt_allegro="Allegro (Polen)", opt_emag="eMAG (Rumänien)",
        opt_tiktok="TikTok Shop (UK/US/EU)", opt_walmart="Walmart (USA)",
        opt_fruugo="Fruugo (paneuropäisch)", opt_kaufland="Kaufland (DE/Mittelosteuropa)",
        opt_zalando="Zalando (europäische Mode)", opt_bol="bol.com (NL/BE)",
        btn="Kostenlosen Check starten →",
        hint="Gäste können 3 kostenlose Prüfungen pro Tag durchführen · Konto erstellen, um Historie zu speichern und Compliance-Blöcke freizuschalten",
        dh="🚨 Der reale Preis der Nicht-Konformität",
        dl1="fehlender EU-Verantwortlicher / fehlende Landessprachen-Hinweise → aus der Suche entfernt, Buy-Box-Verlust, erzwungenes De-Listing",
        dl2="2025 meldete das Safety Gate über 4000 Warnungen, koordinierte Durchsetzung in 27 Ländern, CE-Kategorien sind die besonders betroffene Kategorie",
        dl3="2024–2025 verlassen etwa 15%–20% der kleinen und mittleren Verkäufer den europäischen Markt aufgrund der Compliance-Hürden",
        dl4="KI-Kundenservice ohne Art.50-Offenlegung → Bußgeld bis zu €15 Mio. oder 3 % des weltweiten Umsatzes",
        stats=[("9", "abgedeckte europäische Hauptplattformen"), ("7", "CE-Kategorie-Regelwerke"), ("7", "Hinweise in Landessprache integriert"), ("16", "Listing-Sprachen")],
        tier="💰 Der Check meldet nur Probleme. Lass die KI es fixen — Starter €29/Monat schaltet einfügbare Compliance-Blöcke frei",
        tier_a="alle Preise ansehen →",
        feyebrow="FAQ", ftitle="FAQ-Auswahl",
        faq_a="alle 6 FAQs ansehen →",
        title="Kostenloser GPSR-Compliance-Check — wird dein europäisches Listing gelöscht? | CrossAIO",
        meta="EU 2023/988 GPSR ist in Kraft. Prüfe in 30 Sekunden, ob dein Produkt den EU-Verantwortlichen (EU-Rep), Sicherheitshinweise in der Landessprache oder die CE-Kennzeichnung vermissen — ein fehlender Punkt und die Plattform löscht das Listing. Ohne Registrierung, kostenlos, keine Kreditkarte, keine Shop-Anbindung."),
    "fr": dict(
        topbar="🎓 Le guide d'auto-vérification GPSR gratuit est en ligne — un écart de conformité peut entraîner le déréférencement <a href=\"#check\">→ lancer la vérification gratuite dès maintenant</a>",
        eyebrow="🤖 CrossAIO — le moteur de conformité européen",
        h1="Un assistant IA pour votre<br>activité européenne — <em>croître en restant conforme.</em>",
        sub="Il agit comme un spécialiste des opérations dédié qui surveille votre listing : vérification GPSR automatique, signalement des risques de déréférencement, génération de textes correctifs — 24h/24 et 7j/7.",
        cta1="Inscription gratuite", cta2="En savoir plus",
        tiny='✓ vérif <b>sans inscription</b> · ✓ <b>No Shopify required</b> · ✓ couvre 12 plateformes (12 européennes + US)',
        greet="👋 Bonjour !", hintq="Vous pouvez me demander :",
        chip1="🛡️ vérifier mon listing de jouets", chip2="🔍 trouver les produits sans avertissements allemands", chip3="📈 générer des listings pour 12 plateformes d'un coup",
        foot1="🛡️ Conformité", foot2="📦 Listing", foot3="🌍 12 plateformes",
        c1h="Guide d'auto-vérification GPSR",
        c1p="L'EU 2023/988 est en vigueur. Quels produits doivent porter le CE, quelles langues nécessitent des avertissements — tout expliqué en un guide.",
        c1a="vérif gratuite · auto-vérification en 30 secondes →",
        c2h="Guide d'entrée sur 12 plateformes et de localisation",
        c2p="Allegro exige le polonais, Otto exige l'allemand — limites de titre, langues et règles par plateforme.",
        c2a="voir la couverture des plateformes →",
        c3h="Manuel d'utilisation IA (textes et service client)",
        c3p="Description produit, puces, mots-clés, réponses automatiques aux acheteurs, textes publicitaires 3 plateformes, générés en une fois.",
        c3a="les fonctionnalités en détail →",
        cheek="gratuit · sans inscription · sans carte bancaire · sans consommation de crédits",
        ctitle="Vérification GPSR en 30 secondes",
        csub="saisissez votre produit pour obtenir instantanément le niveau de risque, les directives applicables et la liste de contrôle légale. Sans compte — lancez la vérification immédiatement.",
        l_asin="Amazon ASIN (facultatif, 10 caractères)",
        l_name="Titre du produit *", ph_name="p. ex. Kids Building Blocks Toy",
        l_kw="Mots-clés clés (séparés par des virgules) *", ph_kw="p. ex. toy, puzzle, kids",
        l_plat="Plateforme principale",
        opt_amazon="marketplace Amazon Europe + États-Unis", opt_ebay="eBay",
        opt_cdiscount="Cdiscount (France)", opt_otto="Otto (Allemagne)",
        opt_allegro="Allegro (Pologne)", opt_emag="eMAG (Roumanie)",
        opt_tiktok="TikTok Shop (RU/US/UE)", opt_walmart="Walmart (US)",
        opt_fruugo="Fruugo (paneuropéen)", opt_kaufland="Kaufland (DE/Europe centrale)",
        opt_zalando="Zalando (mode européenne)", opt_bol="bol.com (NL/BE)",
        btn="Lancer la vérification gratuite →",
        hint="les visiteurs peuvent effectuer 3 vérifications gratuites par jour · créez un compte pour enregistrer l'historique et débloquer les blocs de conformité",
        dh="🚨 Le vrai coût de la non-conformité",
        dl1="représentant UE manquant / avertissements en langue locale manquants → suppression des résultats de recherche, perte de la Buy Box, déréférencement forcé",
        dl2="en 2025 le Safety Gate a publié plus de 4000 alertes, application coordonnée dans 27 pays, les catégories CE sont la catégorie la plus touchée",
        dl3="2024–2025 environ 15%–20% des vendeurs petits et moyens quittent le marché européen en raison des barrières de conformité",
        dl4="utiliser un service client IA sans divulgation Art.50 → amende jusqu'à 15 M€ ou 3 % du chiffre d'affaires mondial",
        stats=[("9", "principales plateformes européennes couvertes"), ("7", "ensembles de règles CE"), ("7", "avertissements en langue locale intégrés"), ("16", "langues de génération des listings")],
        tier="💰 la vérification signale seulement les problèmes. Confiez les correctifs à l'IA — Starter €29/mois débloque les blocs de conformité prêts à coller",
        tier_a="voir tous les tarifs →",
        feyebrow="FAQ", ftitle="Extraits de la FAQ",
        faq_a="voir les 6 FAQ →",
        title="Vérification GPSR gratuite — votre listing européen sera-t-il déréférencé ? | CrossAIO",
        meta="L'EU 2023/988 GPSR est en vigueur. Vérifiez en 30 secondes si votre produit manque du représentant UE (EU Rep), des avertissements de sécurité en langue locale ou du marquage CE — un élément manqué et la plateforme déréférence. Sans inscription, gratuit, sans carte bancaire, sans connexion de boutique."),
}


def _home_t(lang: str) -> str:
    t = _HOME_T[lang]
    P = lambda p: _lp(p, lang)
    cards = f"""
<div class="guides">
  <div class="gcard">
    <div class="thumb" style="background:linear-gradient(150deg,#eff6ff,#dbeafe)">🛡️</div>
    <div class="gbody"><h3>{t["c1h"]}</h3><p>{t["c1p"]}</p><a href="#check">{t["c1a"]}</a></div>
  </div>
  <div class="gcard">
    <div class="thumb" style="background:linear-gradient(150deg,#f5f3ff,#ede9fe)">🌍</div>
    <div class="gbody"><h3>{t["c2h"]}</h3><p>{t["c2p"]}</p><a href="{P('/gpsr-check/platforms')}">{t["c2a"]}</a></div>
  </div>
  <div class="gcard">
    <div class="thumb" style="background:linear-gradient(150deg,#f0fdf4,#dcfce7)">🤖</div>
    <div class="gbody"><h3>{t["c3h"]}</h3><p>{t["c3p"]}</p><a href="{P('/gpsr-check/features')}">{t["c3a"]}</a></div>
  </div>
</div>"""
    body = f"""
<div class="topbar">{t["topbar"]}</div>
{_aiact_banner(lang)}

<div class="hero-wrap">
  <div class="orbits">
    <div class="orbit o1"><div class="spin"><i></i></div></div>
    <div class="orbit o2"><div class="spin"><i></i></div></div>
    <div class="orbit o3"><div class="spin"><i></i></div></div>
  </div>
  <div class="hero-grid"></div>
  <div class="hero-glow"><i class="g1"></i><i class="g2"></i></div>
  <div class="particles"><i style="left:8%;top:70%"></i><i style="left:16%;top:40%"></i><i style="left:24%;top:82%"></i><i style="left:33%;top:55%"></i><i style="left:42%;top:30%"></i><i style="left:50%;top:75%"></i><i style="left:58%;top:45%"></i><i style="left:66%;top:85%"></i><i style="left:74%;top:35%"></i></div>
  <div class="hero">
    <div>
      <div class="eyebrow">{t["eyebrow"]}</div>
      <h1>{t["h1"]}</h1>
      <p class="sub">{t["sub"]}</p>
      <div class="cta-row">
        <a href="{P('/signup')}"><button class="pill-blue">{t["cta1"]}</button></a>
        <a href="{P('/gpsr-check/features')}"><button class="pill-ghost">{t["cta2"]}</button></a>
      </div>
      <p class="tiny">{t["tiny"]}</p>
    </div>
    <div class="chat">
      <div class="head"><span class="cdot">🤖</span><b>CrossAIO</b><span class="win">▢ ⋮ ✕</span></div>
      <div class="cbody">
        <div class="greet"><b>{t["greet"]}</b></div>
        <div class="hint-q">{t["hintq"]}</div>
        <div class="chips">
          <div class="chip" onclick="location.href='#check'">{t["chip1"]}</div>
          <div class="chip" onclick="location.href='#check'">{t["chip2"]}</div>
          <div class="chip" onclick="location.href='{P('/gpsr-check/features')}'">{t["chip3"]}</div>
        </div>
        <div id="chatMsgs"></div>
      </div>
      <div class="foot"><span>{t["foot1"]}</span><span>{t["foot2"]}</span><span>{t["foot3"]}</span></div>
    </div>
  </div>
</div>

{cards}

<section id="check">
  <div class="sec-head">
    <div class="sec-eyebrow">{t["cheek"]}</div>
    <h2 class="sec-title">{t["ctitle"]}</h2>
    <p class="sec-sub">{t["csub"]}</p>
  </div>
  <div class="panel">
    <label>{t["l_asin"]}</label><input id="g_asin" placeholder="B0C1234XYZ" maxlength="10" style="text-transform:uppercase">
    <label>{t["l_name"]}</label><input id="g_name" placeholder="{t["ph_name"]}">
    <label>{t["l_kw"]}</label><input id="g_kw" placeholder="{t["ph_kw"]}">
    <label>{t["l_plat"]}</label>
    <select id="g_platform">
      <option value="amazon">{t["opt_amazon"]}</option><option value="ebay">{t["opt_ebay"]}</option>
      <option value="cdiscount">{t["opt_cdiscount"]}</option><option value="otto">{t["opt_otto"]}</option>
      <option value="allegro">{t["opt_allegro"]}</option><option value="emag">{t["opt_emag"]}</option>
      <option value="tiktok">{t["opt_tiktok"]}</option><option value="walmart">{t["opt_walmart"]}</option>
      <option value="fruugo">{t["opt_fruugo"]}</option><option value="kaufland">{t["opt_kaufland"]}</option>
      <option value="zalando">{t["opt_zalando"]}</option><option value="bol">{t["opt_bol"]}</option>
    </select>
    <button class="pill-blue" id="btnGo" style="width:100%;margin-top:22px">{t["btn"]}</button>
    <div class="hint" style="text-align:center;margin-top:10px">{t["hint"]}</div>
    <div id="out"></div>
  </div>
</section>

<section style="padding-top:8px">
  <div class="danger-band">
    <h2>{t["dh"]}</h2>
    <ul>
      <li>{t["dl1"]}</li>
      <li>{t["dl2"]}</li>
      <li>{t["dl3"]}</li>
      <li>{t["dl4"]}</li>
    </ul>
  </div>
</section>

{_stats_band([(n, l) for n, l in t["stats"]])}

<section style="padding-top:8px">
  <div class="tier">
    <p>{t["tier"]}</p>
    <a href="{P('/gpsr-check/pricing')}">{t["tier_a"]}</a>
  </div>
</section>

<section style="padding-top:8px">
  <div class="sec-head">
    <div class="sec-eyebrow">{t["feyebrow"]}</div>
    <h2 class="sec-title">{t["ftitle"]}</h2>
  </div>
  {_faq_block(_faqs(lang)[:3])}
  <p style="text-align:center;margin-top:18px"><a href="{P('/gpsr-check/faq')}" style="color:var(--blue);font-weight:700">{t["faq_a"]}</a></p>
</section>
"""
    html = _shell("home", t["title"], t["meta"], body, lang)
    return html.replace("</body>", f"<script>{_home_js(lang)}</script>\n</body>")


_FEAT_T = {
    "zh": dict(
        eyebrow="✦ GPSR 体检中心 · 功能拆解", h1="五大能力，逐个看透",
        sub="从合规体检到多语言文案，一站式 AI 运营工具 —— 每个板块都对着一个竞品空位。",
        oeyebrow="产品总览", otitle="体检报告长这样",
        whyebrow="工作原理", whytitle="三步开始",
        block_label="板块", cta_block="免费体验 →",
        flow=[("免费体检", "输入产品 30 秒出风险报告，免注册"),
              ("AI 修复", "生成可粘贴合规块 + 当地语言警示语"),
              ("12 平台同步", "多平台矩阵批量落地，字数自动校验")],
        stats=[("5", "能力板块"), ("7", "CE 类目规则库"), ("146", "多语言安全词库"), ("16", "生成语言")],
        cta_title="⚙️ 现在就体验完整体检中心", cta_label="回到体检主页",
        title="功能拆解 — 五大能力逐个看透 | GPSR 体检中心 | CrossAIO",
        meta="GPSR 合规引擎 / 产品描述生成 / 欧洲多平台矩阵 / AI 客服 / 广告文案 —— 五大能力逐个拆解，每个板块都对着一个竞品空位。"),
    "en": dict(
        eyebrow="✦ GPSR Check Center · features explained", h1="Five core capabilities, one by one",
        sub="From compliance check to multilingual copy, an all-in-one AI operations tool — each block fills a competitor gap.",
        oeyebrow="Product overview", otitle="Here's what a check report looks like",
        whyebrow="How it works", whytitle="Start in three steps",
        block_label="Block", cta_block="Try for free →",
        flow=[("Free check", "enter your product, get a risk report in 30 s, no sign-up"),
              ("AI fix", "generates paste-ready compliance blocks + local-language warnings"),
              ("12-platform sync", "multi-platform matrix at scale, auto character validation")],
        stats=[("5", "capability blocks"), ("7", "CE category rule sets"), ("146", "multilingual safety lexicon"), ("16", "languages generated")],
        cta_title="⚙️ Try the full Check Center now", cta_label="Back to the check home",
        title="Features explained — five core capabilities | GPSR Check Center | CrossAIO",
        meta="GPSR compliance engine / product description generator / European multi-platform matrix / AI customer service / ad copy — five capabilities, each block filling a competitor gap."),
    "de": dict(
        eyebrow="✦ GPSR-Check-Center · Funktionen im Detail", h1="Fünf Kernfunktionen im Detail",
        sub="Vom Compliance-Check bis zu mehrsprachigen Texten — ein KI-Operations-Tool für alles, jeder Block schließt eine Marktlücke der Konkurrenz.",
        oeyebrow="Produktübersicht", otitle="So sieht ein Prüfbericht aus",
        whyebrow="So funktioni's", whytitle="In drei Schritten starten",
        block_label="Block", cta_block="Kostenlos testen →",
        flow=[("Kostenloser Check", "Produkt eingeben, Risikobericht in 30 s, ohne Registrierung"),
              ("KI-Fix", "erstellt einfügbare Compliance-Blöcke + Landessprachen-Hinweise"),
              ("13-Plattformen-Sync", "Multi-Plattform-Matrix im Stapel, automatische Zeichenprüfung")],
        stats=[("5", "Kernblöcke"), ("7", "CE-Kategorie-Regelwerke"), ("146", "mehrsprachiger Sicherheits-Wortschatz"), ("16", "Generierungssprachen")],
        cta_title="⚙️ Das ganze Check-Center jetzt testen", cta_label="Zurück zur Check-Startseite",
        title="Funktionen im Detail — fünf Kernfunktionen | GPSR-Check-Center | CrossAIO",
        meta="GPSR-Compliance-Engine / Produktbeschreibungs-Generator / europäische Multi-Plattform-Matrix / KI-Kundenservice / Anzeigentexte — fünf Kernfunktionen, jeder Block schließt eine Konkurrenz-Lücke."),
    "fr": dict(
        eyebrow="✦ Centre de vérification GPSR · les fonctionnalités en détail", h1="Cinq fonctionnalités clés, en détail",
        sub="De la vérification de conformité aux textes multilingues, un outil IA d'opération tout-en-un — chaque bloc comble un vide chez la concurrence.",
        oeyebrow="Aperçu du produit", otitle="Voici à quoi ressemble un rapport de vérification",
        whyebrow="Comment ça marche", whytitle="Commencez en trois étapes",
        block_label="Bloc", cta_block="Essayer gratuitement →",
        flow=[("Vérification gratuite", "saisissez le produit, rapport de risque en 30 s, sans inscription"),
              ("Correctif IA", "génère des blocs de conformité prêts à coller + avertissements locaux"),
              ("Synchro 12 plateformes", "matrice multi-plateformes en masse, validation auto des caractères")],
        stats=[("5", "blocs de fonctionnalités"), ("7", "ensembles de règles CE"), ("146", "lexique multilingue de sécurité"), ("16", "langues de génération")],
        cta_title="⚙️ Essayez tout le centre de vérification maintenant", cta_label="Retour à l'accueil de la vérification",
        title="Les fonctionnalités en détail — cinq fonctionnalités clés | Centre de vérification GPSR | CrossAIO",
        meta="Moteur de conformité GPSR / générateur de descriptions produit / matrice multi-plateformes européenne / service client IA / textes publicitaires — cinq fonctionnalités, chaque bloc comble un vide de la concurrence."),
}


def _features(lang: str = "zh") -> str:
    t = _FEAT_T[lang]
    P = lambda p: _lp(p, lang)
    blocks = []
    for pid, icon, h3, lis, fvisuals in _fblocks(lang):
        li_html = "".join(f"<li>{x}</li>" for x in lis)
        fv = "".join(
            '<div class="fcard"><div><div class="k">' + k + '</div>' + v + '</div><span>' + tag + '</span></div>'
            for k, v, tag in fvisuals[0])
        blocks.append(f"""
<div class="fblock" id="{pid}">
  <div>
    <div class="sec-eyebrow">{icon} {t["block_label"]} {pid[1]} / 5</div>
    <h3>{h3}</h3>
    <ul>{li_html}</ul>
    <a class="pill-blue" style="display:inline-block;text-decoration:none" href="{P('/gpsr-check#check')}">{t["cta_block"]}</a>
  </div>
  <div class="fvisual">{fv}</div>
</div>""")
    body = f"""
<div class="hero-solo">
  <div class="eyebrow">{t["eyebrow"]}</div>
  <h1>{t["h1"]}</h1>
  <p class="sub">{t["sub"]}</p>
</div>

<section style="padding-top:26px">
  <div class="sec-head">
    <div class="sec-eyebrow">{t["oeyebrow"]}</div>
    <h2 class="sec-title">{t["otitle"]}</h2>
  </div>
  {_MOCKUPS["gpsr"](lang=lang)}
</section>

{"".join(blocks)}

<section style="padding-top:8px">
  <div class="sec-head">
    <div class="sec-eyebrow">{t["whyebrow"]}</div>
    <h2 class="sec-title">{t["whytitle"]}</h2>
  </div>
  {_flow_svg(t["flow"], lang)}
</section>

{_stats_band([(n, l) for n, l in t["stats"]])}

{_cta_band(t["cta_title"], P('/gpsr-check#check'), t["cta_label"], lang)}
"""
    return _shell("features", t["title"], t["meta"], body, lang)


_PLAT_T = {
    "zh": dict(
        eyebrow="✦ GPSR 体检中心 · 覆盖平台", h1="13 大平台，规则全部内置",
        sub="每个平台的标题字数、语言、合规规则按卖家中心文档持续维护 —— 悬停下方滚动墙可暂停。",
        note="* 平台标识为品牌色风格化字标（说明用途），商标权利归属各平台所有者；上线时替换为官方授权素材。",
        tier="📋 每个平台的字数 / 语言 / GPSR 要点，免费速查表随时翻", tier_a="打开规则速查表 →",
        cta_title="🌍 你的平台也在里面", cta_label="体检我的平台",
        title="13 大平台覆盖 — 规则全部内置 | GPSR 体检中心 | CrossAIO",
        meta="Amazon 欧洲站+美国站、eBay、Allegro、Otto、Cdiscount、eMAG、TikTok Shop、Fruugo、Walmart、Kaufland、Zalando、bol.com —— 12 平台字数/语言/GPSR 规则全部内置。"),
    "en": dict(
        eyebrow="✦ GPSR Check Center · platforms covered", h1="12 platforms, rules all built in",
        sub="Each platform's title limits, languages and compliance rules are continuously maintained per the seller central documentation — hovering pauses the scrolling wall.",
        note="* Platform marks are stylized brand-color wordmarks (illustrative); trademarks belong to their respective owners; replace with officially licensed assets at launch.",
        tier="📋 Per-platform character limits / languages / GPSR essentials, free rules reference on demand", tier_a="open the rules reference →",
        cta_title="🌍 Your platform is in there too", cta_label="Check my platform",
        title="12-platform coverage — rules all built in | GPSR Check Center | CrossAIO",
        meta="Amazon EU+US, eBay, Allegro, Otto, Cdiscount, eMAG, TikTok Shop, Fruugo, Walmart, Kaufland, Zalando, bol.com — 12 platforms, character limits / languages / GPSR rules all built in."),
    "de": dict(
        eyebrow="✦ GPSR-Check-Center · abgedeckte Plattformen", h1="12 Plattformen, Regeln alle integriert",
        sub="Titel-Limits, Sprachen und Compliance-Regeln jeder Plattform werden laut Seller-Center-Dokumentation laufend gepflegt — beim Überfahren pausiert die Laufleiste.",
        note="* Plattform-Zeichen sind stilisierte Wortmarken in Markenfarben (Illustrationszweck); Markenrechte liegen bei den jeweiligen Inhabern; bei Launch durch offiziell lizenzierte Assets ersetzen.",
        tier="📋 Zeichenlimits / Sprachen / GPSR-Punkte je Plattform, kostenlose Regelübersicht zum Nachschlagen", tier_a="Regelübersicht öffnen →",
        cta_title="🌍 Deine Plattform ist auch dabei", cta_label="Meine Plattform prüfen",
        title="13-Plattformen-Abdeckung — Regeln alle integriert | GPSR-Check-Center | CrossAIO",
        meta="Amazon Europa+USA, eBay, Allegro, Otto, Cdiscount, eMAG, TikTok Shop, Fruugo, Walmart, Kaufland, Zalando, bol.com — 12 Plattformen, Zeichenlimits / Sprachen / GPSR-Regeln alle integriert."),
    "fr": dict(
        eyebrow="✦ Centre de vérification GPSR · plateformes couvertes", h1="12 plateformes, règles toutes intégrées",
        sub="Les limites de titres, langues et règles de conformité de chaque plateforme sont mises à jour en continu selon la documentation Seller Central — la bande défilante se met en pause au survol.",
        note="* Les marques de plateformes sont des wordmarks stylisés aux couleurs de marque (illustratifs) ; les marques appartiennent à leurs propriétaires respectifs ; à remplacer par des contenus sous licence officielle au lancement.",
        tier="📋 Limites de caractères / langues / points GPSR par plateforme, référentiel de règles gratuit à consulter", tier_a="ouvrir le référentiel de règles →",
        cta_title="🌍 Votre plateforme y est aussi", cta_label="Vérifier ma plateforme",
        title="Couverture 12 plateformes — règles toutes intégrées | Centre de vérification GPSR | CrossAIO",
        meta="Amazon Europe+US, eBay, Allegro, Otto, Cdiscount, eMAG, TikTok Shop, Fruugo, Walmart, Kaufland, Zalando, bol.com — 12 plateformes, limites de caractères / langues / règles GPSR toutes intégrées."),
}


def _platforms(lang: str = "zh") -> str:
    t = _PLAT_T[lang]
    P = lambda p: _lp(p, lang)
    cards = []
    meta_map = _PLATFORM_META_I18N.get(lang)
    for i, (key, (mark, name, meta)) in enumerate(_PLATFORM_MARKS.items()):
        if meta_map and key in meta_map:
            name, meta = meta_map[key]
        cards.append(
            f'<div class="site" style="animation-delay:{min(i * 0.06, 0.6):.2f}s">'
            f'<span class="mark">{mark}</span>'
            f'<span class="meta"><b>{_esc(name)}</b>{_esc(meta)}</span></div>')
    body = f"""
<div class="hero-solo">
  <div class="eyebrow">{t["eyebrow"]}</div>
  <h1>{t["h1"]}</h1>
  <p class="sub">{t["sub"]}</p>
</div>

<section style="padding-top:26px">
  {_platform_marquee(lang=lang)}
</section>

<section style="padding-top:8px">
  <div class="sites">{"".join(cards)}</div>
  <p class="mark-note">{t["note"]}</p>
</section>

<section style="padding-top:8px">
  <div class="tier">
    <p>{t["tier"]}</p>
    <a href="{P('/rules')}">{t["tier_a"]}</a>
  </div>
</section>

{_cta_band(t["cta_title"], P('/gpsr-check#check'), t["cta_label"], lang)}
"""
    return _shell("platforms", t["title"], t["meta"], body, lang)


_COMP_T = {
    "zh": dict(
        eyebrow="✦ GPSR 体检中心 · 竞品对比", h1="不绑店，不烧钱，直击合规",
        sub="与绑店型工具（如 Marqetir）逐项对比 —— 体验路径、成本、合规能力、平台覆盖。",
        col_cmp="绑店型工具（如 Marqetir）", col_cross="CrossAIO",
        rows=[
            ("开始使用", "必须先绑定 Shopify/Woo 商店", "No Shopify required — 打开即用"),
            ("先体验后付费", "注册绑店才能看功能", "免注册先体检，满意再注册"),
            ("起订成本", "€159+/月", "免费体检 + €29/月起"),
            ("GPSR 合规", "不管合规", "合规块内嵌每份 listing"),
            ("平台覆盖", "欧洲平台 12+", "12 平台（欧洲 12 + Amazon US，含 Kaufland/Zalando/bol）"),
            ("语义搜索适配", "无", "Rufus/iZi 问答覆盖度评分"),
        ],
        stats=[("€0", "体检成本（免注册）"), ("€29", "月起解锁合规块"), ("€159+", "绑店型工具月费"), ("€500+", "一次合规咨询报价")],
        cta_title="⚖️ 先免注册体检，满意再注册", cta_label="免费体检",
        title="竞品对比 — 不绑店，不烧钱，直击合规 | GPSR 体检中心 | CrossAIO",
        meta="CrossAIO 与绑店型工具逐项对比：无需绑定店铺、免注册先体检、€29/月起、GPSR 合规块内嵌、12 平台覆盖、语义搜索适配评分。"),
    "en": dict(
        eyebrow="✦ GPSR Check Center · comparison", h1="No store, no waste, straight to compliance",
        sub="Head-to-head with store-connected tools (e.g. Marqetir) — onboarding, cost, compliance, platform coverage.",
        col_cmp="Store-connected tools (e.g. Marqetir)", col_cross="CrossAIO",
        rows=[
            ("Getting started", "must connect a Shopify/Woo store first", "No Shopify required — open and use"),
            ("Try before you pay", "sign up and connect a store to see features", "check first with no sign-up, register if happy"),
            ("Starting price", "€159+/month", "free check + from €29/month"),
            ("GPSR compliance", "ignores compliance", "compliance blocks embedded in every listing"),
            ("Platform coverage", "12+ European platforms", "12 platforms (12 European + Amazon US, incl. Kaufland/Zalando/bol)"),
            ("Semantic search readiness", "none", "Rufus/iZi Q&A coverage score"),
        ],
        stats=[("€0", "check cost (no sign-up)"), ("€29", "/month to unlock compliance blocks"), ("€159+", "store-connected tool monthly fee"), ("€500+", "one compliance consulting quote")],
        cta_title="⚖️ Check first with no sign-up, register if happy", cta_label="Free check",
        title="Comparison — no store, no waste, straight to compliance | GPSR Check Center | CrossAIO",
        meta="CrossAIO vs store-connected tools: no store connection, check first with no sign-up, from €29/month, GPSR compliance blocks embedded, 12 platforms, semantic search readiness score."),
    "de": dict(
        eyebrow="✦ GPSR-Check-Center · Vergleich", h1="Kein Shop, keine Kosten, direkt zur Konformität",
        sub="Direktvergleich mit Shop-bindenden Tools (z. B. Marqetir) — Einstieg, Kosten, Konformität, Plattform-Abdeckung.",
        col_cmp="Shop-bindende Tools (z. B. Marqetir)", col_cross="CrossAIO",
        rows=[
            ("Einstieg", "muss zuerst einen Shopify-/Woo-Shop anbinden", "No Shopify required — sofort nutzbar"),
            ("Erst testen, dann zahlen", "Registrierung + Shop-Anbindung nötig, um Funktionen zu sehen", "zuerst ohne Registrierung prüfen, bei Gefallen registrieren"),
            ("Einstiegspreis", "€159+/Monat", "kostenloser Check + ab €29/Monat"),
            ("GPSR-Konformität", "kümmert sich nicht um Konformität", "Compliance-Blöcke in jedem Listing eingebettet"),
            ("Plattform-Abdeckung", "12+ europäische Plattformen", "12 Plattformen (12 europäische + Amazon US, inkl. Kaufland/Zalando/bol)"),
            ("Semantische Suchanpassung", "keine", "Rufus/iZi-Q&A-Abdeckungs-Score"),
        ],
        stats=[("€0", "Check-Kosten (ohne Registrierung)"), ("€29", "/Monat für Compliance-Blöcke"), ("€159+", "Monatstarif shop-bindender Tools"), ("€500+", "ein Compliance-Beratungsangebot")],
        cta_title="⚖️ Zuerst ohne Registrierung prüfen, bei Gefallen registrieren", cta_label="Kostenloser Check",
        title="Vergleich — kein Shop, keine Kosten, direkt zur Konformität | GPSR-Check-Center | CrossAIO",
        meta="CrossAIO im Vergleich mit shop-bindenden Tools: keine Shop-Anbindung, erst ohne Registrierung prüfen, ab €29/Monat, GPSR-Compliance-Blöcke integriert, 12 Plattformen, semantische Suchanpassung."),
    "fr": dict(
        eyebrow="✦ Centre de vérification GPSR · comparaison", h1="Sans boutique, sans dépense, droit à la conformité",
        sub="Comparaison directe avec les outils liés à la boutique (ex. Marqetir) — parcours, coût, conformité, couverture des plateformes.",
        col_cmp="Outils liés à la boutique (ex. Marqetir)", col_cross="CrossAIO",
        rows=[
            ("Pour commencer", "doit d'abord connecter une boutique Shopify/Woo", "No Shopify required — ouvrez et utilisez"),
            ("Essayer avant de payer", "inscription + connexion boutique pour voir les fonctionnalités", "vérifiez d'abord sans inscription, inscrivez-vous si satisfait"),
            ("Prix de départ", "€159+/mois", "vérification gratuite + dès €29/mois"),
            ("Conformité GPSR", "ignore la conformité", "blocs de conformité intégrés à chaque listing"),
            ("Couverture plateformes", "12+ plateformes européennes", "12 plateformes (12 européennes + Amazon US, dont Kaufland/Zalando/bol)"),
            ("Compatibilité recherche sémantique", "aucune", "score de couverture Q&R Rufus/iZi"),
        ],
        stats=[("€0", "coût de la vérification (sans inscription)"), ("€29", "/mois pour débloquer les blocs"), ("€159+", "tarif mensuel des outils liés à la boutique"), ("€500+", "un tarif d'un conseil en conformité")],
        cta_title="⚖️ Vérifiez d'abord sans inscription, inscrivez-vous si satisfait", cta_label="Vérification gratuite",
        title="Comparaison — sans boutique, sans dépense, droit à la conformité | Centre de vérification GPSR | CrossAIO",
        meta="CrossAIO comparé aux outils liés à la boutique : sans connexion de boutique, vérif d'abord sans inscription, dès €29/mois, blocs de conformité GPSR intégrés, 12 plateformes, compatibilité recherche sémantique."),
}


def _compare(lang: str = "zh") -> str:
    t = _COMP_T[lang]
    P = lambda p: _lp(p, lang)
    rows_html = "".join(
        f'<tr><td><b>{_esc(a)}</b></td><td class="nowin">{b}</td><td class="win">{c}</td></tr>'
        for a, b, c in t["rows"])
    body = f"""
<div class="hero-solo">
  <div class="eyebrow">{t["eyebrow"]}</div>
  <h1>{t["h1"]}</h1>
  <p class="sub">{t["sub"]}</p>
</div>

<section class="compare" style="padding-top:30px">
  <table>
    <tr><th></th><th>{t["col_cmp"]}</th><th style="color:var(--ok)">{t["col_cross"]}</th></tr>
    {rows_html}
  </table>
</section>

{_stats_band([(n, l) for n, l in t["stats"]])}

{_cta_band(t["cta_title"], P('/gpsr-check#check'), t["cta_label"], lang)}
"""
    return _shell("compare", t["title"], t["meta"], body, lang)


_PRIC_T = {
    "zh": dict(
        eyebrow="✦ GPSR 体检中心 · 定价", h1="体检只报问题。修复交给 AI。",
        sub="升级后自动生成可直接粘贴进 listing 的 GPSR 合规块：当地语言警示语 + 欧代标注 + 产品标识，一次生成多平台适配。",
        card_h="Starter 解锁全部修复能力", card_price="€29", card_small="/月起",
        card_p="对比：合规咨询报价 €500+ / 一次下架损失远超一年订阅",
        card_btn="免费注册开始 →",
        free_h="🆓 免费体检", free_pp="€0",
        free_li=["免注册，每 IP 每天 3 次", "风险等级 + 适用指令 + 法定检查清单",
                 "12 平台规则判定（CE 类目识别）", "不消耗任何生成额度"],
        free_no=["可粘贴合规块（欧代 / 警示语 / 标识）", "体检历史保存"],
        hot_h="⭐ Starter 及以上", hot_pp="€29/月起",
        hot_li=["免费档全部能力", "GPSR 合规块：当地语言警示语 + 欧代 + 产品标识",
                "欧代台账联动 —— 自动内嵌真实欧代", "技术文件清单（8 项 / 10 年存档指引）",
                "体检历史 + 修复文案生成", "Listing 监控每日风险日报"],
        tier="📊 想看完整四档定价（含 Pro / Business 能力对照）？", tier_a="查看完整定价 →",
        stats=[("€500+", "一次合规咨询报价"), ("€29", "月起的 AI 修复"), ("3 次/天", "免费体检额度"), ("10 年", "技术文件存档时限")],
        cta_title="💰 体检免费，修复一步到位", cta_label="先做免费体检",
        title="定价 — 体检免费，修复交给 AI | GPSR 体检中心 | CrossAIO",
        meta="GPSR 免费体检每 IP 每天 3 次；Starter €29/月起解锁可粘贴合规块（当地语言警示语 + 欧代标注 + 产品标识）、体检历史与技术文件清单。"),
    "en": dict(
        eyebrow="✦ GPSR Check Center · pricing", h1="The check only reports issues. Let AI fix it.",
        sub="Upgrade to auto-generate paste-ready GPSR compliance blocks for your listing: local-language warnings + EU Rep marking + product marking, adapted to multiple platforms in one pass.",
        card_h="Starter unlocks all fix capabilities", card_price="€29", card_small="/month",
        card_p="vs. €500+ per compliance consulting quote / a single delisting costs far more than a year's subscription",
        card_btn="Sign up free and start →",
        free_h="🆓 Free check", free_pp="€0",
        free_li=["no sign-up, 3 checks per IP per day", "risk level + applicable directives + legal checklist",
                 "12-platform rule validation (CE category detection)", "consumes no generation credits"],
        free_no=["paste-ready compliance blocks (EU Rep / warnings / marking)", "save check history"],
        hot_h="⭐ Starter and above", hot_pp="from €29/month",
        hot_li=["everything in the free tier", "GPSR compliance blocks: local-language warnings + EU Rep + product marking",
                "EU Rep registry sync — automatically embeds the real EU Rep", "technical file checklist (8 items / 10-year retention guidance)",
                "check history + fix copy generation", "Listing monitoring daily risk report"],
        tier="📊 Want to see all four pricing tiers (incl. Pro / Business comparison)?", tier_a="see full pricing →",
        stats=[("€500+", "one compliance consulting quote"), ("€29", "/month for AI fixes"), ("3/day", "free check quota"), ("10 years", "technical file retention period")],
        cta_title="💰 Free check, fixes in one step", cta_label="Run the free check first",
        title="Pricing — check free, fixes by AI | GPSR Check Center | CrossAIO",
        meta="Free GPSR check: 3 per IP per day; Starter from €29/month unlocks paste-ready compliance blocks (local-language warnings + EU Rep marking + product marking), check history and technical file checklist."),
    "de": dict(
        eyebrow="✦ GPSR-Check-Center · Preise", h1="Der Check meldet nur Probleme. Lass die KI es fixen.",
        sub="Upgrade und erhalte automatisch einfügbare GPSR-Compliance-Blöcke für dein Listing: Hinweise in Landessprache + EU-Verantwortlicher-Kennzeichnung + Produktkennzeichnung, in einem Durchgang für mehrere Plattformen angepasst.",
        card_h="Starter schaltet alle Fix-Funktionen frei", card_price="€29", card_small="/Monat",
        card_p="im Vergleich: €500+ für eine Compliance-Beratung / ein einziges De-Listing kostet mehr als ein Jahres-Abo",
        card_btn="Kostenlos registrieren und starten →",
        free_h="🆓 Kostenloser Check", free_pp="€0",
        free_li=["ohne Registrierung, 3 Prüfungen pro IP und Tag", "Risikostufe + anwendbare Richtlinien + gesetzliche Checkliste",
                 "13-Plattformen-Regelprüfung (CE-Kategorie-Erkennung)", "verbraucht kein Generierungskontingent"],
        free_no=["einfügbare Compliance-Blöcke (EU-Verantw. / Hinweise / Kennzeichnung)", "Prüfhistorie speichern"],
        hot_h="⭐ Starter und höher", hot_pp="ab €29/Monat",
        hot_li=["alle Funktionen des kostenlosen Tarifs", "GPSR-Compliance-Blöcke: Landessprachen-Hinweise + EU-Verantw. + Produktkennzeichnung",
                "Verknüpfung mit EU-Verantwortlichen-Register — bindet den echten EU-Verantwortlichen automatisch ein", "Checkliste technischer Unterlagen (8 Punkte / 10 Jahre Aufbewahrungshinweise)",
                "Prüfhistorie + Fix-Text-Generierung", "täglicher Listing-Monitoring-Risikobericht"],
        tier="📊 Alle vier Preistarife (inkl. Pro / Business-Vergleich) ansehen?", tier_a="alle Preise ansehen →",
        stats=[("€500+", "ein Compliance-Beratungsangebot"), ("€29", "/Monat für KI-Fixes"), ("3/Tag", "kostenloses Prüfkontingent"), ("10 Jahre", "Aufbewahrungsfrist techn. Unterlagen")],
        cta_title="💰 Check kostenlos, Fixes in einem Schritt", cta_label="Zuerst kostenlos prüfen",
        title="Preise — Check kostenlos, Fixes von der KI | GPSR-Check-Center | CrossAIO",
        meta="Kostenloser GPSR-Check: 3 pro IP und Tag; Starter ab €29/Monat schaltet einfügbare Compliance-Blöcke (Hinweise in Landessprache + EU-Verantwortlicher-Kennzeichnung + Produktkennzeichnung), Prüfhistorie und Checkliste technischer Unterlagen frei."),
    "fr": dict(
        eyebrow="✦ Centre de vérification GPSR · tarifs", h1="La vérification signale les problèmes. Confiez les correctifs à l'IA.",
        sub="Passez à un forfait supérieur pour générer automatiquement des blocs de conformité GPSR prêts à coller dans votre listing : avertissements en langue locale + marquage du représentant UE + marquage du produit, adaptés à plusieurs plateformes en une fois.",
        card_h="Starter débloque toutes les capacités de correction", card_price="€29", card_small="/mois",
        card_p="à comparer : 500 €+ pour un conseil en conformité / un seul déréférencement coûte bien plus qu'un an d'abonnement",
        card_btn="Inscription gratuite, démarrage →",
        free_h="🆓 Vérification gratuite", free_pp="€0",
        free_li=["sans inscription, 3 vérifications par IP et par jour", "niveau de risque + directives applicables + liste de contrôle légale",
                 "validation des règles sur 12 plateformes (détection catégories CE)", "ne consomme aucun crédit de génération"],
        free_no=["blocs de conformité prêts à coller (représentant UE / avertissements / marquage)", "enregistrer l'historique des vérifications"],
        hot_h="⭐ Starter et supérieur", hot_pp="dès €29/mois",
        hot_li=["toutes les fonctionnalités de l'offre gratuite", "blocs de conformité GPSR : avertissements locaux + représentant UE + marquage du produit",
                "synchronisation du registre des représentants UE — intègre automatiquement le vrai représentant UE", "liste de contrôle de la documentation technique (8 éléments / conservation 10 ans)",
                "historique des vérifications + génération de textes correctifs", "rapport de surveillance quotidien des listings"],
        tier="📊 Envie de voir les quatre formules de tarifs (incl. comparatif Pro / Business) ?", tier_a="voir tous les tarifs →",
        stats=[("€500+", "un tarif d'un conseil en conformité"), ("€29", "/mois pour les correctifs IA"), ("3/jour", "quota de vérifications gratuites"), ("10 ans", "durée de conservation des documents techniques")],
        cta_title="💰 Vérif gratuite, correctifs en une étape", cta_label="Lancez d'abord la vérification gratuite",
        title="Tarifs — vérif gratuite, correctifs par l'IA | Centre de vérification GPSR | CrossAIO",
        meta="Vérification GPSR gratuite : 3 par IP et par jour ; Starter dès €29/mois débloque les blocs de conformité prêts à coller (avertissements en langue locale + marquage représentant UE + marquage du produit), l'historique et la liste de contrôle technique."),
}


def _pricing(lang: str = "zh") -> str:
    t = _PRIC_T[lang]
    P = lambda p: _lp(p, lang)
    free_li = "".join(f"<li>{x}</li>" for x in t["free_li"])
    free_no = "".join(f'<li class="no">{x}</li>' for x in t["free_no"])
    hot_li = "".join(f"<li>{x}</li>" for x in t["hot_li"])
    body = f"""
{_aiact_banner(lang)}
<div class="hero-solo">
  <div class="eyebrow">{t["eyebrow"]}</div>
  <h1>{t["h1"]}</h1>
  <p class="sub">{t["sub"]}</p>
</div>

<section style="padding-top:26px">
  <div class="pricing-card">
    <h2>{t["card_h"]}</h2>
    <div class="price">{t["card_price"]}<small>{t["card_small"]}</small></div>
    <p>{t["card_p"]}</p>
    <a href="{P('/signup')}"><button class="pill-blue">{t["card_btn"]}</button></a>
  </div>
  <div class="ptiers">
    <div class="ptier">
      <h3>{t["free_h"]}</h3>
      <div class="pp">{t["free_pp"]}</div>
      <ul>
        {free_li}
        {free_no}
      </ul>
    </div>
    <div class="ptier hot">
      <h3>{t["hot_h"]}</h3>
      <div class="pp">{t["hot_pp"]}</div>
      <ul>
        {hot_li}
      </ul>
    </div>
  </div>
</section>

<section style="padding-top:26px">
  <div class="tier">
    <p>{t["tier"]}</p>
    <a href="{P('/pricing')}">{t["tier_a"]}</a>
  </div>
</section>

{_stats_band([(n, l) for n, l in t["stats"]])}

{_cta_band(t["cta_title"], P('/gpsr-check#check'), t["cta_label"], lang)}
"""
    return _shell("pricing", t["title"], t["meta"], body, lang)


_FAQ_T = {
    "zh": dict(
        eyebrow="✦ GPSR 体检中心 · 常见问题", h1="FAQ",
        sub="关于免费体检、GPSR 法规、数据隐私与合规边界的六个高频问题。",
        cta_title="❓ 还有疑问？直接体验最快", cta_label="免费体检 30 秒",
        title="FAQ — 常见问题 | GPSR 体检中心 | CrossAIO",
        meta="GPSR 体检是否需要注册、GPSR 法规何时强制、是否免费、是否需要绑定店铺、ASIN 数据隐私、报告是否替代合规咨询。"),
    "en": dict(
        eyebrow="✦ GPSR Check Center · FAQ", h1="FAQ",
        sub="Six frequently asked questions on the free check, GPSR rules, data privacy and compliance boundaries.",
        cta_title="❓ Still have questions? trying it is fastest", cta_label="Free 30-second check",
        title="FAQ — frequently asked questions | GPSR Check Center | CrossAIO",
        meta="Whether the GPSR check needs an account, when GPSR becomes mandatory, whether it's free, whether a store connection is needed, ASIN data privacy, and whether the report replaces compliance consulting."),
    "de": dict(
        eyebrow="✦ GPSR-Check-Center · FAQ", h1="FAQ",
        sub="Sechs häufige Fragen zum kostenlosen Check, zur GPSR, zum Datenschutz und zu Grenzen der Konformität.",
        cta_title="❓ Noch Fragen? Ausprobieren ist am schnellsten", cta_label="Kostenloser 30-Sekunden-Check",
        title="FAQ — häufige Fragen | GPSR-Check-Center | CrossAIO",
        meta="Ob der GPSR-Check ein Konto braucht, ab wann die GPSR Pflicht ist, ob sie kostenlos ist, ob eine Shop-Anbindung nötig ist, ASIN-Datenschutz und ob der Bericht eine Compliance-Beratung ersetzt."),
    "fr": dict(
        eyebrow="✦ Centre de vérification GPSR · FAQ", h1="FAQ",
        sub="Six questions fréquentes sur la vérification gratuite, le règlement GPSR, la confidentialité et les limites de la conformité.",
        cta_title="❓ Encore des questions ? Essayez, c'est le plus rapide", cta_label="Vérif gratuite 30 secondes",
        title="FAQ — questions fréquentes | Centre de vérification GPSR | CrossAIO",
        meta="Faut-il un compte pour la vérification GPSR, quand le GPSR devient obligatoire, est-ce gratuit, faut-il connecter une boutique, confidentialité des données ASIN, et le rapport remplace-t-il un conseil en conformité."),
}


def _faq(lang: str = "zh") -> str:
    t = _FAQ_T[lang]
    P = lambda p: _lp(p, lang)
    body = f"""
<div class="hero-solo">
  <div class="eyebrow">{t["eyebrow"]}</div>
  <h1>{t["h1"]}</h1>
  <p class="sub">{t["sub"]}</p>
</div>

<section style="padding-top:26px">
  {_faq_block(_faqs(lang))}
</section>

{_cta_band(t["cta_title"], P('/gpsr-check#check'), t["cta_label"], lang)}
"""
    return _shell("faq", t["title"], t["meta"], body, lang)


_PAGES = {"home": _home, "features": _features, "platforms": _platforms,
          "compare": _compare, "pricing": _pricing, "faq": _faq}

for _slug, _fn in _PAGES.items():
    def _make(fn=_fn, slug=_slug):
        def _handler():
            return HTMLResponse(fn("zh"))
        _handler.__name__ = f"gpsr_page_{slug}"
        return _handler

    if _slug == "home":
        router.get("/gpsr-check", include_in_schema=False)(_make())
    else:
        router.get(f"/gpsr-check/{_slug}", include_in_schema=False)(_make())

    for _lng in ("en", "de", "fr"):
        def _make_l(fn=_fn, slug=_slug, lng=_lng):
            def _handler():
                return HTMLResponse(fn(lng))
            _handler.__name__ = f"gpsr_page_{lng}_{slug}"
            return _handler

        if _slug == "home":
            router.get(f"/{_lng}/gpsr-check", include_in_schema=False)(_make_l())
        else:
            router.get(f"/{_lng}/gpsr-check/{_slug}", include_in_schema=False)(_make_l())


