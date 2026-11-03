"""产品能力落地页 /features/{slug} 测试。"""
import pytest

SLUGS = ["gpsr", "listing-generator", "matrix", "review-rewrite", "ai-service",
         "safety-redline", "inbox", "ad-copy", "listing-watch"]


@pytest.mark.parametrize("slug", SLUGS)
def test_feature_page_renders(client, slug):
    r = client.get(f"/features/{slug}")
    assert r.status_code == 200
    assert "CrossAIO" in r.text
    # 首页同款多页式导航
    assert "产品能力" in r.text and "覆盖平台" in r.text and "免费工具" in r.text
    # H10 架构关键层：痛点/功能拆解/工作原理/定价关联/FAQ/CTA
    assert "工作原理" in r.text and "常见问题" in r.text and "查看完整定价" in r.text
    # 每页含 SVG 产品图
    assert "<svg" in r.text


def test_feature_unknown_redirects(client):
    r = client.get("/features/nope", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/features"


def test_features_index_lists_all(client):
    r = client.get("/features")
    assert r.status_code == 200
    for slug in SLUGS:
        assert f'/features/{slug}"' in r.text


def test_cross_links_between_feature_pages(client):
    r = client.get("/features/gpsr")
    assert r.status_code == 200
    # 其他 5 个功能页交叉链接 + 平台规则页交叉链接
    for slug in ["listing-generator", "matrix", "review-rewrite", "ai-service", "safety-redline"]:
        assert f"/features/{slug}" in r.text
    assert "/rules/allegro" in r.text
    # 导航含 6 平台规则页
    assert "/rules/emag" in r.text and "/rules/bol" in r.text


def test_home_links_to_feature_pages(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    for slug in SLUGS:
        assert f"/features/{slug}" in html
    # 产品能力模块 = 多页式导航：顶部导航条 + 总览链接
    assert "产品能力 · 多页式导航" in html
    assert 'class="fnav"' in html and 'href="/features"' in html
    assert "进入落地页模块" in html


def test_workbench_has_feature_nav_injection(client):
    """工作台 /app 头部注入「产品能力」多页式导航（与全站单一数据源同构）。"""
    r = client.get("/app")
    assert r.status_code == 200
    html = r.text
    # 6 个落地页直达链接 + 总览，全部出现
    for slug in SLUGS:
        assert f"/features/{slug}" in html
    assert "🗂️ 产品能力总览" in html
    # 悬停高亮 CSS 与点击跳转结构齐备
    assert "fnavitem" in html and "fdrop" in html
    assert ".fnavitem:hover .fdrop" in html
    # 占位符已被替换（不再残留）
    assert "<!--FEATURE_NAV-->" not in html


def test_landing_pages_dynamic_assets(client):
    """6 个落地页均含动态素材：扫描光效 mockup / 动画流程图 / 13 平台滚动墙。"""
    r = client.get("/features/gpsr")
    html = r.text
    assert "mk-scan" in html and "mk-dot" in html and "cb-float" in html  # hero 动态化
    assert 'class="fl-line"' in html and "fl-node" in html                # 动画流程图
    assert html.count('class="pm-chip"') == 26                            # 13 平台 × 2 无缝滚动
    assert "cb-marquee" in html and "prefers-reduced-motion" in html      # 动画 + 降级


def test_workbench_nav_switches_panels_in_app(client):
    """工作台导航点击 = 台内切换功能面板（使用功能）；落地页为独立 ↗ 次要入口。"""
    html = client.get("/app").text
    pairs = [("desc", "/features/listing-generator"), ("gpsr", "/features/gpsr"),
             ("cs", "/features/ai-service"), ("inbox", "/features/inbox"),
             ("ad", "/features/ad-copy"), ("review", "/features/review-rewrite"),
             ("watch", "/features/listing-watch"), ("bill", "/pricing")]
    for tab, path in pairs:
        # 主导航是 button：在台内切换面板，而不是直接离开到落地页
        assert f'data-tab="{tab}"' in html, tab
        # 落地页是独立的、带 class=lpjump 的介绍入口
        assert f'class="lpjump" href="{path}"' in html, path
    # 面板切换由 JS activateTab 驱动，而非 window.open / 整页跳转
    assert "activateTab" in html and "window.open" not in html


def test_landing_pages_link_back_to_workbench(client):
    """每个落地页含「🚀 在工作台中使用」按钮，带 ?tab= 深链直达对应面板。"""
    pairs = {"listing-generator": "desc", "gpsr": "gpsr", "ai-service": "cs",
             "inbox": "inbox", "ad-copy": "ad", "review-rewrite": "review",
             "listing-watch": "watch"}
    for slug, tab in pairs.items():
        html = client.get(f"/features/{slug}").text
        assert f'href="/app?tab={tab}"' in html, slug
        assert "在工作台中使用" in html


def test_workbench_every_tab_has_usage_guide(client):
    """工作台每个功能面板内置「❓ 怎么用」使用指南。"""
    html = client.get("/app").text
    assert html.count('details class="howto"') + html.count("details.howto") >= 8
    for tab_id in ("tab-desc", "tab-gpsr", "tab-cs", "tab-inbox",
                   "tab-ad", "tab-review", "tab-watch", "tab-bill"):
        assert f'id="{tab_id}"' in html
    # 每个面板卡片内都嵌了 howto（粗检：8 个 summary + 关键步骤词）
    assert html.count("❓ 怎么用") == 8
    assert "载入演示会话" in html and "开始免费体检" in html
