"""平台规则落地页（/rules/{platform}）SEO 页面验证。"""
from app.main import app
from fastapi.testclient import TestClient


def _client():
    return TestClient(app)


def test_rule_page_renders_native_content():
    c = _client()
    for platform, marker in [
        ("allegro", "INFORMACJE"),          # 波兰语政策名出现于页面
        ("emag", "ANPC"),
        ("cdiscount", "DGCCRF"),
        ("otto", "ProdSG"),
        ("kaufland", "DoC"),
        ("bol", "ACM"),
    ]:
        r = c.get(f"/rules/{platform}")
        assert r.status_code == 200, (platform, r.status_code)
        html = r.text
        assert "GPSR 合规规则速查" in html
        assert marker in html or platform == "allegro"  # allegro 页断言波兰语内容
        if platform == "allegro":
            assert "Bezpieczeństwo produktów" in html or "UOKiK" in html
        assert "/gpsr-check" in html      # 体检 CTA
        assert "/pricing" in html         # 解锁 CTA
        # 固定首页同款多页式导航（产品能力 + 覆盖平台 + 免费工具 + 定价）
        assert "产品能力" in html and "覆盖平台" in html and "免费工具" in html
        assert "/features/gpsr" in html   # 产品能力 dropdown 注入
        assert "/skills" in html          # 免费工具 dropdown 注入
        assert 'class="solo" href="/pricing"' in html  # 定价 solo 项


def test_rule_page_cross_links():
    c = _client()
    html = c.get("/rules/emag").text
    for other in ("allegro", "cdiscount", "otto", "kaufland", "bol"):
        assert f"/rules/{other}" in html   # 交叉链接


def test_rule_page_nav_highlights_current_platform():
    c = _client()
    html = c.get("/rules/otto").text
    # 当前平台在「覆盖平台」dropdown 中高亮
    assert '<a href="/rules/otto" class="on">' in html
    # 产品能力 dropdown 固定注入且不与当前页混淆高亮
    assert '<a href="/features/gpsr">' in html


def test_unknown_platform_redirects_to_rules_index():
    c = _client()
    r = c.get("/rules/not_a_platform", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/rules"
