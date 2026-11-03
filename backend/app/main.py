"""
CrossAIO — FastAPI 主应用
本地运行：uvicorn app.main:app --reload --port 8000
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db
from .routers import (ads, analytics, billing, customer_service, ebay,
                      listings, products, users, eu_rep, inbox, rule_pages,
                      feature_pages, gpsr_pages, compliance, automation)
from .routers.site_nav import FEATURE_ITEMS, FEATURE_I18N, NAV_I18N
from .scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
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
app.include_router(compliance.router, prefix=f"{API_PREFIX}/compliance", tags=["compliance"])
app.include_router(automation.router, prefix=f"{API_PREFIX}", tags=["automation"])
app.include_router(listings.router, prefix=f"{API_PREFIX}", tags=["watch"])


@app.get("/", include_in_schema=False)
def index():
    """营销主页（H10 风格：Hero + 平台墙 + 功能 + 定价预览 + FAQ）"""
    return FileResponse(Path(__file__).parent / "static" / "home.html")


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
    return FileResponse(f)


@app.get("/{lang}/", include_in_schema=False)
def lang_home(lang: str):
    """语言目录根：/en/ /de/ /fr/ → static/{lang}/home.html"""
    if lang not in I18N_LANGS:
        raise HTTPException(status_code=404)
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
# 动态 sitemap.xml：4 语言 × 32 路径 = 128 条 URL
# ---------------------------------------------------------------------------
SITEMAP_PATHS = (
    "/", "/app", "/pricing", "/privacy", "/terms", "/skills", "/rules",
    "/signin", "/signup", "/compliance-check", "/gpsr-check",
    "/gpsr-check/features", "/gpsr-check/platforms", "/gpsr-check/compare",
    "/gpsr-check/pricing", "/gpsr-check/faq",
    # 产品能力落地页（9 页 + 总览）
    "/features",
    "/features/gpsr", "/features/listing-generator", "/features/matrix",
    "/features/review-rewrite", "/features/ai-service",
    "/features/safety-redline", "/features/inbox", "/features/ad-copy",
    "/features/listing-watch",
    # 平台原生规则落地页（6 平台）
    "/rules/allegro", "/rules/emag", "/rules/cdiscount", "/rules/otto",
    "/rules/kaufland", "/rules/bol",
)
SITEMAP_LANGS = ("zh", "en", "de", "fr")
SITEMAP_LASTMOD = "2026-11-03"


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml():
    """动态站点地图：基址取 settings.app_url；中文无前缀，en/de/fr 加前缀。"""
    from xml.sax.saxutils import escape

    base = settings.app_url.rstrip("/")
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path in SITEMAP_PATHS:
        for lang in SITEMAP_LANGS:
            if lang == "zh":
                loc_path = path
            else:
                loc_path = f"/{lang}/" + path.lstrip("/")
            out.append(
                f"  <url><loc>{escape(base + loc_path)}</loc>"
                f"<lastmod>{SITEMAP_LASTMOD}</lastmod></url>")
    out.append("</urlset>")
    return Response("\n".join(out), media_type="application/xml")
