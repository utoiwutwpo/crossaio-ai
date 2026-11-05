"""平台 GPSR 规则落地页（SEO）— /rules/{platform} 动态渲染。

单一数据源：app/experts/platform_rules.py（6 平台原生规则集）。
页面更新自动随数据同步，无需手工维护 6 份 HTML。
每页结构：Hero（政策名+监管机构）→ 违规后果红卡 → 平台特有规则 →
欧代要求 → 当地语言警示语样例（免费 1 条，其余付费解锁）→ 体检 CTA → 交叉链接。
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..config import settings
from ..experts import platform_rules
from ..experts.gpsr import CE_RULES
from .site_nav import NAV_CSS, site_nav

router = APIRouter()

_PLATFORM_DISPLAY = {
    "allegro": ("Allegro", "🇵🇱 波兰 / 捷克 / 斯洛伐克 · pl/cs/sk"),
    "emag": ("eMAG", "🇷🇴 罗马尼亚 / 匈牙利 / 保加利亚 · ro/hu/bg"),
    "cdiscount": ("Cdiscount", "🇫🇷 法国 · fr"),
    "otto": ("Otto", "🇩🇪 德国 · de"),
    "kaufland": ("Kaufland", "🇩🇪🇦🇹🇨🇿🇸🇰 德/奥/捷/斯 · de/cs/sk"),
    "bol": ("bol.com", "🇳🇱🇧🇪 荷兰 / 比利时 · nl"),
}

# 交叉链接卡片内嵌官方 logo；bol 无 logo，键缺失时只渲染文字
_X_LOGO = {
    "allegro": ("allegro.svg", "Allegro"),
    "emag": ("emag.svg", "eMAG"),
    "cdiscount": ("cdiscount.png", "Cdiscount"),
    "otto": ("otto.svg", "Otto"),
    "kaufland": ("kaufland.svg", "Kaufland"),
}


def _x_inner(platform: str, sub: str) -> str:
    """x-link 内部：[logo img] + [name + small sub]。bol 无 logo 时只输出文字块。"""
    name = _PLATFORM_DISPLAY[platform][0]
    logo = _X_LOGO.get(platform)
    img = (f'<img class="x-logo" src="/img/logos/{logo[0]}" alt="{logo[1]}" />'
           if logo else "")
    return f'{img}<span class="x-txt">{name}<small>{sub}</small></span>'

_LANG_NAME = {
    "en": "英语", "de": "德语", "fr": "法语", "es": "西语", "it": "意语",
    "pl": "波兰语", "ro": "罗马尼亚语", "nl": "荷兰语", "sv": "瑞典语",
    "cs": "捷克语", "sk": "斯洛伐克语", "hu": "匈牙利语", "bg": "保加利亚语",
}

# ---------------------------------------------------------------------------
# 规则页外壳视觉（en/de/fr/zh 共用）— 视觉蓝本 en/home.html
# 深色 page-head 科技层 + 玻璃内容卡 + gh-code 警示样例窗 + 页尾合规 CTA 带。
# 纯展示层；平台数据 / 文案 / 路由 / 切换器 / hreflang 一律不动。
# ---------------------------------------------------------------------------
_RULES_CSS = """
  :root{--navy:#0b1030;--ink:#0f172a;--muted:#64748b;--border:#e2e8f0;--bg:#fff;--soft:#f8fafc;
    --blue:#2563eb;--blue-light:#3b82f6;--blue-dark:#1d4ed8;--purple:#8b5cf6;--violet:#7c3aed;
    --ok:#059669;--err:#dc2626}
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:Inter,"Segoe UI","Microsoft YaHei",system-ui,sans-serif;background:var(--bg);color:var(--ink);line-height:1.75}
  a{text-decoration:none;color:inherit}

  /* dark page-head tech layer */
  .page-head{position:relative;overflow:hidden;
    background:
      radial-gradient(1100px 520px at 82% 18%,rgba(124,58,237,.45),transparent 62%),
      radial-gradient(820px 460px at 12% 100%,rgba(29,78,216,.38),transparent 55%),
      linear-gradient(115deg,#0a0f2e 0%,#141040 48%,#3b1a86 100%);
    padding:64px 24px 76px;text-align:center;color:#fff}
  .ph-grid{position:absolute;inset:0;pointer-events:none;opacity:.5;
    background-image:linear-gradient(rgba(255,255,255,.05) 1px,transparent 1px),
      linear-gradient(90deg,rgba(255,255,255,.05) 1px,transparent 1px);
    background-size:44px 44px;
    -webkit-mask-image:radial-gradient(ellipse 75% 70% at 50% 40%,#000 30%,transparent 78%);
    mask-image:radial-gradient(ellipse 75% 70% at 50% 40%,#000 30%,transparent 78%)}
  .ph-glow{position:absolute;inset:0;pointer-events:none}
  .ph-glow i{position:absolute;border-radius:50%;filter:blur(70px);opacity:.5;animation:glowpulse 9s ease-in-out infinite}
  .ph-glow i.g1{width:400px;height:400px;left:50%;top:-120px;background:radial-gradient(circle,rgba(139,92,246,.55),transparent 70%)}
  .ph-glow i.g2{width:340px;height:340px;right:-90px;bottom:-140px;background:radial-gradient(circle,rgba(59,130,246,.5),transparent 70%);animation-delay:3s}
  @keyframes glowpulse{0%,100%{opacity:.45}50%{opacity:.75}}
  .particles{position:absolute;inset:0;pointer-events:none}
  .particles i{position:absolute;width:5px;height:5px;border-radius:50%;background:#93c5fd;opacity:0;animation:ptw 7s linear infinite}
  .particles i:nth-child(2){width:4px;height:4px;background:#c4b5fd;animation-delay:1.1s;animation-duration:9s}
  .particles i:nth-child(3){width:6px;height:6px;background:#a5b4fc;animation-delay:2.2s;animation-duration:6s}
  .particles i:nth-child(4){width:4px;height:4px;background:#93c5fd;animation-delay:3.3s;animation-duration:8s}
  .particles i:nth-child(5){width:5px;height:5px;background:#c4b5fd;animation-delay:.6s;animation-duration:10s}
  .particles i:nth-child(6){width:3px;height:3px;background:#a5b4fc;animation-delay:1.8s;animation-duration:7s}
  .particles i:nth-child(7){width:5px;height:5px;background:#93c5fd;animation-delay:2.9s;animation-duration:9s}
  .particles i:nth-child(8){width:4px;height:4px;background:#c4b5fd;animation-delay:4s;animation-duration:6.5s}
  .particles i:nth-child(9){width:5px;height:5px;background:#a5b4fc;animation-delay:.9s;animation-duration:8.5s}
  .particles i:nth-child(10){width:3px;height:3px;background:#93c5fd;animation-delay:2.5s;animation-duration:11s}
  .particles i:nth-child(11){width:4px;height:4px;background:#c4b5fd;animation-delay:3.7s;animation-duration:7.5s}
  .particles i:nth-child(12){width:6px;height:6px;background:#a5b4fc;animation-delay:1.4s;animation-duration:9.5s}
  @keyframes ptw{0%{transform:translateY(0);opacity:0}8%{opacity:.85}85%{opacity:.5}100%{transform:translateY(-60vh);opacity:0}}
  .ph-inner{position:relative;z-index:2;max-width:880px;margin:0 auto}
  .ph-emblem{width:58px;height:58px;margin:0 auto 18px;filter:drop-shadow(0 10px 26px rgba(124,58,237,.55))}
  .page-head .eyebrow{display:inline-block;font-size:12.5px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#c4b5fd;margin-bottom:14px;background:rgba(139,92,246,.16);border:1px solid rgba(139,92,246,.35);padding:7px 16px;border-radius:999px;backdrop-filter:blur(6px)}
  .page-head h1{font-size:36px;font-weight:800;line-height:1.2;margin-bottom:12px;text-shadow:0 0 44px rgba(147,197,253,.35)}
  .page-head p{color:#c7d0e8;font-size:15px;max-width:680px;margin:0 auto 22px}
  .ph-badges{display:flex;gap:9px;justify-content:center;flex-wrap:wrap}
  .ph-badge{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.16);border-radius:999px;padding:6px 15px;font-size:12.5px;font-weight:700;color:#e2e8f0;backdrop-filter:blur(6px)}
  .ph-badge.ph-auth{background:rgba(139,92,246,.18);border-color:rgba(196,181,253,.45);color:#e9d5ff;box-shadow:0 0 22px rgba(139,92,246,.35)}

  section{max-width:900px;margin:0 auto;padding:44px 24px}
  h2.sec{font-size:19px;font-weight:800;margin:26px 0 14px}

  /* glass content cards */
  .card{background:rgba(255,255,255,.82);backdrop-filter:blur(10px);border:1px solid var(--border);border-radius:18px;padding:24px 26px;margin-bottom:16px;box-shadow:0 6px 24px rgba(15,23,42,.06);transition:.25s}
  .card:hover{transform:translateY(-4px);box-shadow:0 18px 42px rgba(37,99,235,.12);border-color:#bfdbfe}
  .card h3{font-size:15px;font-weight:800;margin-bottom:10px}
  .meta-row{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 14px}
  .badge{background:var(--soft);border:1px solid var(--border);border-radius:999px;padding:4px 13px;font-size:12.5px;font-weight:700;color:#334155}
  .card.danger{border-color:#fecaca;background:rgba(254,242,242,.85)}
  .card.danger h3{color:var(--err)}
  .card ul{margin:8px 0 0 20px}
  .card li{font-size:14px;color:#334155;padding:3px 0}
  .policy-link{display:inline-block;color:var(--blue);font-weight:700;font-size:13.5px;word-break:break-all}
  .policy-link:hover{color:var(--violet)}

  /* gh-code warning sample window */
  .gh-code{background:#0a0f2e;border:1px solid rgba(255,255,255,.1);border-radius:12px;overflow:hidden;font-family:ui-monospace,Consolas,monospace}
  .gh-code .bar{display:flex;align-items:center;gap:7px;padding:10px 14px;background:#131a3a;border-bottom:1px solid rgba(255,255,255,.08)}
  .gh-code .bar i{width:11px;height:11px;border-radius:50%;display:block}
  .gh-code .bar i:nth-child(1){background:#f87171}
  .gh-code .bar i:nth-child(2){background:#fbbf24}
  .gh-code .bar i:nth-child(3){background:#34d399}
  .gh-code .bar span{margin-left:8px;font-size:11.5px;color:#94a3b8}
  .gh-code .body{padding:16px 18px;color:#e2e8f0;font-size:13.5px;white-space:pre-wrap;overflow-x:auto}
  .lock{background:var(--soft);border:1px dashed var(--border);border-radius:12px;padding:16px 20px;font-size:13.5px;color:var(--muted);margin-top:14px}

  /* bottom compliance CTA band */
  .cta-band{position:relative;overflow:hidden;border-radius:22px;padding:48px 36px;text-align:center;color:#fff;margin:26px 0;
    background:
      radial-gradient(900px 420px at 85% 15%,rgba(124,58,237,.42),transparent 60%),
      linear-gradient(115deg,#0a0f2e,#251a5e 55%,#3b1a86)}
  .cta-band::before{content:"";position:absolute;inset:0;pointer-events:none;
    background-image:linear-gradient(rgba(255,255,255,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.05) 1px,transparent 1px);
    background-size:40px 40px}
  .cta-band .cta-inner{position:relative;z-index:2}
  .cta-band h2{font-size:26px;font-weight:800;margin-bottom:10px}
  .cta-band p{color:#c7d0e8;font-size:14px;margin-bottom:22px}
  .cta-row{display:flex;gap:12px;justify-content:center;flex-wrap:wrap}
  .pill-blue{background:linear-gradient(90deg,var(--blue-light),var(--violet));color:#fff;border-radius:999px;padding:13px 30px;font-size:15px;font-weight:700;border:none;display:inline-block;cursor:pointer;box-shadow:0 12px 32px rgba(124,58,237,.5);transition:.2s;position:relative;overflow:hidden}
  .pill-blue:hover{transform:translateY(-2px);box-shadow:0 16px 40px rgba(124,58,237,.6)}
  .pill-blue::after{content:"";position:absolute;top:0;left:-100%;width:100%;height:100%;background:linear-gradient(90deg,transparent,rgba(255,255,255,.22),transparent);animation:shine 3.2s ease-in-out infinite}
  @keyframes shine{0%{left:-100%}55%,100%{left:100%}}
  .pill-ghost{background:rgba(255,255,255,.06);color:#fff;border:1.5px solid rgba(255,255,255,.5);border-radius:999px;padding:12px 26px;font-size:15px;font-weight:600;display:inline-block;cursor:pointer;transition:.2s;backdrop-filter:blur(6px)}
  .pill-ghost:hover{border-color:#fff;background:rgba(255,255,255,.12);transform:translateY(-2px)}
  .cta-note{margin-top:16px;font-size:13.5px;color:#c7d0e8}
  .cta-note a{color:#fff;font-weight:700;text-decoration:underline;text-underline-offset:3px}
  .cta-note a:hover{color:#c4b5fd}

  .x-links{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
  .x-link{background:rgba(255,255,255,.82);backdrop-filter:blur(10px);border:1px solid var(--border);border-radius:14px;padding:15px 18px;font-weight:800;font-size:14.5px;transition:.25s;display:flex;align-items:center;gap:12px}
  .x-link .x-logo{height:16px;width:auto;object-fit:contain;flex:0 0 auto;display:block}
  .x-link .x-txt{display:flex;flex-direction:column;line-height:1.3}
  .x-link small{font-weight:600;color:var(--muted);font-size:12px;margin-top:2px}
  .x-link:hover{transform:translateY(-3px);border-color:#bfdbfe;box-shadow:0 14px 32px rgba(37,99,235,.12)}

  footer{border-top:1px solid var(--border);background:var(--soft);padding:28px 24px;text-align:center;font-size:13px;color:var(--muted)}
  footer a:hover{color:var(--blue)}
  @media(max-width:640px){.x-links{grid-template-columns:1fr}}
  @media (prefers-reduced-motion: reduce){.particles i,.ph-glow i,.pill-blue::after{animation:none}}
"""

_PARTICLES = (
    '<div class="particles">'
    '<i style="left:8%;top:70%"></i><i style="left:16%;top:40%"></i>'
    '<i style="left:24%;top:82%"></i><i style="left:33%;top:55%"></i>'
    '<i style="left:42%;top:30%"></i><i style="left:50%;top:75%"></i>'
    '<i style="left:58%;top:45%"></i><i style="left:66%;top:85%"></i>'
    '<i style="left:74%;top:35%"></i><i style="left:82%;top:65%"></i>'
    '<i style="left:88%;top:20%"></i><i style="left:14%;top:15%"></i>'
    '</div>'
)

_PHM_EMBLEM = (
    '<svg class="ph-emblem" viewBox="0 0 64 64" width="58" height="58" aria-hidden="true">'
    '<defs><linearGradient id="phg" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#3b82f6"/><stop offset="1" stop-color="#8b5cf6"/></linearGradient></defs>'
    '<path d="M32 6 L54 14 V32 C54 46 44 55 32 59 C20 55 10 46 10 32 V14 Z" fill="url(#phg)" opacity=".92"/>'
    '<path d="M22 32 L29 39 L43 25" stroke="#fff" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
    '</svg>'
)


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _warning_sample(lang: str) -> str:
    """取该语言的一条代表性警示语样例（玩具窒息警示 — 最高频执法类目）。"""
    for rule in CE_RULES:
        if rule["category"] == "toys":
            return rule["warnings"].get(lang) or rule["warnings"]["en"]
    return ""


def _page(platform: str) -> str:
    card = platform_rules.platform_rules_card(platform)
    name, countries = _PLATFORM_DISPLAY[platform]
    native = _LANG_NAME.get(card["native_language"], card["native_language"])
    sample = _warning_sample(card["native_language"])
    others = [p for p in platform_rules.list_native_rule_platforms() if p != platform]

    rules_html = "".join(
        f'<li>{_esc(r)}</li>' for r in card["rules"])
    reps_html = "".join(
        f'<li>{_esc(r)}</li>' for r in card["rep_requirements"])
    others_html = "".join(
        f'<a class="x-link" href="/rules/{p}">{_x_inner(p, _PLATFORM_DISPLAY[p][1])}</a>'
        for p in others)
    auth_short = card["authority"].split("（")[0]

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} GPSR 合规规则 · {native}警示语 · 监管机构 {_esc(auth_short)} | CrossAIO</title>
<meta name="description" content="{name} 平台 GPSR 合规规则速查：{_esc(card['policy_name'])}、当地监管 {_esc(card['authority'])}、欧代字段要求、{native}警示语与合规块生成。缺合规块后果：{_esc(card['enforcement'])}">
<style>
{_RULES_CSS}
{NAV_CSS}
</style>
</head>
<body>
{site_nav("platforms", platform, switcher=_switcher_rules(f"/rules/{platform}", "zh"))}

<div class="page-head">
  <div class="ph-grid"></div>
  <div class="ph-glow"><i class="g1"></i><i class="g2"></i></div>
  {_PARTICLES}
  <div class="ph-inner">
    {_PHM_EMBLEM}
    <div class="eyebrow">{name} · GPSR 平台原生规则</div>
    <h1>{name} GPSR 合规规则速查</h1>
    <p>{_esc(card['policy_name'])}<br>当地监管机构：{_esc(card['authority'])} · 平台原生语言：{native}</p>
    <div class="ph-badges">
      <span class="ph-badge">🏪 {name}</span>
      <span class="ph-badge">{countries}</span>
      <span class="ph-badge ph-auth">🛡️ {_esc(auth_short)}</span>
    </div>
  </div>
</div>

<section>
  <div class="card">
    <h3>📋 官方政策与回填位置</h3>
    <div class="meta-row">
      <span class="badge">覆盖市场：{countries}</span>
      <span class="badge">合规信息回填字段：{_esc(card['listing_field'])}</span>
      <span class="badge">警示语语言数：{card['warning_language_count']}</span>
    </div>
    <a class="policy-link" href="{card['policy_url']}" target="_blank" rel="noopener">官方政策入口 ↗</a>
  </div>

  <div class="card danger">
    <h3>🚨 违规后果（不做 GPSR 的代价）</h3>
    <p style="font-size:14.5px;font-weight:600">{_esc(card['enforcement'])}</p>
  </div>

  <div class="card">
    <h3>📐 {name} 平台特有规则（{card['rule_count']} 条）</h3>
    <ul>{rules_html}</ul>
  </div>

  <div class="card">
    <h3>🇪🇺 欧盟责任人（欧代）字段要求</h3>
    <ul>{reps_html}</ul>
  </div>

  <div class="card">
    <h3>🌐 {native}警示语样例（玩具窒息警示 — 最高频执法类目）</h3>
    <div class="gh-code">
      <div class="bar"><i></i><i></i><i></i><span>warning · {_esc(card['native_language'])}.txt</span></div>
      <div class="body">{_esc(sample)}</div>
    </div>
    <div class="lock">🔒 其余类目（电气/PPE/母婴/食品接触等）全部 {card['warning_language_count']} 语言警示语 + 完整合规块，
    在 <a href="/pricing" style="color:var(--blue);font-weight:700">Starter 档（€29/月）</a>解锁，含{name}平台原生头部与欧代行，可直接粘贴或经 API 回填。</div>
  </div>

  <div class="cta-band">
    <div class="cta-inner">
      <h2>你的 {name} listing 合规吗？30 秒免费体检</h2>
      <p>输入产品标题与关键词，立刻看到缺什么、会被{_esc(auth_short)}怎么罚</p>
      <div class="cta-row">
        <a href="/gpsr-check"><button class="pill-blue">免费体检 {name} listing →</button></a>
        <a href="/compliance-check"><button class="pill-ghost">一键合规体检</button></a>
      </div>
      <div class="cta-note">查看 <a href="/pricing">定价与解锁原生合规块 →</a></div>
    </div>
  </div>

  <h2 class="sec">其他已深耕平台的原生规则页</h2>
  <div class="x-links">{others_html}</div>
</section>

<footer>
  <a href="/">首页</a> · <a href="/rules">规则速查表</a> · <a href="/pricing">定价</a> · <a href="/gpsr-check">免费体检</a>
  <div style="margin-top:10px">CrossAIO — 平台原生 GPSR 合规引擎 · 规则信息为工程辅助参考，以平台官方政策为准 · © 2026</div>
</footer>
</body>
</html>"""


@router.get("/rules/{platform}", response_class=HTMLResponse, include_in_schema=False)
def platform_rule_page(platform: str):
    """平台 GPSR 规则落地页（动态渲染，数据源 platform_rules）。"""
    if platform not in platform_rules.list_native_rule_platforms():
        return RedirectResponse("/rules", status_code=302)
    return HTMLResponse(_page(platform))


# ---------------------------------------------------------------------------
# 多语言基础设施（en/de/fr）— hreflang / 切换器 / 偏好脚本 与 gpsr_pages.py
# 冻结范式逐字符对齐；zh 仍走上面的 _page()，输出逐字节不变。
# ---------------------------------------------------------------------------
_LANG_HTML = {"zh": "zh-CN", "en": "en", "de": "de", "fr": "fr"}
_LANG_PREFIX = {"zh": "", "en": "/en", "de": "/de", "fr": "/fr"}


def _hreflang_rules(base: str, lang: str) -> str:
    """<head> 内 5 行 hreflang；中文路径无前缀，x-default 指向中文版。"""
    b = settings.public_url
    return (
        f'<link rel="alternate" hreflang="zh" href="{b}{base}">\n'
        f'<link rel="alternate" hreflang="en" href="{b}/en{base}">\n'
        f'<link rel="alternate" hreflang="de" href="{b}/de{base}">\n'
        f'<link rel="alternate" hreflang="fr" href="{b}/fr{base}">\n'
        f'<link rel="alternate" hreflang="x-default" href="{b}{base}">'
    )


def _switcher_rules(base: str, lang: str) -> str:
    """语言切换器：🌐 图标 + 原生下拉（英文第一、中文最后）。"""
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


# ---------------------------------------------------------------------------
# 页面层 I18N 数据（仅本文件；platform_rules.py 数据不动）
# 翻译范围：页面框架文案、countries 行、语言名、rep_requirements / enforcement /
# rules 三字段、authority 括注。native 字段（policy_name/policy_url/listing_field/
# block_header/rep_label/native_language/警示语样例）保持平台原生语言不译。
# ---------------------------------------------------------------------------
_RULES_I18N = {
    "en": {
        "countries": {
            "allegro": "🇵🇱 Poland / Czechia / Slovakia · pl/cs/sk",
            "emag": "🇷🇴 Romania / Hungary / Bulgaria · ro/hu/bg",
            "cdiscount": "🇫🇷 France · fr",
            "otto": "🇩🇪 Germany · de",
            "kaufland": "🇩🇪🇦🇹🇨🇿🇸🇰 Germany / Austria / Czechia / Slovakia · de/cs/sk",
            "bol": "🇳🇱🇧🇪 Netherlands / Belgium · nl",
        },
        "lang_name": {
            "en": "English", "de": "German", "fr": "French", "es": "Spanish",
            "it": "Italian", "pl": "Polish", "ro": "Romanian", "nl": "Dutch",
            "sv": "Swedish", "cs": "Czech", "sk": "Slovak", "hu": "Hungarian",
            "bg": "Bulgarian",
        },
        "authority": {
            "allegro": "UOKiK (Polish Competition and Consumer Protection Authority)",
            "emag": "ANPC (National Authority for Consumer Protection, Romania)",
            "cdiscount": "DGCCRF (Directorate General for Competition, Consumer Affairs and Fraud Control)",
            "otto": "Market surveillance authorities of the German Länder",
            "kaufland": "Market surveillance authorities (DE) + ČIA/ÚOP (CZ/SK)",
            "bol": "ACM (Netherlands Authority for Consumers and Markets) + FOD (Belgium)",
        },
        "t": {
            "title": "{name} GPSR compliance rules · {native} warnings · market surveillance {authority} | CrossAIO",
            "desc": "{name} platform GPSR compliance quick reference: {policy}, local surveillance {authority}, EU-rep field requirements, {native} warnings and compliance-block generation. Cost of skipping the compliance block: {enforcement}",
            "eyebrow": "{name} · native GPSR platform rules",
            "h1": "{name} GPSR compliance rules at a glance",
            "head_p": "{policy}<br>Market surveillance authority: {authority} · native listing language: {native}",
            "card1_h3": "📋 Official policy & backfill location",
            "badge_markets": "Markets covered: {countries}",
            "badge_field": "Compliance-info backfill field: {field}",
            "badge_warn": "Warning languages: {n}",
            "policy_link": "Official policy entry ↗",
            "danger_h3": "🚨 Consequences of non-compliance (the cost of skipping GPSR)",
            "rules_h3": "📐 {name} platform-specific rules ({n})",
            "rep_h3": "🇪🇺 EU responsible person (EU Rep) field requirements",
            "sample_h3": "🌐 {native} warning sample (toy choking warning — most enforced category)",
            "lock": "🔒 All other categories (electrical / PPE / baby & maternity / food contact): {n}-language warnings + the full compliance block, unlocked in the {pricing} Starter plan (€29/mo). Includes {name}'s native header and EU-rep line — ready to paste or backfill via API.",
            "pricing_starter": "Starter",
            "cta_h2": "Is your {name} listing compliant? Free 30-second check",
            "cta_p": "Enter your product title and keywords and instantly see what's missing and how {authority} will penalize it",
            "btn1": "Free check of {name} listing →",
            "btn2": "Unlock the native compliance block",
            "btn3": "One-click compliance check",
            "xlinks_h2": "Native rule pages of other platforms we've deep-dived",
            "footer_home": "Home", "footer_rules": "Rules reference",
            "footer_pricing": "Pricing", "footer_check": "Free check",
            "slogan": "CrossAIO — platform-native GPSR compliance engine · rule information is engineering assistance; the platform's official policy prevails · © 2026",
        },
        "cards": {
            "allegro": {
                "listing_field": "description / Safety information",
                "rep_requirements": [
                    "EU responsible person name + postal address (Polish sellers may use a local entity)",
                    "Contact email must be readable text; pure images are not allowed",
                    "Product identifier (model/batch) must match the packaging",
                ],
                "enforcement": "Non-compliant listings are hidden or delisted; repeat offenses restrict account features; UOKiK may impose fines of up to 10% of turnover",
                "rules": [
                    "Since Dec 2024 Allegro requires non-EU sellers to disclose an EU responsible person in the listing, otherwise delisting under GPSR",
                    "Polish warnings are mandatory; readability for CZ/SK-site buyers follows Allegro's translation policy",
                    "Toys must include an EN 71 test summary (the DoC may be provided as a link)",
                ],
            },
            "emag": {
                "rep_requirements": [
                    "An EU responsible person based in Romania is acceptable; eMAG requires name + address + phone + email",
                    "GPSR information must appear as text in the description, beyond photos",
                    "The product page must include a DoC (Declaration of Conformity) link or a way to request it",
                ],
                "enforcement": "ANPC fines (up to RON 100,000 per case); eMAG delists the listing and freezes payouts until rectification",
                "rules": [
                    "eMAG Romania requires Romanian warnings (the language ANPC enforces in)",
                    "Hungarian is optional (eMAG.HU is a separate site, not auto-synced)",
                    "Electronics must state RoHS and WEEE recycling information in the description",
                ],
            },
            "cdiscount": {
                "rep_requirements": [
                    "EU responsible person information must be in French; DGCCRF requires a read-receipt email",
                    "French warnings are mandatory on the French site (Loi Toubon: consumer information must be in French)",
                    "Product identifier, CE mark and EU responsible person must appear on the same page",
                ],
                "enforcement": "DGCCRF administrative summons / criminal penalties (up to 2 years imprisonment + €300,000); Cdiscount delists directly",
                "rules": [
                    "French warnings are mandatory (Loi Toubon) and cannot be replaced by English alone",
                    "Food-contact products must carry a French food-contact declaration and DGCCRF number",
                    "Products with button batteries must carry a child-swallowing warning (French enforcement focus since 2023)",
                ],
            },
            "otto": {
                "rep_requirements": [
                    "German market surveillance (ProdSG §6(2)) requires the EU responsible person information to be readable in German",
                    "Otto requires the EU responsible person details to match between the listing and the packaging",
                    "The GS mark (if applicable) must be shown alongside the CE mark",
                ],
                "enforcement": "ProdSG fines up to €100,000 per case; Otto delists the listing and it affects the store rating",
                "rules": [
                    "German warnings are mandatory; Otto runs random GPSR checks on German-site listings",
                    "Plug type must be Schuko (DE/AT); IT/CH plug standards must be explained separately",
                    "The VerpackG LUCID registration number must be available on request",
                ],
            },
            "kaufland": {
                "rep_requirements": [
                    "EU responsible person information must cover all sales-site languages (DE/AT/CZ/SK)",
                    "Kaufland requires the DoC file to be uploaded to the Seller Portal",
                ],
                "enforcement": "Delisting + violation record in the Seller Portal; ProdSG fine risk on the German site",
                "rules": [
                    "The four-country sites (DE/AT/CZ/SK) share one listing, so warnings must cover all four languages",
                    "Uploading the EN 71 DoC for toys is a hard requirement of the site",
                ],
            },
            "bol": {
                "rep_requirements": [
                    "Responsible person information in Dutch/French (BE); ACM requires a read-receipt email",
                    "bol requires EU responsible person information to appear in both the listing and the invoice",
                ],
                "enforcement": "ACM fines (up to 1% of turnover / €900,000); bol delists and deducts conversion weight",
                "rules": [
                    "Dutch warnings are mandatory; Belgian buyers get French warnings",
                    "Battery products must state RECURSEL/BEBAT recycling information",
                ],
            },
        },
    },
    "de": {
        "countries": {
            "allegro": "🇵🇱 Polen / Tschechien / Slowakei · pl/cs/sk",
            "emag": "🇷🇴 Rumänien / Ungarn / Bulgarien · ro/hu/bg",
            "cdiscount": "🇫🇷 Frankreich · fr",
            "otto": "🇩🇪 Deutschland · de",
            "kaufland": "🇩🇪🇦🇹🇨🇿🇸🇰 Deutschland / Österreich / Tschechien / Slowakei · de/cs/sk",
            "bol": "🇳🇱🇧🇪 Niederlande / Belgien · nl",
        },
        "lang_name": {
            "en": "Englisch", "de": "Deutsch", "fr": "Französisch", "es": "Spanisch",
            "it": "Italienisch", "pl": "Polnisch", "ro": "Rumänisch", "nl": "Niederländisch",
            "sv": "Schwedisch", "cs": "Tschechisch", "sk": "Slowakisch", "hu": "Ungarisch",
            "bg": "Bulgarisch",
        },
        "authority": {
            "allegro": "UOKiK (Polnische Behörde für Wettbewerb und Verbraucherschutz)",
            "emag": "ANPC (Nationale Behörde für Verbraucherschutz, Rumänien)",
            "cdiscount": "DGCCRF (Generaldirektion für Wettbewerb, Verbraucherschutz und Betrugsbekämpfung)",
            "otto": "Marktüberwachungsbehörden der deutschen Länder",
            "kaufland": "Marktüberwachungsbehörden (DE) + ČIA/ÚOP (CZ/SK)",
            "bol": "ACM (Niederländische Behörde für Verbraucher und Märkte) + FOD (Belgien)",
        },
        "t": {
            "title": "{name} GPSR-Compliance-Regeln · {native} Warnhinweise · Marktüberwachung {authority} | CrossAIO",
            "desc": "{name} GPSR-Compliance-Regeln im Überblick: {policy}, lokale Marktüberwachung {authority}, Anforderungen an das EU-Verantwortlichen-Feld, {native} Warnhinweise und Compliance-Block-Erzeugung. Folgen ohne Compliance-Block: {enforcement}",
            "eyebrow": "{name} · native GPSR-Plattformregeln",
            "h1": "{name} GPSR-Compliance-Regeln im Überblick",
            "head_p": "{policy}<br>Marktüberwachungsbehörde: {authority} · native Listing-Sprache: {native}",
            "card1_h3": "📋 Offizielle Richtlinie & Backfill-Stelle",
            "badge_markets": "Abgedeckte Märkte: {countries}",
            "badge_field": "Backfill-Feld für Compliance-Info: {field}",
            "badge_warn": "Warnhinweis-Sprachen: {n}",
            "policy_link": "Offizielle Richtlinie aufrufen ↗",
            "danger_h3": "🚨 Folgen eines Verstoßes (die Kosten, GPSR zu ignorieren)",
            "rules_h3": "📐 {name}-spezifische Plattformregeln ({n})",
            "rep_h3": "🇪🇺 Anforderungen an den EU-Verantwortlichen-Feld",
            "sample_h3": "🌐 {native} Warnhinweis-Beispiel (Spielzeug-Erstickungswarnung — am häufigsten geprüfte Kategorie)",
            "lock": "🔒 Alle weiteren Kategorien (Elektro / PPE / Baby & Mama / Lebensmittelkontakt): Warnhinweise in {n} Sprachen + vollständiger Compliance-Block, freischaltbar im {pricing}-Starter-Tarif (€29/Monat). Inkl. nativem {name}-Kopf und EU-Verantwortlichen-Zeile — direkt einfügbar oder per API backfillbar.",
            "pricing_starter": "Starter",
            "cta_h2": "Ist dein {name}-Listing compliant? Kostenloser 30-Sekunden-Check",
            "cta_p": "Produkttitel und Keywords eingeben und sofort sehen, was fehlt und wie {authority} es ahnden wird",
            "btn1": "Kostenloser Check des {name}-Listings →",
            "btn2": "Native Compliance-Block freischalten",
            "btn3": "Compliance-Check in einem Klick",
            "xlinks_h2": "Native Regel-Seiten weiterer Plattformen",
            "footer_home": "Startseite", "footer_rules": "Regelübersicht",
            "footer_pricing": "Preise", "footer_check": "Kostenloser Check",
            "slogan": "CrossAIO — native GPSR-Compliance-Engine · Regeln sind technische Hilfestellung, maßgeblich ist die offizielle Plattformrichtlinie · © 2026",
        },
        "cards": {
            "allegro": {
                "listing_field": "description / Safety information",
                "rep_requirements": [
                    "Name + Postanschrift des EU-Verantwortlichen (polnische Verkäufer dürfen ein lokales Unternehmen nutzen)",
                    "Die Kontakt-E-Mail muss als lesbarer Text angegeben werden; reine Bilder sind nicht erlaubt",
                    "Die Produktkennzeichnung (Modell/Batch) muss mit der Verpackung übereinstimmen",
                ],
                "enforcement": "Beanstandete Listings werden ausgeblendet oder gelöscht; bei Wiederholungstaten werden Kontofunktionen eingeschränkt; UOKiK kann Bußgelder von bis zu 10 % des Umsatzes verhängen",
                "rules": [
                    "Seit Dez. 2024 verlangt Allegro von Nicht-EU-Verkäufern die Angabe eines EU-Verantwortlichen im Listing, sonst De-Listing nach GPSR",
                    "Warnhinweise auf Polnisch sind Pflicht; Lesbarkeit für Käufer auf CZ/SK-Sites richtet sich nach der Allegro-Übersetzungsrichtlinie",
                    "Spielzeug muss eine EN-71-Prüfzusammenfassung enthalten (die DoC darf als Link hinterlegt werden)",
                ],
            },
            "emag": {
                "rep_requirements": [
                    "Ein in Rumänien ansässiger EU-Verantwortlicher ist zulässig; eMAG verlangt Name + Adresse + Telefon + E-Mail",
                    "GPSR-Informationen müssen als Text in der Beschreibung erscheinen, nicht nur in Fotos",
                    "Die Produktseite muss einen Link zur DoC (Konformitätserklärung) oder einen Weg zu deren Anforderung enthalten",
                ],
                "enforcement": "ANPC-Bußgelder (bis zu 100.000 RON pro Fall); eMAG nimmt das Listing raus und sperrt Auszahlungen bis zur Nachbesserung",
                "rules": [
                    "eMAG Rumänien verlangt rumänische Warnhinweise (die Sprache der ANPC-Überwachung)",
                    "Ungarisch ist optional (eMAG.HU ist eine eigenständige Site, keine automatische Synchronisierung)",
                    "Elektronikprodukte müssen in der Beschreibung auf RoHS- und WEEE-Recycling hinweisen",
                ],
            },
            "cdiscount": {
                "rep_requirements": [
                    "Die Angaben zum EU-Verantwortlichen müssen auf Französisch sein; die DGCCRF verlangt eine E-Mail mit Empfangsbestätigung",
                    "Französische Warnhinweise sind auf der französischen Site Pflicht (Loi Toubon: Verbraucherinformationen müssen auf Französisch erfolgen)",
                    "Produktkennzeichnung, CE-Kennzeichnung und EU-Verantwortlicher müssen auf derselben Seite stehen",
                ],
                "enforcement": "DGCCRF: Verwaltungsvorladung / Strafen (bis zu 2 Jahren Haft + 300.000 €); Cdiscount nimmt das Listing direkt raus",
                "rules": [
                    "Französische Warnhinweise sind Pflicht (Loi Toubon), reines Englisch reicht nicht",
                    "Lebensmittelkontaktprodukte brauchen eine französische Erklärung zum Lebensmittelkontakt mit DGCCRF-Nummer",
                    "Knopfzellen-Produkte brauchen einen Warnhinweis zum Verschlucken durch Kinder (französischer Prüfschwerpunkt seit 2023)",
                ],
            },
            "otto": {
                "rep_requirements": [
                    "Die deutsche Marktüberwachung (ProdSG 6 Abs. 2) verlangt, dass die Angaben zum EU-Verantwortlichen auf Deutsch lesbar sind",
                    "Otto verlangt Übereinstimmung der Angaben zum EU-Verantwortlichen in Listing und Verpackung",
                    "Das GS-Zeichen (falls vorhanden) ist neben dem CE-Zeichen zu zeigen",
                ],
                "enforcement": "ProdSG-Bußgelder bis zu 100.000 € pro Fall; Otto löscht das Listing und das geht in die Shop-Bewertung ein",
                "rules": [
                    "Deutsche Warnhinweise sind Pflicht; Otto führt stichprobenartige GPSR-Prüfungen auf DE-Listings durch",
                    "Steckertyp muss Schuko sein (DE/AT); IT/CH-Steckernormen sind extra zu erläutern",
                    "Die LUCID-Registriernummer nach Verpackungsgesetz (VerpackG) muss vorliegen",
                ],
            },
            "kaufland": {
                "rep_requirements": [
                    "Die Angaben zum EU-Verantwortlichen müssen alle Verkaufssprachen abdecken (DE/AT/CZ/SK)",
                    "Kaufland verlangt das Hochladen der DoC-Datei ins Seller Portal",
                ],
                "enforcement": "De-Listing + Verstoß-Eintrag im Seller Portal; ProdSG-Bußgeldrisiko auf der DE-Site",
                "rules": [
                    "Die vier Länder-Sites (DE/AT/CZ/SK) teilen sich ein Listing, Warnhinweise müssen alle vier Sprachen abdecken",
                    "Für Spielzeug ist das Hochladen der EN-71-DoC eine harte Site-Vorgabe",
                ],
            },
            "bol": {
                "rep_requirements": [
                    "Verantwortlichen-Angaben auf Niederländisch/Französisch (BE); die ACM verlangt eine E-Mail mit Empfangsbestätigung",
                    "bol verlangt die Angabe zum EU-Verantwortlichen sowohl im Listing als auch auf der Rechnung",
                ],
                "enforcement": "ACM-Bußgelder (bis zu 1 % des Umsatzes / 900.000 €); bol löscht das Listing und zieht Conversion-Gewicht ab",
                "rules": [
                    "Niederländische Warnhinweise sind Pflicht; belgische Käufer erhalten französische Warnhinweise",
                    "Batterieprodukte müssen Recycling-Hinweise zu RECURSEL/BEBAT enthalten",
                ],
            },
        },
    },
    "fr": {
        "countries": {
            "allegro": "🇵🇱 Pologne / Tchéquie / Slovaquie · pl/cs/sk",
            "emag": "🇷🇴 Roumanie / Hongrie / Bulgarie · ro/hu/bg",
            "cdiscount": "🇫🇷 France · fr",
            "otto": "🇩🇪 Allemagne · de",
            "kaufland": "🇩🇪🇦🇹🇨🇿🇸🇰 Allemagne / Autriche / Tchéquie / Slovaquie · de/cs/sk",
            "bol": "🇳🇱🇧🇪 Pays-Bas / Belgique · nl",
        },
        "lang_name": {
            "en": "anglais", "de": "allemand", "fr": "français", "es": "espagnol",
            "it": "italien", "pl": "polonais", "ro": "roumain", "nl": "néerlandais",
            "sv": "suédois", "cs": "tchèque", "sk": "slovaque", "hu": "hongrois",
            "bg": "bulgare",
        },
        "authority": {
            "allegro": "UOKiK (Office polonais de la concurrence et de la protection des consommateurs)",
            "emag": "ANPC (Autorité nationale de protection des consommateurs, Roumanie)",
            "cdiscount": "DGCCRF (Direction générale de la concurrence, de la consommation et de la répression des fraudes)",
            "otto": "Autorités de surveillance du marché des Länder allemands",
            "kaufland": "Autorités de surveillance du marché (DE) + ČIA/ÚOP (CZ/SK)",
            "bol": "ACM (Autorité néerlandaise des consommateurs et des marchés) + FOD (Belgique)",
        },
        "t": {
            "title": "Règles GPSR {name} · avertissements {native} · surveillance {authority} | CrossAIO",
            "desc": "Référence GPSR {name} : {policy}, surveillance locale {authority}, exigences sur le représentant UE, avertissements {native} et génération de bloc de conformité. Sanctions sans bloc conformité : {enforcement}",
            "eyebrow": "{name} · règles GPSR natives de la plateforme",
            "h1": "{name} — règles de conformité GPSR en un coup d'œil",
            "head_p": "{policy}<br>Autorité de surveillance du marché : {authority} · langue native du listing : {native}",
            "card1_h3": "📋 Politique officielle & emplacement de backfill",
            "badge_markets": "Marchés couverts : {countries}",
            "badge_field": "Champ de backfill des infos conformité : {field}",
            "badge_warn": "Langues des avertissements : {n}",
            "policy_link": "Accès à la politique officielle ↗",
            "danger_h3": "🚨 Sanctions en cas de non-conformité (le coût de l'oubli du GPSR)",
            "rules_h3": "📐 Règles spécifiques à {name} ({n})",
            "rep_h3": "🇪🇺 Exigences relatives au champ représentant UE",
            "sample_h3": "🌐 Exemple d'avertissement {native} (avertissement d'étouffement pour jouets — catégorie la plus contrôlée)",
            "lock": "🔒 Toutes les autres catégories (électrique / EPI / bébé & maternité / contact alimentaire) : avertissements en {n} langues + bloc de conformité complet, déblocables sur le {pricing} forfait Starter (29 €/mois). Avec en-tête natif {name} et ligne représentant UE — prêt à coller ou à backfiller via l'API.",
            "pricing_starter": "forfait",
            "cta_h2": "Votre listing {name} est-il conforme ? Vérification gratuite en 30 s",
            "cta_p": "Saisissez titre produit et mots-clés, et voyez immédiatement ce qui manque et comment {authority} sanctionnera",
            "btn1": "Vérification gratuite du listing {name} →",
            "btn2": "Débloquer le bloc de conformité natif",
            "btn3": "Vérification conformité en 1 clic",
            "xlinks_h2": "Pages de règles natives d'autres plateformes",
            "footer_home": "Accueil", "footer_rules": "Référentiel de règles",
            "footer_pricing": "Tarifs", "footer_check": "Vérification gratuite",
            "slogan": "CrossAIO — moteur de conformité GPSR natif par plateforme · les règles sont une assistance technique, la politique officielle de la plateforme prévaut · © 2026",
        },
        "cards": {
            "allegro": {
                "listing_field": "description / Safety information",
                "rep_requirements": [
                    "Nom + adresse postale du représentant UE (les vendeurs polonais peuvent utiliser une entité locale)",
                    "L'adresse e-mail de contact doit être un texte lisible ; les images seules ne sont pas autorisées",
                    "L'identifiant produit (modèle/lot) doit correspondre à l'emballage",
                ],
                "enforcement": "Les listings non conformes sont masqués ou déréférencés ; les récidives entraînent des restrictions de compte ; l'UOKiK peut infliger des amendes allant jusqu'à 10 % du chiffre d'affaires",
                "rules": [
                    "Depuis décembre 2024, Allegro exige des vendeurs non UE qu'ils indiquent un représentant UE dans le listing, sous peine de déréférencement au titre du GPSR",
                    "Les avertissements en polonais sont obligatoires ; la lisibilité pour les acheteurs des sites CZ/SK suit la politique de traduction d'Allegro",
                    "Les jouets doivent comporter un résumé d'essai EN 71 (la DoC peut être fournie sous forme de lien)",
                ],
            },
            "emag": {
                "rep_requirements": [
                    "Un représentant UE établi en Roumanie est accepté ; eMAG exige nom + adresse + téléphone + e-mail",
                    "Les informations GPSR doivent apparaître en texte dans la description, au-delà des photos",
                    "La page produit doit comporter un lien vers la DoC (déclaration de conformité) ou un moyen de la demander",
                ],
                "enforcement": "Amendes de l'ANPC (jusqu'à 100 000 RON par infraction) ; eMAG déréférence et bloque les paiements jusqu'à mise en conformité",
                "rules": [
                    "eMAG Roumanie exige des avertissements en roumain (langue retenue par l'ANPC)",
                    "Le hongrois est optionnel (eMAG.HU est un site distinct, sans synchronisation automatique)",
                    "Les produits électroniques doivent mentionner les consignes de recyclage RoHS et DEEE dans la description",
                ],
            },
            "cdiscount": {
                "rep_requirements": [
                    "Les informations sur le représentant UE doivent être en français ; la DGCCRF exige un e-mail avec accusé de réception",
                    "Les avertissements en français sont obligatoires sur le site France (Loi Toubon : l'information aux consommateurs doit être en français)",
                    "Identifiant produit, marquage CE et représentant UE doivent figurer sur la même page",
                ],
                "enforcement": "Convocation administrative / sanctions pénales de la DGCCRF (jusqu'à 2 ans d'emprisonnement + 300 000 €) ; Cdiscount déréférence immédiatement",
                "rules": [
                    "Les avertissements en français sont obligatoires (Loi Toubon), l'anglais seul ne suffit pas",
                    "Les produits au contact des aliments doivent comporter une déclaration française de contact alimentaire et un numéro DGCCRF",
                    "Les produits à pile bouton doivent porter un avertissement sur l'ingestion par les enfants (priorité de contrôle française depuis 2023)",
                ],
            },
            "otto": {
                "rep_requirements": [
                    "La surveillance du marché allemande (ProdSG §6 al. 2) exige que les informations sur le représentant UE soient lisibles en allemand",
                    "Otto exige que les coordonnées du représentant UE correspondent entre le listing et l'emballage",
                    "Le label GS (le cas échéant) doit figurer à côté du marquage CE",
                ],
                "enforcement": "Amendes ProdSG jusqu'à 100 000 € par infraction ; Otto déréférence le listing et la note boutique est impactée",
                "rules": [
                    "Les avertissements en allemand sont obligatoires ; Otto effectue des contrôles GPSR aléatoires sur les listings du site Allemagne",
                    "Le type de prise doit être Schuko (DE/AT) ; les normes IT/CH doivent être expliquées séparément",
                    "Le numéro d'enregistrement LUCID (VerpackG) doit pouvoir être fourni",
                ],
            },
            "kaufland": {
                "rep_requirements": [
                    "Les informations sur le représentant UE doivent couvrir toutes les langues des sites de vente (DE/AT/CZ/SK)",
                    "Kaufland exige le téléversement de la DoC dans le Seller Portal",
                ],
                "enforcement": "Déréférencement + signalement d'infraction dans le Seller Portal ; risque d'amende ProdSG sur le site Allemagne",
                "rules": [
                    "Les quatre sites (DE/AT/CZ/SK) partagent un même listing, les avertissements doivent couvrir les quatre langues",
                    "Le dépôt de la DoC EN 71 pour les jouets est une exigence stricte du site",
                ],
            },
            "bol": {
                "rep_requirements": [
                    "Informations sur le responsable en néerlandais/français (BE) ; l'ACM exige un e-mail avec accusé de réception",
                    "bol exige que les informations sur le responsable UE figurent à la fois dans le listing et sur la facture",
                ],
                "enforcement": "Amendes ACM (jusqu'à 1 % du chiffre d'affaires / 900 000 €) ; bol déréférence et retire du poids de conversion",
                "rules": [
                    "Les avertissements en néerlandais sont obligatoires ; les acheteurs belges reçoivent les avertissements en français",
                    "Les produits avec batterie doivent mentionner les consignes de recyclage RECURSEL/BEBAT",
                ],
            },
        },
    },
}


def _page_i18n(platform: str, lang: str) -> str:
    card = platform_rules.platform_rules_card(platform)
    i18n = _RULES_I18N[lang]
    d = i18n["t"]
    name = _PLATFORM_DISPLAY[platform][0]
    countries = i18n["countries"][platform]
    native = i18n["lang_name"][card["native_language"]]
    authority = i18n["authority"][platform]
    pd = i18n["cards"][platform]
    sample = _warning_sample(card["native_language"])
    p = _LANG_PREFIX[lang]
    base = f"/rules/{platform}"
    others = [x for x in platform_rules.list_native_rule_platforms() if x != platform]

    rules_html = "".join(f'<li>{_esc(r)}</li>' for r in pd["rules"])
    reps_html = "".join(f'<li>{_esc(r)}</li>' for r in pd["rep_requirements"])
    others_html = "".join(
        f'<a class="x-link" href="{p}/rules/{x}">{_x_inner(x, i18n["countries"][x])}</a>'
        for x in others)

    title = d["title"].format(name=name, native=_esc(native), authority=_esc(authority))
    desc = d["desc"].format(
        name=name, policy=_esc(card["policy_name"]), authority=_esc(authority),
        native=_esc(native), enforcement=_esc(pd["enforcement"]))
    eyebrow = d["eyebrow"].format(name=name)
    h1 = d["h1"].format(name=name)
    head_p = d["head_p"].format(
        policy=_esc(card["policy_name"]), authority=_esc(authority), native=_esc(native))
    badge_markets = d["badge_markets"].format(countries=countries)
    badge_field = d["badge_field"].format(field=_esc(pd.get("listing_field", card["listing_field"])))
    badge_warn = d["badge_warn"].format(n=card["warning_language_count"])
    rules_h3 = d["rules_h3"].format(name=name, n=card["rule_count"])
    sample_h3 = d["sample_h3"].format(native=_esc(native))
    cta_h2 = d["cta_h2"].format(name=name)
    cta_p = d["cta_p"].format(authority=_esc(authority))
    btn1 = d["btn1"].format(name=name)
    auth_short = authority.split(" (")[0]
    lock = d["lock"].format(
        n=card["warning_language_count"], name=name,
        pricing=f'<a href="{p}/pricing" style="color:var(--blue);font-weight:700">{_esc(d["pricing_starter"])}</a>')

    return f"""<!DOCTYPE html>
<html lang="{_LANG_HTML[lang]}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
{_hreflang_rules(base, lang)}
<style>
{_RULES_CSS}
{NAV_CSS}
</style>
</head>
<body>
{site_nav("platforms", platform, lang=lang, switcher=_switcher_rules(base, lang))}

<div class="page-head">
  <div class="ph-grid"></div>
  <div class="ph-glow"><i class="g1"></i><i class="g2"></i></div>
  {_PARTICLES}
  <div class="ph-inner">
    {_PHM_EMBLEM}
    <div class="eyebrow">{eyebrow}</div>
    <h1>{h1}</h1>
    <p>{head_p}</p>
    <div class="ph-badges">
      <span class="ph-badge">🏪 {name}</span>
      <span class="ph-badge">{countries}</span>
      <span class="ph-badge ph-auth">🛡️ {_esc(auth_short)}</span>
    </div>
  </div>
</div>

<section>
  <div class="card">
    <h3>{d['card1_h3']}</h3>
    <div class="meta-row">
      <span class="badge">{badge_markets}</span>
      <span class="badge">{badge_field}</span>
      <span class="badge">{badge_warn}</span>
    </div>
    <a class="policy-link" href="{card['policy_url']}" target="_blank" rel="noopener">{_esc(d['policy_link'])}</a>
  </div>

  <div class="card danger">
    <h3>{d['danger_h3']}</h3>
    <p style="font-size:14.5px;font-weight:600">{_esc(pd['enforcement'])}</p>
  </div>

  <div class="card">
    <h3>{rules_h3}</h3>
    <ul>{rules_html}</ul>
  </div>

  <div class="card">
    <h3>{d['rep_h3']}</h3>
    <ul>{reps_html}</ul>
  </div>

  <div class="card">
    <h3>{sample_h3}</h3>
    <div class="gh-code">
      <div class="bar"><i></i><i></i><i></i><span>warning · {_esc(card['native_language'])}.txt</span></div>
      <div class="body">{_esc(sample)}</div>
    </div>
    <div class="lock">{lock}</div>
  </div>

  <div class="cta-band">
    <div class="cta-inner">
      <h2>{cta_h2}</h2>
      <p>{cta_p}</p>
      <div class="cta-row">
        <a href="{p}/gpsr-check"><button class="pill-blue">{btn1}</button></a>
        <a href="{p}/compliance-check"><button class="pill-ghost">{_esc(d['btn3'])}</button></a>
      </div>
      <div class="cta-note"><a href="{p}/pricing">{_esc(d['btn2'])} →</a></div>
    </div>
  </div>

  <h2 class="sec">{_esc(d['xlinks_h2'])}</h2>
  <div class="x-links">{others_html}</div>
</section>

<footer>
  <a href="{p}/">{_esc(d['footer_home'])}</a> · <a href="{p}/rules">{_esc(d['footer_rules'])}</a> · <a href="{p}/pricing">{_esc(d['footer_pricing'])}</a> · <a href="{p}/gpsr-check">{_esc(d['footer_check'])}</a>
  <div style="margin-top:10px">{_esc(d['slogan'])}</div>
</footer>
{_LANG_SCRIPT}
</body>
</html>"""


@router.get("/{lang}/rules/{platform}", response_class=HTMLResponse, include_in_schema=False)
def platform_rule_page_i18n(lang: str, platform: str):
    """平台 GPSR 规则落地页 en/de/fr 三语版（/rules/{platform} 的语言镜像）。"""
    if lang not in ("en", "de", "fr"):
        return HTMLResponse("Not Found", status_code=404)
    if platform not in platform_rules.list_native_rule_platforms():
        return RedirectResponse(f"/{lang}/rules", status_code=302)
    return HTMLResponse(_page_i18n(platform, lang))
