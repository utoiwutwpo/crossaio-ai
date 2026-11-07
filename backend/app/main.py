"""
CrossAIO — FastAPI 主应用
本地运行：uvicorn app.main:app --reload --port 8000
"""
import base64 as _base64
import logging
import re as _re
import secrets as _secrets
import time as _time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qsl as _parse_qsl, urlencode as _urlencode

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .config import settings
from .database import init_db
from . import community_models  # 注册社区/播客/峰会 ORM 模型（随 create_all 自动建表）
from . import blog_post_pages   # 博客文章真实 URL 页（/en/blog/{slug}，SEO 可索引）
from .routers import (ads, analytics, billing, customer_service, ebay,
                      listings, products, users, eu_rep, inbox, rule_pages,
                      feature_pages, gpsr_pages, compliance, automation,
                      community, podcast, summit, blog, trust, academy,
                      notifications, connectors)
from .routers.site_nav import FEATURE_ITEMS, FEATURE_I18N, NAV_I18N
from .scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from .content_seed import _ensure_content
    _ensure_content()   # 增长飞轮内容补种（博客/播客/峰会，幂等）
    from .community_seed import ensure_community_threads
    ensure_community_threads()   # 社区示例讨论（按跨境平台分子类别，幂等）
    start_scheduler()   # 7x24 监控：每日定时体检 + 风险日报
    yield
    stop_scheduler()


app = FastAPI(
    title="CrossAIO API",
    description="跨境电商AI助手 — 产品描述生成 / AI客服 / 广告文案",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# SEO：为所有 HTML 页面注入 canonical / hreflang / description / OG 标签。
# 单点实现，无需改 44+ 个静态文件；页面已自带 canonical 时自动跳过（幂等）。
# ---------------------------------------------------------------------------
SEO_LANGS = ("en", "de", "fr")
SEO_GENERIC_DESC = {
    "zh": "CrossAIO——欧洲跨境电商 AI 合规工作台：GPSR 合规检查、AI 产品描述、差评改写、多语言 AI 客服与广告文案，一站覆盖 Allegro、Otto、Kaufland、bol 等欧洲主流平台。",
    "en": "CrossAIO — the AI compliance workspace for European cross-border e-commerce: GPSR checks, AI product descriptions, review rewrites, multilingual AI customer service and ad copy across Allegro, Otto, Kaufland, bol and more.",
    "de": "CrossAIO — die KI-Compliance-Plattform für europäischen grenzüberschreitenden E-Commerce: GPSR-Prüfungen, KI-Produkttexte, Rezbewertungen umschreiben, mehrsprachiger KI-Kundenservice und Werbetexte für Allegro, Otto, Kaufland, bol und mehr.",
    "fr": "CrossAIO — la plateforme de conformité IA pour le e-commerce transfrontalier européen : contrôles GPSR, descriptions produits par IA, réécriture d'avis négatifs, service client IA multilingue et textes publicitaires sur Allegro, Otto, Kaufland, bol et plus.",
}
SEO_PAGE_DESC = {
    "/": {
        "zh": "CrossAIO：欧洲跨境电商 AI 合规工作台。GPSR 合规检查、AI 产品描述生成、差评改写、多语言客服，4 语种界面，免费开始。",
        "en": "CrossAIO: AI compliance workspace for selling into Europe. GPSR checks, AI listing descriptions, review rewrites and multilingual support in 4 languages. Start free.",
        "de": "CrossAIO: KI-Compliance-Workbench für den Verkauf in Europa. GPSR-Prüfungen, KI-Produkttexte, Rezbewertungen und mehrsprachiger Support in 4 Sprachen. Kostenlos starten.",
        "fr": "CrossAIO : l'atelier de conformité IA pour vendre en Europe. Contrôles GPSR, descriptions produits IA, réécriture d'avis et support multilingue en 4 langues. Démarrage gratuit.",
    },
    "/pricing": {
        "zh": "CrossAIO 定价：Starter €29/月、Pro €49/月、Business €149/月，年付更省。含 GPSR 合规、AI 描述、差评改写与多语言客服配额。",
        "en": "CrossAIO pricing: Starter €29/mo, Pro €49/mo, Business €149/mo — save with yearly billing. GPSR compliance, AI descriptions, review rewrites and multilingual support included.",
        "de": "CrossAIO Preise: Starter 29 €/Monat, Pro 49 €/Monat, Business 149 €/Monat — mit Jahresabo sparen. Inklusive GPSR-Compliance, KI-Texte und mehrsprachigem Support.",
        "fr": "Tarifs CrossAIO : Starter 29 €/mois, Pro 49 €/mois, Business 149 €/mois — économisez avec l'abonnement annuel. Conformité GPSR, descriptions IA et support multilingue inclus.",
    },
    "/gpsr-check": {
        "zh": "免费 GPSR 合规自查：上传产品信息，按欧盟通用产品安全法规逐项检查，生成整改清单，覆盖 27 国要求。",
        "en": "Free GPSR compliance check: upload your product data and get an itemized EU General Product Safety Regulation report with a remediation checklist for all 27 member states.",
        "de": "Kostenlose GPSR-Prüfung: Produktdaten hochladen und einen detaillierten Bericht zur EU-Produktsicherheitsverordnung mit Maßnahmen-Checkliste erhalten.",
        "fr": "Contrôle GPSR gratuit : téléversez vos données produit et obtenez un rapport détaillé au règlement européen sur la sécurité générale des produits, avec plan d'action.",
    },
}
_SEO_NOINDEX_SEGMENTS = ("app", "signin", "signup", "traffic")


def _split_lang_path(path: str):
    """'/de/pricing' → ('de', '/pricing')；'/' → ('en', '/')（英文为默认首页）；
    '/zh/' → ('zh', '/')；'/en/' → ('en', '/')；其余根路径视为中文页。"""
    parts = path.strip("/").split("/", 1)
    if parts and parts[0] == "zh":
        sub = "/" + parts[1] if len(parts) > 1 and parts[1] else "/"
        return "zh", sub
    if parts and parts[0] in SEO_LANGS:
        sub = "/" + parts[1] if len(parts) > 1 and parts[1] else "/"
        return parts[0], sub
    if not path or path == "/":
        return "en", "/"
    return "zh", path


def _seo_head_tags(path: str, html: str) -> str:
    lang, sub = _split_lang_path(path)
    base = settings.site_url

    # URL 生成：首页 en='/'、zh='/zh/'；其余页面中文无前缀（根路径），
    # en /{lang} 前缀。中文内容页仍以根路径为 canonical（已提交 GSC 的 URL 不变）。
    def _u(lg: str) -> str:
        if sub == "/":
            if lg == "en":
                return base + "/"
            if lg == "zh":
                return base + "/zh/"
            return f"{base}/{lg}/"
        return base + sub if lg == "zh" else f"{base}/{lg}{sub}"

    m = _re.search(r"<title[^>]*>(.*?)</title>", html, _re.S | _re.I)
    title = _re.sub(r"\s+", " ", m.group(1)).strip() if m else "CrossAIO"

    if any(seg in path.rstrip("/").split("/") for seg in _SEO_NOINDEX_SEGMENTS):
        return '<meta name="robots" content="noindex, follow">'

    from xml.sax.saxutils import escape as _e
    desc = (SEO_PAGE_DESC.get(sub) or SEO_GENERIC_DESC).get(lang) or SEO_GENERIC_DESC["en"]
    has_desc = 'name="description"' in html
    has_og = 'property="og:title"' in html
    # 顺序：英文优先（en → de → fr）；2026-11-06 决策 zh 不做 SEO，不入 hreflang
    alternates = "".join(
        f'<link rel="alternate" hreflang="{lg}" href="{_e(_u(lg))}">'
        for lg in ("en", "de", "fr"))
    alternates += f'<link rel="alternate" hreflang="x-default" href="{_e(_u("en"))}">'
    desc_tags = "" if has_desc else f'<meta name="description" content="{_e(desc)}">'
    og_tags = "" if has_og else (
        '<meta property="og:type" content="website">'
        + '<meta property="og:site_name" content="CrossAIO">'
        + f'<meta property="og:title" content="{_e(title)}">'
        + f'<meta property="og:description" content="{_e(desc)}">'
        + f'<meta property="og:url" content="{_e(_u(lang))}">'
        + '<meta name="twitter:card" content="summary_large_image">'
        + f'<meta name="twitter:title" content="{_e(title)}">'
        + f'<meta name="twitter:description" content="{_e(desc)}">'
    )
    return (
        f'<link rel="canonical" href="{_e(_u(lang))}">'
        + alternates
        + desc_tags
        + og_tags
    )


# ---------------------------------------------------------------------------
# 访问量统计：服务端 PV + UTM 首触归因 + 可选 GA4
# 2026-11-07 P0：UA 三态分类（human / bot / probe）与渠道参数落库，
# 目的是让一周后的「真人访问量 / 渠道转化」可复算、可归因，不再被自检请求灌水。
# ---------------------------------------------------------------------------
_BOT_UA_RE = _re.compile(
    r"bot|spider|crawl|slurp|bingpreview|facebookexternalhit|curl|python|"
    r"wget|httpie|headless|ahrefs|semrush|mj12|dotbot|go-http-client|"
    r"scrapy|mechanize|libwww|lwp::|java/|node-fetch|axios|okhttp|"
    r"yandex|baiduspider|duckduckbot|petalbot", _re.I)

# 内部探针 / 平台健康检查 / 自动化浏览器：单列 probe，既不算真人也不算搜索引擎。
_PROBE_UA_RE = _re.compile(
    r"uptimerobot|pingdom|statuscake|site24x7|monitor|healthcheck|health-check|"
    r"kube-probe|elb-healthcheck|googlehc|render/|nagios|zabbix|datadog|"
    r"newrelic|lighthouse|playwright|puppeteer|selenium|phantomjs|postman|"
    r"insomnia|crossaio-|check_http", _re.I)

# 真人浏览器必须具备完整指纹：Mozilla/5.0 + 渲染引擎 + 具体浏览器版本号。
_BROWSER_UA_RE = _re.compile(
    r"Mozilla/5\.0.*(?:Chrome/\d|Safari/\d|Firefox/\d|Edg/\d|"
    r"OPR/\d|Version/\d|SamsungBrowser/\d)", _re.I | _re.S)

_UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")
_VID_COOKIE = "caio_vid"
_ATTR_COOKIE = "caio_attr"

# Referer 兜底：已云端排期但链接未带 UTM 的帖子（FB 3 条）仍能归到渠道。
_REF_CHANNELS = (
    ("reddit", "reddit"), ("sellerforum", "sellerforum"),
    ("facebook", "facebook"), ("instagram", "instagram"),
    ("google.", "google"), ("bing.", "bing"),
    ("linkedin.", "linkedin"), ("youtube.", "youtube"),
    ("allegro", "allegro"), ("bol.com", "bol"), ("emag", "emag"),
)


def _classify_ua(ua: str, accept: str, sec_fetch_dest: str) -> str:
    """返回 human / bot / probe。

    2026-11-06 的看板把「无 UA / 健康检查 / 自建 curl 验证」也算成真人，
    导致 31 个真人 PV 中几乎没有真实访客。此处改为三态：
      bot    = 搜索引擎与已知抓取器（仍要单独看，判断收录进度）
      probe  = 空 UA、无浏览器指纹、健康检查、自动化客户端（不计真人）
      human  = 完整浏览器指纹 + 文档导航请求头
    """
    u = (ua or "").strip()
    low = u.lower()
    if _BOT_UA_RE.search(low):
        return "bot"
    if not u or len(u) < 25 or _PROBE_UA_RE.search(low):
        return "probe"
    if not _BROWSER_UA_RE.search(u):
        return "probe"
    if sec_fetch_dest and sec_fetch_dest.lower() not in ("document", "iframe"):
        return "probe"
    if "text/html" not in (accept or "").lower():
        return "probe"
    return "human"


def _utm_from_query(request) -> dict:
    out = {}
    for k in _UTM_KEYS:
        v = (request.query_params.get(k) or "").strip()[:60]
        if v:
            out[k] = v
    return out


def _encode_attr(utm: dict) -> str:
    """cookie 值用 urlsafe base64，避免 & / = 被 Cookie 解析器截断。"""
    return _base64.urlsafe_b64encode(_urlencode(utm).encode()).decode().rstrip("=")


def _decode_attr(raw: str) -> dict:
    try:
        s = _base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode()
        return {k: v[:60] for k, v in _parse_qsl(s, keep_blank_values=False)
                if k in _UTM_KEYS}
    except Exception:
        return {}


def _ref_channel(ref: str) -> str:
    low = (ref or "").lower()
    for needle, name in _REF_CHANNELS:
        if needle in low:
            return name
    return ""


def _ga4_snippet() -> str:
    """Measurement ID 未配置时返回空串，站点保持零第三方脚本。"""
    mid = (settings.ga4_measurement_id or "").strip()
    if not mid.startswith("G-") or len(mid) < 5:
        return ""
    return (
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={mid}"></script>'
        '<script>window.dataLayer=window.dataLayer||[];'
        'function gtag(){dataLayer.push(arguments);}'
        'gtag("js",new Date());'
        f'gtag("config","{mid}");</script>'
    )


def _record_pageview(request, vid: str, utm: dict, ua_kind: str, ref: str) -> None:
    """服务端记录一次页面浏览（含 UTM 首触归因）。失败绝不阻断业务。"""
    try:
        from .database import SessionLocal, AnalyticsEvent
        from .routers.analytics import ip_hash
        db = SessionLocal()
        try:
            db.add(AnalyticsEvent(
                event_type="page_view",
                platform=ua_kind,  # human / bot / probe
                utm_source=utm.get("utm_source", "")[:100],
                utm_medium=utm.get("utm_medium", "")[:100],
                utm_campaign=utm.get("utm_campaign", "")[:100],
                ip_hash=ip_hash(request),
                user_id="",
                meta={
                    "path": request.url.path[:200],
                    "ua": (request.headers.get("user-agent") or "")[:300],
                    "ua_kind": ua_kind,
                    "is_bot": ua_kind != "human",  # 兼容旧看板字段
                    "ref": ref[:200],
                    "vid": vid,
                    "utm": dict(utm),
                },
            ))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
    except Exception:
        pass


@app.middleware("http")
async def seo_head_inject_middleware(request, call_next):
    resp = await call_next(request)
    ctype = resp.headers.get("content-type", "")
    if resp.status_code != 200 or not ctype.startswith("text/html"):
        return resp
    body = b"".join([chunk async for chunk in resp.body_iterator])
    html = body.decode("utf-8", errors="replace")

    # 匿名访客 ID + 渠道归因 cookie（last non-direct，30 天）。
    # 只存随机 ID 与 utm_* 参数，不含任何个人信息。
    vid = request.cookies.get(_VID_COOKIE) or _secrets.token_hex(8)
    new_cookies: list[str] = []
    if not request.cookies.get(_VID_COOKIE):
        new_cookies.append(
            f"{_VID_COOKIE}={vid}; Max-Age=31536000; Path=/; SameSite=Lax; HttpOnly")
    ref = (request.headers.get("referer") or "")[:200]
    utm = _utm_from_query(request)
    if utm.get("utm_source"):
        new_cookies.append(
            f"{_ATTR_COOKIE}={_encode_attr(utm)}; Max-Age=2592000; Path=/; SameSite=Lax")
    else:
        utm = _decode_attr(request.cookies.get(_ATTR_COOKIE) or "")
        if not utm:
            channel = _ref_channel(ref)
            if channel:
                utm = {"utm_source": channel, "utm_medium": "referral"}
                # 无 UTM 的渠道点击（FB 云端帖 / Reddit profile）也要持久化，
                # 否则后续站内跳转后的体检 / 注册事件会丢失渠道归因。
                new_cookies.append(
                    f"{_ATTR_COOKIE}={_encode_attr(utm)}; Max-Age=2592000; Path=/; SameSite=Lax")

    # 服务端 PV：覆盖全部 200 HTML 页面；内部看板自身不计入，避免刷新污染数据。
    if request.url.path.rstrip("/") != "/traffic":
        ua_kind = _classify_ua(
            request.headers.get("user-agent") or "",
            request.headers.get("accept") or "",
            request.headers.get("sec-fetch-dest") or "",
        )
        await run_in_threadpool(
            _record_pageview, request, vid=vid, utm=utm,
            ua_kind=ua_kind, ref=ref)

    # GA4：ID 未配置时零注入。两个返回分支都要带上，故在此统一改写 body。
    head_i = html.find("<head")
    ga4 = _ga4_snippet()
    if ga4 and head_i >= 0 and "googletagmanager.com/gtag/js" not in html:
        gi = html.find(">", head_i)
        if gi >= 0:
            html = html[:gi + 1] + "\n" + ga4 + html[gi + 1:]
            body = html.encode("utf-8")

    def _with_cookies(r: Response) -> Response:
        for cookie in new_cookies:
            r.headers.append("set-cookie", cookie)
        return r

    def _rebuild(_body: bytes) -> Response:
        # body_iterator 已被上方消费，必须用新 Response 重建返回：
        # 直接 return resp 会得到已耗尽的迭代器 → 200 + 空 body（content-length 超前）。
        headers = dict(resp.headers)
        headers.pop("content-length", None)
        return _with_cookies(
            Response(_body, status_code=200, headers=headers, media_type=ctype))

    head_i = html.find("<head")
    if head_i < 0 or 'rel="canonical"' in html:
        return _rebuild(body)
    close_i = html.find(">", head_i)
    if close_i < 0:
        return _rebuild(body)
    try:
        tags = _seo_head_tags(request.url.path, html)
    except Exception:
        return _rebuild(body)
    new_html = html[:close_i + 1] + "\n" + tags + html[close_i + 1:]
    headers = dict(resp.headers)
    headers.pop("content-length", None)
    return _with_cookies(
        HTMLResponse(new_html, status_code=resp.status_code, headers=headers))

API_PREFIX = "/api/v1"
app.include_router(users.router, prefix=f"{API_PREFIX}/users", tags=["users"])
app.include_router(users.oauth_router, tags=["users-oauth"])  # Google OAuth2 回调：GET /users/google（顶层路径）
app.include_router(products.router, prefix=f"{API_PREFIX}/products", tags=["products"])
app.include_router(customer_service.router, prefix=f"{API_PREFIX}/customer-service", tags=["customer-service"])
app.include_router(customer_service.reviews_router, prefix=f"{API_PREFIX}/reviews", tags=["reviews"])  # P0-4 差评改写
app.include_router(ads.router, prefix=f"{API_PREFIX}/ads", tags=["ads"])
app.include_router(billing.router, prefix=f"{API_PREFIX}/billing", tags=["billing"])
app.include_router(ebay.router, prefix=f"{API_PREFIX}/ebay", tags=["eBay"])
app.include_router(analytics.router, prefix=f"{API_PREFIX}/analytics", tags=["analytics"])
app.include_router(eu_rep.router, prefix=f"{API_PREFIX}/eu-reps", tags=["eu-reps"])
app.include_router(inbox.router, prefix=f"{API_PREFIX}/inbox", tags=["inbox"])
app.include_router(rule_pages.router, tags=["rule-pages"])
# gpsr_pages 必须先于 feature_pages 注册：/gpsr-check/features 等 2 段路径
# 不能被 /{lang}/features（lang=gpsr-check）抢先匹配吞掉
app.include_router(gpsr_pages.router, tags=["gpsr-pages"])
app.include_router(feature_pages.router, tags=["feature-pages"])

# ---------------------------------------------------------------------------
# 增长页英文版 + 博客文章真实 URL（2026-11-06，SEO 修复）
# ---------------------------------------------------------------------------
# 背景：academy/community/blog/podcast/summit/trust 的根路径文件内容本身即英文
# （html lang="en"），但 sitemap 生成 /en/ 前缀 URL 时无对应路由 → 死链；
# 博客文章此前只有 hash 路由（/#slug），搜索引擎无法索引。
# 处理：逐页固定注册（不用 /en/{page} 通配，避免吞掉 /en/rules 等 I18N 页）；
# 注册顺序必须在 gpsr/feature router 之后、`/{lang}/{page}` 之前。
# zh 不做 SEO（2026-11-06 决策）：sitemap/hreflang 已整体移除 zh。
EN_GROWTH_PAGES = ("blog", "academy", "community", "podcast", "summit", "trust")
_EN_GROWTH_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate"}


def _en_growth_page(page: str):
    f = Path(__file__).parent / "static" / f"{page}.html"
    if not f.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(f, headers=_EN_GROWTH_CACHE)


for _p in EN_GROWTH_PAGES:
    def _handler(_page: str = _p):
        return _en_growth_page(_page)
    app.get(f"/en/{_p}", include_in_schema=False)(_handler)


@app.get("/en/blog/{slug}", include_in_schema=False)
def en_blog_post(slug: str):
    """博客文章规范 URL（英文，SEO 可索引；正文服务端渲染 + Article JSON-LD）。"""
    return blog_post_pages.render_post(slug)


@app.get("/blog/{slug}", include_in_schema=False)
def blog_post_root_redirect(slug: str):
    """根路径文章 URL 归一：规范地址为 /en/blog/{slug}（英文首发）。"""
    return RedirectResponse(f"/en/blog/{slug}", status_code=301)
# ---------------------------------------------------------------------------
app.include_router(compliance.router, prefix=f"{API_PREFIX}/compliance", tags=["compliance"])
app.include_router(automation.router, prefix=f"{API_PREFIX}", tags=["automation"])
app.include_router(listings.router, prefix=f"{API_PREFIX}", tags=["watch"])
app.include_router(notifications.router, prefix=f"{API_PREFIX}", tags=["notifications"])
app.include_router(connectors.router, prefix=f"{API_PREFIX}/platforms", tags=["connectors"])

# 社区 / 播客 / 峰会 —— 对标 Helium 10 Seller Connect Forum / Serious Sellers Podcast / Prosper Show
app.include_router(community.router, prefix=f"{API_PREFIX}/community", tags=["community"])
app.include_router(podcast.router, prefix=f"{API_PREFIX}/podcast", tags=["podcast"])
app.include_router(summit.router, prefix=f"{API_PREFIX}/summit", tags=["summit"])
app.include_router(blog.router, prefix=f"{API_PREFIX}/blog", tags=["blog"])
app.include_router(trust.router, prefix=f"{API_PREFIX}/trust", tags=["trust"])
app.include_router(academy.router, prefix=f"{API_PREFIX}/academy", tags=["academy"])

# 静态资源：/img/** 直接映射到 app/static/img/**（平台 logo、头像等）
app.mount("/img", StaticFiles(directory=Path(__file__).parent / "static" / "img"), name="img")
# 播客音频：/podcast-audio/** 映射到 app/static/podcast/**（TTS 预生成的单集音频）
app.mount("/podcast-audio", StaticFiles(directory=Path(__file__).parent / "static" / "podcast"),
          name="podcast-audio")

# 营销页/落地页 HTML 统一禁缓存：改版后浏览器立即拿到新 HTML，避免旧导航/旧文案滞留
_NO_CACHE_HEADERS = {"Cache-Control": "no-cache, no-store, must-revalidate"}


@app.post("/api/v1/admin/self-restart", include_in_schema=True,
          summary="远程自重启：触发 watcher 重启 / 兜底调起 restart-remote.bat")
def admin_self_restart():
    """运维通道（双保险）：
    1) 主通道：写 .restart-trigger 触发文件 → watcher（每 5 秒轮询）杀旧拉新；
    2) 兜底：同时调起 restart-remote.bat（杀旧→等3秒→start-uvicorn.bat），
       watcher 未运行时由 bat 直接完成重启。
    本请求正常返回后约 3-8 秒服务会短暂中断，随后以最新代码恢复。
    """
    import subprocess
    backend = Path(__file__).parent.parent
    # 1) trigger 文件（watcher 消费；即使 watcher 暂不在线，文件留在盘上无害）
    try:
        (backend / ".restart-trigger").write_text(
            f"self-restart via API {_time.strftime('%Y-%m-%dT%H:%M:%S')}", encoding="utf-8")
    except OSError:
        pass
    # 2) bat 兜底
    bat = backend / "restart-remote.bat"
    if bat.is_file():
        # 直接 cmd /c 执行 bat（不加 start 包装：DETACHED 下 start 会静默失败）；
        # CREATE_NO_WINDOW 隐藏窗口，bat 作为独立进程存活，随后会杀掉本服务并拉起新实例
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            subprocess.Popen(["cmd", "/c", str(bat)],
                             cwd=str(bat.parent), creationflags=flags, close_fds=False)
        except OSError:
            pass  # bat 失败时仍可依赖 trigger 文件（watcher 在线时）
    return {"ok": True,
            "message": "restart scheduled: trigger file written + bat fallback; service bounces in ~3-8s"}


@app.get("/", include_in_schema=False)
def index():
    """营销主页（默认英文版：www.crossaio.com 首页采用英语，中文版迁至 /zh/）"""
    return FileResponse(Path(__file__).parent / "static" / "en" / "home.html",
                        headers=_NO_CACHE_HEADERS)


@app.get("/zh", include_in_schema=False)
@app.get("/zh/", include_in_schema=False)
def zh_home():
    """中文营销主页：/zh/（原根路径中文首页迁移至此）"""
    return FileResponse(Path(__file__).parent / "static" / "home.html",
                        headers=_NO_CACHE_HEADERS)


def _feature_nav_html(lang: str = "zh") -> str:
    """工作台头部的「产品能力」下拉导航 — 单一数据源 site_nav.FEATURE_ITEMS。

    与首页/落地页同构：9 个落地页直达链接 + 🗂️ 产品能力总览，
    悬停高亮展开，点击即跳转。
    lang="zh" 时输出与历史版本逐字节等价；en/de/fr 文案按术语表翻译，
    /features/* 已有翻译版本，href 加语言前缀。
    """
    nav = NAV_I18N.get(lang, NAV_I18N["zh"])
    feat_tr = FEATURE_I18N.get(lang)
    p = "" if lang == "zh" else f"/{lang}"
    links = ""
    for i, (_, href, icon, label, sub) in enumerate(FEATURE_ITEMS):
        if feat_tr is not None:
            label, sub = feat_tr[i]
        links += (f'<a href="{p}{href}"><span>{icon} {label}'
                  f'<small>{sub}</small></span></a>')
    links += (f'<a href="{p}/features"><span>🗂️ {nav["feature_overview_label"]}'
              f'<small>{nav["feature_overview_sub"]}</small></span></a>')
    return (f'<div class="fnavitem"><span class="flabel">{nav["features"]} ▾</span>'
            f'<div class="fdrop">{links}</div></div>')


@app.get("/en/sitemap", include_in_schema=False)
def html_sitemap():
    """可索引的 HTML 站点地图（英文）：把全部可索引 URL 串成站内抓取枢纽。

    2026-11-07 索引加速：Googlebot 从首页可达的链接出发，能一次性发现
    13 个平台规则页与 5 篇高意图文章，比只依赖 sitemap.xml 更快。
    页面自带 canonical + en-only hreflang，避免 middleware 注入 de/fr 死链。
    """
    from xml.sax.saxutils import escape
    base = settings.site_url
    canonical = f"{base}/en/sitemap"
    blog_paths = [f"/blog/{s}" for s in _blog_slugs()]
    rule_paths = [p for p in SITEMAP_PATHS if p.startswith("/rules/")]
    feature_paths = [p for p in SITEMAP_PATHS if p.startswith("/features")]
    core_paths = [p for p in SITEMAP_PATHS
                  if not p.startswith(("/rules/", "/features"))
                  and p != "/sitemap"]
    groups = (
        ("High-intent compliance guides", blog_paths),
        ("Marketplace rule pages (13 platforms)", rule_paths),
        ("Product capability pages", feature_paths),
        ("Core pages", core_paths),
    )

    def _li(path: str) -> str:
        url = _sitemap_loc("en", path)
        label = url[len(base):] or "/"
        return f'<li><a href="{escape(url)}">{escape(label)}</a></li>'

    sections = []
    for title, paths in groups:
        if not paths:
            continue
        sections.append(
            f'<section><h2>{escape(title)} <span class="n">{len(paths)}</span></h2>'
            f'<ul class="cols">{"".join(_li(p) for p in paths)}</ul></section>')

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Site map | CrossAIO EU compliance guides &amp; marketplace rules</title>
<link rel="canonical" href="{escape(canonical)}">
<link rel="alternate" hreflang="en" href="{escape(canonical)}">
<link rel="alternate" hreflang="x-default" href="{escape(canonical)}">
<meta name="description" content="Browse every CrossAIO page: EU GPSR compliance guides, Error 5995 and takedown appeal SOPs, and native rule pages for 13 European marketplaces.">
<style>
body{{margin:0;background:#f6f7f9;color:#1b1f26;font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.wrap{{max-width:1000px;margin:0 auto;padding:36px 20px 70px}}
h1{{font-size:26px;margin:0 0 6px}} p.sub{{color:#6b7280;margin:0 0 28px}}
section{{background:#fff;border:1px solid #e6e8ec;border-radius:10px;padding:18px 20px;margin-bottom:16px}}
h2{{font-size:16px;margin:0 0 12px}} h2 .n{{color:#6b7280;font-weight:400;font-size:13px}}
ul.cols{{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(2,1fr);gap:4px 20px}}
li a{{color:#0f766e;text-decoration:none}} li a:hover{{text-decoration:underline}}
footer{{margin-top:24px;color:#6b7280;font-size:13px}}
@media(max-width:700px){{ul.cols{{grid-template-columns:1fr}}}}
</style>
</head>
<body><div class="wrap">
<h1>CrossAIO site map</h1>
<p class="sub">All indexable English pages, grouped by intent. Updated {SITEMAP_LASTMOD}.</p>
{''.join(sections)}
<footer><a href="/en/">Home</a> · <a href="/sitemap.xml">XML sitemap</a> · CrossAIO © 2026</footer>
</div></body></html>"""
    return HTMLResponse(page, headers={"Cache-Control": "no-cache"})


@app.get("/traffic", include_in_schema=False)
def traffic_dashboard():
    """内部访问量看板（noindex；数据接口需 X-Admin-Token）。"""
    return FileResponse(
        Path(__file__).parent / "static" / "traffic.html",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.get("/app", include_in_schema=False)
def app_workbench():
    """工作台（登录后使用：生成/体检/客服/广告/差评改写/订阅）。

    头部注入与全站一致的「产品能力」多页式导航（占位符替换，
    数据源共享 site_nav.FEATURE_ITEMS，避免 12 份拷贝漂移）。
    """
    html = (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(
        html.replace("<!--FEATURE_NAV-->", _feature_nav_html()),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.get("/pricing", include_in_schema=False)
def pricing_page():
    """定价页（四档套餐 + 功能对比表 + 计费 FAQ）"""
    return FileResponse(Path(__file__).parent / "static" / "pricing.html")


@app.get("/privacy", include_in_schema=False)
def privacy_page():
    """隐私政策（GDPR 合规）"""
    return FileResponse(Path(__file__).parent / "static" / "privacy.html")


@app.get("/terms", include_in_schema=False)
def terms_page():
    """服务条款"""
    return FileResponse(Path(__file__).parent / "static" / "terms.html")


@app.get("/skills", include_in_schema=False)
def skills_page():
    """开源 Skills 展示页（GPSR 检查器 + 欧洲平台规则库，MIT）"""
    return FileResponse(Path(__file__).parent / "static" / "skills.html")


@app.get("/trust", include_in_schema=False)
def trust_page():
    """透明定价信任页（反定位：四承诺 + 公开对比 + 一键取消）"""
    return FileResponse(Path(__file__).parent / "static" / "trust.html")


@app.get("/blog", include_in_schema=False)
def blog_page():
    """博客内容矩阵页（教育获客，英文首发，en/de/fr）"""
    return FileResponse(Path(__file__).parent / "static" / "blog.html")


@app.get("/academy", include_in_schema=False)
def academy_page():
    """Academy 页（教育护城河：课程/进度/结业证书，术语同化载体）"""
    return FileResponse(Path(__file__).parent / "static" / "academy.html")


@app.get("/community", include_in_schema=False)
def community_page():
    """论坛页（Seller Connect 对标；作者证书徽章打通 Academy 身份）"""
    return FileResponse(Path(__file__).parent / "static" / "community.html")


@app.get("/podcast", include_in_schema=False)
def podcast_page():
    """播客落地页（收听闭环：播放器 + shownotes + 体检/Academy CTA + 峰会横幅）"""
    return FileResponse(Path(__file__).parent / "static" / "podcast.html")


@app.get("/summit", include_in_schema=False)
def summit_page():
    """虚拟峰会落地页（议程 + 报名带 UTM 归因 + 播客互链）"""
    return FileResponse(Path(__file__).parent / "static" / "summit.html")


@app.get("/rules", include_in_schema=False)
def rules_page():
    """免费平台规则速查页（13 平台 SEO/社群获客资产，数据来自注册表 API）"""
    return FileResponse(Path(__file__).parent / "static" / "rules.html")


@app.get("/signin", include_in_schema=False)
def signin_page():
    """登录页（H10 风格：Google 登录 + 邮箱密码）"""
    return FileResponse(Path(__file__).parent / "static" / "signin.html")


@app.get("/signup", include_in_schema=False)
def signup_page():
    """注册页（H10 风格：Google 注册 + 邮箱密码）"""
    return FileResponse(Path(__file__).parent / "static" / "signup.html")


@app.get("/gpsr-check/pl", include_in_schema=False)
def gpsr_landing_pl():
    """波兰语落地页 — Allegro 卖家社群投放"""
    return FileResponse(Path(__file__).parent / "static" / "gpsr-check-pl.html")


@app.get("/gpsr-check/ro", include_in_schema=False)
def gpsr_landing_ro():
    """罗马尼亚语落地页 — eMAG 卖家社群投放"""
    return FileResponse(Path(__file__).parent / "static" / "gpsr-check-ro.html")


@app.get("/gpsr", include_in_schema=False)
def gpsr_shortlink_zh():
    """社媒短链别名 — Facebook 链接化时会把连字符后的路径截断（/gpsr-check→/gpsr），
    统一 301 到英文版体检页（社媒引流全走英文站点）。"""
    return RedirectResponse("/en/gpsr-check", status_code=301)


@app.get("/en/gpsr", include_in_schema=False)
def gpsr_shortlink_en():
    """英文短链别名 — 同 /gpsr：社媒截断容错，301 到英文版体检页。"""
    return RedirectResponse("/en/gpsr-check", status_code=301)


@app.get("/compliance-check", include_in_schema=False)
def compliance_landing():
    """一键合规体检落地页（GPSR 付费闭环获客入口：免费体检 + 付费交付物）"""
    return FileResponse(Path(__file__).parent / "static" / "compliance-check.html")


@app.get("/effects.css", include_in_schema=False)
def effects_css():
    """共享静态样式（页面 <link href="/effects.css">）。"""
    return FileResponse(Path(__file__).parent / "static" / "effects.css")


@app.get("/effects.js", include_in_schema=False)
def effects_js():
    """共享静态效果脚本（滚动渐入/数字计数/语言切换器移动端折叠）。"""
    return FileResponse(Path(__file__).parent / "static" / "effects.js")


@app.get("/health", summary="健康检查")
def health():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "llm_mode": "mock" if not settings.llm_api_key else "live",
    }


# ---------------------------------------------------------------------------
# 三语静态页路由（en/de/fr，与中文版结构镜像）
# 注册在所有既有路由之后：/gpsr-check/pl、/gpsr-check/ro、/gpsr-check/* 等
# 由 gpsr_pages.router 先行匹配，不受本块影响。
# ---------------------------------------------------------------------------
I18N_LANGS = ("en", "de", "fr")
I18N_PAGES = ("pricing", "privacy", "terms", "skills", "rules",
              "signin", "signup", "compliance-check")


def _static_lang_file(lang: str, name: str) -> FileResponse:
    f = Path(__file__).parent / "static" / lang / f"{name}.html"
    if not f.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(f, headers=_NO_CACHE_HEADERS)


@app.get("/{lang}/", include_in_schema=False)
def lang_home(lang: str):
    """语言目录根：/en/ /de/ /fr/ → static/{lang}/home.html
    /en/ 已升级为根路径 /（英文为默认首页），301 归一避免重复内容。"""
    if lang not in I18N_LANGS:
        raise HTTPException(status_code=404)
    if lang == "en":
        return RedirectResponse("/", status_code=301)
    return _static_lang_file(lang, "home")


@app.get("/{lang}/app", include_in_schema=False)
def lang_app(lang: str):
    """语言工作台：/en/app 等，注入对应语言的「产品能力」导航。"""
    if lang not in I18N_LANGS:
        raise HTTPException(status_code=404)
    f = Path(__file__).parent / "static" / lang / "index.html"
    if not f.is_file():
        raise HTTPException(status_code=404)
    html = f.read_text(encoding="utf-8")
    return HTMLResponse(
        html.replace("<!--FEATURE_NAV-->", _feature_nav_html(lang)),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.get("/{lang}/{page}", include_in_schema=False)
def lang_static_page(lang: str, page: str):
    """语言静态页：/{lang}/{pricing,privacy,terms,skills,rules,signin,signup,compliance-check}"""
    if lang not in I18N_LANGS or page not in I18N_PAGES:
        raise HTTPException(status_code=404)
    return _static_lang_file(lang, page)


# ---------------------------------------------------------------------------
# 动态 sitemap.xml：4 语言 × 路径 + hreflang 互链；robots.txt；Google 验证文件
# ---------------------------------------------------------------------------
SITEMAP_PATHS = (
    "/", "/pricing", "/privacy", "/terms", "/skills", "/rules",
    "/compliance-check", "/gpsr-check",
    "/gpsr-check/features", "/gpsr-check/platforms", "/gpsr-check/compare",
    "/gpsr-check/pricing", "/gpsr-check/faq",
    # 产品能力落地页（9 页 + 总览）
    "/features",
    "/features/gpsr", "/features/listing-generator", "/features/matrix",
    "/features/review-rewrite", "/features/ai-service",
    "/features/safety-redline", "/features/inbox", "/features/ad-copy",
    "/features/listing-watch",
    # 平台原生规则落地页（2026-11-06 补齐 registry 全部 13 平台）
    "/rules/amazon", "/rules/amazon_us", "/rules/ebay", "/rules/zalando",
    "/rules/fruugo", "/rules/walmart", "/rules/tiktok",
    "/rules/allegro", "/rules/emag", "/rules/cdiscount", "/rules/otto",
    "/rules/kaufland", "/rules/bol",
    # 增长飞轮页（Academy / 社区 / 博客 / 播客 / 峰会 / 信任）
    "/academy", "/community", "/blog", "/podcast", "/summit", "/trust",
    "/sitemap",  # HTML 站点地图：首页可达的抓取枢纽（2026-11-07 索引加速）
)
SITEMAP_LANGS = ("en", "de", "fr")  # 三语（2026-11-06 决策：zh 不做 SEO，不入 sitemap/hreflang）
SITEMAP_LASTMOD = "2026-11-07"  # 索引加速：内容更新后改 lastmod，提示 Googlebot 重抓

# 单语页面：仅英文版真实存在（内容即英文，见 /en/{page} 增长页路由），
# sitemap 只收录 en；de/fr 无内容版，不得生成死链。
SITEMAP_EN_ONLY_PATHS = ("/academy", "/community", "/blog", "/podcast",
                         "/summit", "/trust", "/sitemap")


def _sitemap_loc(lang: str, path: str) -> str:
    # 首页特例：英文=根路径（默认首页）；其余页面按语言前缀。
    # zh 不做 SEO（2026-11-06 决策）：不再生成 /zh/ URL。
    if path == "/":
        return settings.site_url + ("/" if lang == "en" else f"/{lang}/")
    return settings.site_url + f"/{lang}/" + path.lstrip("/")


def _path_langs(path: str) -> tuple:
    """每路径收录语言：默认三语；单语页仅 en；博客文章页仅 en（英文首发）。"""
    if path in SITEMAP_EN_ONLY_PATHS or path.startswith("/blog/"):
        return ("en",)
    return SITEMAP_LANGS


def _blog_slugs() -> list[str]:
    """已发布博客文章 slug（sitemap 动态收录 /blog/{slug}，规范 URL 为 /en/blog/{slug}）。

    查询失败时返回空列表——sitemap 仍输出其余页面，不为内容库异常放大故障。
    """
    try:
        from .database import SessionLocal
        from .community_models import BlogPost
        db = SessionLocal()
        try:
            return [s for (s,) in db.query(BlogPost.slug)
                    .filter(BlogPost.is_published.is_(True))
                    .order_by(BlogPost.published_at.desc()).all()]
        finally:
            db.close()
    except Exception:
        return []


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml():
    """动态站点地图：基址取 settings.site_url（SEO 身份域名）；
    每条 URL 携带该路径实际存在语言的 hreflang 互链（单语页仅 en + x-default）；
    登录/注册/工作台不入图；博客文章随内容库动态收录。"""
    from xml.sax.saxutils import escape

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    paths = list(SITEMAP_PATHS) + [f"/blog/{s}" for s in _blog_slugs()]
    for path in paths:
        langs = _path_langs(path)
        loc = _sitemap_loc(langs[0], path)
        alts = "".join(
            f'<xhtml:link rel="alternate" hreflang="{lg}" '
            f'href="{escape(_sitemap_loc(lg, path))}"/>'
            for lg in langs)
        alts += (f'<xhtml:link rel="alternate" hreflang="x-default" '
                 f'href="{escape(_sitemap_loc("en", path))}"/>')
        out.append(
            f"  <url><loc>{escape(loc)}</loc>"
            f"<lastmod>{SITEMAP_LASTMOD}</lastmod>{alts}</url>")
    out.append("</urlset>")
    return Response("\n".join(out), media_type="application/xml")


@app.get("/robots.txt", include_in_schema=False)
def robots_txt():
    """robots.txt：放行全部页面（应用页靠 meta noindex 收编），声明 sitemap。"""
    lines = ["User-agent: *", "Allow: /", "Disallow: /api/",
             f"Sitemap: {settings.site_url}/sitemap.xml", ""]
    return Response("\n".join(lines), media_type="text/plain")


@app.get("/{vfile}", include_in_schema=False)
def google_verification_file(vfile: str):
    """Google Search Console 所有权验证：/google****.html 返回配置内容。

    GOOGLE_SITE_VERIFICATION 存文件名（如 google5c1a2b3d4e5f6789.html），
    验证内容可以是任意非空文本——GSC 只检查该 URL 返回 200。
    """
    token = settings.google_site_verification.strip()
    if token and vfile == token:
        return Response(f"google-site-verification: {token}", media_type="text/plain")
    raise HTTPException(status_code=404)
