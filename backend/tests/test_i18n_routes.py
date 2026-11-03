"""
三语化（zh / en / de / fr）路由回归测试。

只断言、不改业务代码。验证口径：
- /en /de /fr 静态主页、定价、工作台、GPSR 子页 → 200 + <html lang> 正确 + 无中文残留
  （中文残留判定前先删除 <div class="lang-switch"> 切换器块，该块内含「中文」标签属允许项）
- zh 路由回归：/ 、/pricing 、/gpsr-check 仍 200 且含中文原文
- /sitemap.xml → 200 + application/xml + 64 条 <loc> + 基址 http://localhost:9000
- hreflang 5 行 alternate，基址均为 http://localhost:9000
- 切换器 4 个 data-lang 链接 + 当前语言 aria-current="page"
- /gpsr-check/pl 、/gpsr-check/ro 仍 200；非法语言/路径 404
"""
import re

import pytest
from fastapi.testclient import TestClient

from app.main import app  # noqa: F401  (conftest 已设好测试环境并 import)

# CJK 统一表意文字（中文残留判定）
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
# 语言切换器块：<div class="lang-switch" ...>4 个 a 标签</div>（扁平，无嵌套 div）
SWITCHER_RE = re.compile(r'<div class="lang-switch".*?</div>', re.DOTALL)
# <style> 块：CSS 注释/规则不可见（feature_pages.py 顶部 CSS 含中文开发者注释，
# 属不可见串，单独上报；此处只判定「可见正文」是否漏译）。
STYLE_RE = re.compile(r"<style.*?</style>", re.DOTALL)
LANG_ATTR_RE = re.compile(r'<html lang="([^"]+)"')


def _visible(html: str) -> str:
    """只保留可见正文：删除 <style> 块（含不可见 CSS 中文注释）与语言切换器块
    （内含「中文」标签与各语言链接，属允许项）。"""
    html = STYLE_RE.sub("", html)
    html = SWITCHER_RE.sub("", html)
    return html


def cjk_residue(html: str) -> list:
    """可见正文中的 CJK 字符列表（空=无可见中文残留）。"""
    return CJK_RE.findall(_visible(html))


def html_lang(html: str) -> str:
    m = LANG_ATTR_RE.search(html)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# 1. 三语主页 /en/ /de/ /fr/
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("lang,marker", [
    ("en", "all-Europe"),          # en home title: "CrossAIO — the all-Europe platform ..."
    ("de", "Kostenlos"),           # de home: "Kostenlos registrieren" / "Kostenloser GPSR-Selbstcheck"
    ("fr", "gratuit"),             # fr home: "Essai gratuit" / "Démarrez gratuitement"
])
def test_home_langs(client: TestClient, lang, marker):
    r = client.get(f"/{lang}/")
    assert r.status_code == 200, r.text
    html = r.text
    assert html_lang(html) == lang, f"<html lang> 应为 {lang}，实际 {html_lang(html)}"
    assert "CrossAIO" in html
    assert marker in html, f"/{lang}/ 缺少语言特征词 {marker!r}"
    residue = cjk_residue(html)
    assert not residue, f"/{lang}/ 删除切换器块后仍有中文残留: {''.join(residue[:20])}"


# ---------------------------------------------------------------------------
# 2. 定价 + 工作台 × 3 语言
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("lang", ["en", "de", "fr"])
@pytest.mark.parametrize("page", ["pricing", "app"])
def test_pricing_app_langs(client: TestClient, lang, page):
    r = client.get(f"/{lang}/{page}")
    assert r.status_code == 200, r.text
    assert html_lang(r.text) == lang, f"/{lang}/{page} lang 属性错误: {html_lang(r.text)}"
    residue = cjk_residue(r.text)
    assert not residue, f"/{lang}/{page} 中文残留: {''.join(residue[:20])}"


# ---------------------------------------------------------------------------
# 3. GPSR 子页 × 3 语言抽查（6 条）
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("url,lang", [
    ("/en/gpsr-check", "en"),
    ("/en/gpsr-check/platforms", "en"),
    ("/de/gpsr-check/features", "de"),
    ("/de/gpsr-check/pricing", "de"),
    ("/fr/gpsr-check/faq", "fr"),
    ("/fr/gpsr-check/compare", "fr"),
])
def test_gpsr_sample_langs(client: TestClient, url, lang):
    r = client.get(url)
    assert r.status_code == 200, r.text
    assert html_lang(r.text) == lang, f"{url} lang 属性错误: {html_lang(r.text)}"
    residue = cjk_residue(r.text)
    assert not residue, f"{url} 中文残留: {''.join(residue[:20])}"


# ---------------------------------------------------------------------------
# 4. zh 路由回归
# ---------------------------------------------------------------------------
def test_zh_home_regression(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    assert html_lang(r.text) == "zh-CN"
    assert "免费注册" in r.text
    assert "免费开始" in r.text  # meta description


def test_zh_pricing_regression(client: TestClient):
    r = client.get("/pricing")
    assert r.status_code == 200
    assert html_lang(r.text) == "zh-CN"
    assert "€29" in r.text


def test_zh_gpsr_regression(client: TestClient):
    r = client.get("/gpsr-check")
    assert r.status_code == 200
    assert html_lang(r.text) == "zh-CN"
    assert CJK_RE.search(r.text), "zh /gpsr-check 应含中文"


# ---------------------------------------------------------------------------
# 5. sitemap.xml
# ---------------------------------------------------------------------------
def test_sitemap(client: TestClient):
    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    assert "application/xml" in r.headers["content-type"]
    locs = re.findall(r"<loc>(.*?)</loc>", r.text)
    assert len(locs) == 128, f"sitemap 应 128 条 loc（32 路径 × 4 语言），实际 {len(locs)}"
    for loc in locs:
        assert loc.startswith("http://localhost:9000"), f"loc 基址错误: {loc}"


# ---------------------------------------------------------------------------
# 6. hreflang（抽查 /en/pricing）
# ---------------------------------------------------------------------------
def test_hreflang_en_pricing(client: TestClient):
    r = client.get("/en/pricing")
    assert r.status_code == 200
    alternates = re.findall(
        r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', r.text)
    # zh / en / de / fr / x-default = 5 行
    assert len(alternates) == 5, f"/en/pricing 应 5 行 alternate，实际 {len(alternates)}"
    codes = [c for c, _ in alternates]
    assert codes == ["zh", "en", "de", "fr", "x-default"], f"hreflang 顺序错误: {codes}"
    for _, href in alternates:
        assert href.startswith("http://localhost:9000"), f"hreflang href 基址错误: {href}"


# ---------------------------------------------------------------------------
# 7. 切换器（4 个 data-lang + 当前语言 aria-current）
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("url,current", [
    ("/en/pricing", "en"),
    ("/de/", "de"),
    ("/fr/gpsr-check/faq", "fr"),
])
def test_switcher(client: TestClient, url, current):
    r = client.get(url)
    assert r.status_code == 200
    langs = re.findall(r'data-lang="([^"]+)"', r.text)
    assert langs == ["zh", "en", "de", "fr"], f"{url} 切换器 4 链接错误: {langs}"
    # 当前语言必须有 aria-current="page"
    cur = re.search(
        rf'<a [^>]*data-lang="{current}"[^>]*aria-current="page"', r.text)
    assert cur, f"{url} 当前语言 {current} 缺少 aria-current=\"page\""


# ---------------------------------------------------------------------------
# 8. pl / ro 落地页仍 200
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("url", ["/gpsr-check/pl", "/gpsr-check/ro"])
def test_pl_ro_landing(client: TestClient, url):
    r = client.get(url)
    assert r.status_code == 200, f"{url} 应 200"


# ---------------------------------------------------------------------------
# 9. 404 抽查
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("url", ["/en/nope", "/xx/", "/de/does-not-exist"])
def test_404(client: TestClient, url):
    r = client.get(url)
    assert r.status_code == 404, f"{url} 应 404，实际 {r.status_code}"


# ---------------------------------------------------------------------------
# 10. /features/* 与 /rules/{platform} 三语页（任务新增：补全 en/de/fr）
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("url,lang", [
    ("/en/features", "en"),
    ("/en/features/gpsr", "en"),
    ("/de/features/listing-generator", "de"),
    ("/fr/features", "fr"),
    ("/fr/features/ad-copy", "fr"),
    ("/en/rules/otto", "en"),
    ("/de/rules/allegro", "de"),
    ("/fr/rules/cdiscount", "fr"),
    ("/en/rules/bol", "en"),
])
def test_features_rules_langs(client: TestClient, url, lang):
    r = client.get(url)
    assert r.status_code == 200, r.text
    assert html_lang(r.text) == lang, f"{url} lang 属性错误: {html_lang(r.text)}"
    residue = cjk_residue(r.text)
    assert not residue, f"{url} 中文残留: {''.join(residue[:20])}"
    alternates = re.findall(r'<link rel="alternate" hreflang="([^"]+)"', r.text)
    assert alternates == ["zh", "en", "de", "fr", "x-default"], f"{url} hreflang 缺失: {alternates}"
    langs = re.findall(r'data-lang="([^"]+)"', r.text)
    assert langs == ["zh", "en", "de", "fr"], f"{url} 切换器 4 链接错误: {langs}"
    cur = re.search(
        rf'<a [^>]*data-lang="{lang}"[^>]*aria-current="page"', r.text)
    assert cur, f"{url} 当前语言 {lang} 缺少 aria-current=\"page\""


@pytest.mark.parametrize("url,loc", [
    ("/en/features/nope", "/en/features"),
    ("/fr/rules/nope", "/fr/rules"),
])
def test_features_rules_lang_unknown_redirect(client: TestClient, url, loc):
    r = client.get(url, follow_redirects=False)
    assert r.status_code == 302, f"{url} 应 302"
    assert r.headers["location"] == loc, f"{url} 应重定向到 {loc}"
