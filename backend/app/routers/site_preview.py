"""站点预览路由（纯新增）。

新版落地页挂在 /zh/v2/**、/{lang}/v2/**（en/de/fr）与 /site-preview/** 三个前缀下；
不改动 /、/zh/、/en/ 与任何既有页面。
原站导航作为统一外壳运行时注入：中文读 static/home.html，英/德/法读各自语言首页，
保证四个语种外壳结构一致、仅文案不同。
注册位置必须早于 main.py 的 /{lang}/{page} 兜底路由。
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter()

_ROOT = Path(__file__).resolve().parent.parent / "static"
_DIR = _ROOT / "site-preview"
_HOME_BY_LANG = {
    "zh": _ROOT / "home.html",
    "en": _ROOT / "en" / "home.html",
    "de": _ROOT / "de" / "home.html",
    "fr": _ROOT / "fr" / "home.html",
}
_HEADERS = {"Cache-Control": "no-cache, no-store, must-revalidate"}
_PAGES = ("launch", "rescue", "ops", "govern")
LANGS = ("en", "de", "fr")


def _nav_shell(lang: str = "zh") -> str:
    """取该语种首页的导航，保证新版与同语种首页共用同一个外壳。"""
    try:
        html = _HOME_BY_LANG[lang].read_text(encoding="utf-8")
        start = html.index('<div class="topbar">')
        end = html.index("</nav>") + len("</nav>")
        return '<div id="site-nav">' + html[start:end] + "</div>"
    except Exception:
        return ""


def _html(name: str, prefix: str, lang: str = "zh") -> HTMLResponse:
    src = _DIR / f"{name}.html" if lang == "zh" else _DIR / lang / f"{name}.html"
    if not src.is_file():
        raise HTTPException(status_code=404)
    text = src.read_text(encoding="utf-8")
    if prefix != "/site-preview/":
        text = text.replace("/site-preview/", prefix)
    nav = _nav_shell(lang)
    if nav:
        text = text.replace(
            "</head>", '<link rel="stylesheet" href="%snav.css">\n</head>' % prefix, 1
        )
        text = text.replace("<body>", "<body>\n" + nav, 1)
    return HTMLResponse(content=text, headers=_HEADERS)


def _page(page: str) -> str:
    if page not in _PAGES:
        raise HTTPException(status_code=404)
    return page


@router.get("/site-preview/landing.css", include_in_schema=False)
def site_preview_css():
    return FileResponse(_DIR / "landing.css", media_type="text/css", headers=_HEADERS)


@router.get("/site-preview/nav.css", include_in_schema=False)
def site_preview_nav_css():
    return FileResponse(_DIR / "nav.css", media_type="text/css", headers=_HEADERS)


@router.get("/site-preview", include_in_schema=False)
@router.get("/site-preview/", include_in_schema=False)
def site_preview_home():
    return _html("index", "/site-preview/")


@router.get("/site-preview/{page}", include_in_schema=False)
def site_preview_page(page: str):
    return _html(_page(page), "/site-preview/")


@router.get("/zh/v2/landing.css", include_in_schema=False)
def zh_v2_css():
    return FileResponse(_DIR / "landing.css", media_type="text/css", headers=_HEADERS)


@router.get("/zh/v2/nav.css", include_in_schema=False)
def zh_v2_nav_css():
    return FileResponse(_DIR / "nav.css", media_type="text/css", headers=_HEADERS)


@router.get("/zh/v2", include_in_schema=False)
@router.get("/zh/v2/", include_in_schema=False)
def zh_v2_home():
    return _html("index", "/zh/v2/")


@router.get("/zh/v2/{page}", include_in_schema=False)
def zh_v2_page(page: str):
    return _html(_page(page), "/zh/v2/")

# —— 13 个二级落页（纯新增）：/zh/v2/feature|platform|tool/* ——
SUB_PAGES = {
    "feature": ("gpsr", "listing", "matrix", "review", "ai-service", "safety"),
    "platform": ("rules", "app", "localize", "limits"),
    "tool": ("check", "skills", "trust"),
}


@router.get("/zh/v2/{group}/{slug}", include_in_schema=False)
def zh_v2_subpage(group: str, slug: str):
    if group not in SUB_PAGES or slug not in SUB_PAGES[group]:
        raise HTTPException(status_code=404)
    return _html(f"{group}-{slug}", "/zh/v2/")


# ---------------------------------------------------------------------------
# 英 / 德 / 法三语镜像：/{lang}/v2/**（结构与中文版 1:1，文案为对应语种）
# ---------------------------------------------------------------------------
@router.get("/{lang}/v2/landing.css", include_in_schema=False)
def lang_v2_css(lang: str):
    if lang not in LANGS:
        raise HTTPException(status_code=404)
    return FileResponse(_DIR / "landing.css", media_type="text/css", headers=_HEADERS)


@router.get("/{lang}/v2/nav.css", include_in_schema=False)
def lang_v2_nav_css(lang: str):
    if lang not in LANGS:
        raise HTTPException(status_code=404)
    return FileResponse(_DIR / "nav.css", media_type="text/css", headers=_HEADERS)


@router.get("/{lang}/v2", include_in_schema=False)
@router.get("/{lang}/v2/", include_in_schema=False)
def lang_v2_home(lang: str):
    if lang not in LANGS:
        raise HTTPException(status_code=404)
    return _html("index", f"/{lang}/v2/", lang)


@router.get("/{lang}/v2/{group}/{slug}", include_in_schema=False)
def lang_v2_subpage(lang: str, group: str, slug: str):
    if lang not in LANGS or group not in SUB_PAGES or slug not in SUB_PAGES[group]:
        raise HTTPException(status_code=404)
    return _html(f"{group}-{slug}", f"/{lang}/v2/", lang)


@router.get("/{lang}/v2/{page}", include_in_schema=False)
def lang_v2_page(lang: str, page: str):
    if lang not in LANGS:
        raise HTTPException(status_code=404)
    return _html(_page(page), f"/{lang}/v2/", lang)
