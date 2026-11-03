"""GPSR 体检中心多页化（6 个落地页）回归测试。"""
SLUGS = ["home", "features", "platforms", "compare", "pricing", "faq"]
PATHS = {"home": "/gpsr-check", "features": "/gpsr-check/features",
         "platforms": "/gpsr-check/platforms", "compare": "/gpsr-check/compare",
         "pricing": "/gpsr-check/pricing", "faq": "/gpsr-check/faq"}


def _get(client, slug):
    r = client.get(PATHS[slug])
    assert r.status_code == 200, (slug, r.status_code)
    return r.text


def test_all_pages_render_with_site_nav(client):
    """6 页全部渲染，且每页固定首页同款多页式导航。"""
    for slug in SLUGS:
        html = _get(client, slug)
        # 共享导航（首页同款）：三大 dropdown + 定价 solo + 工作台/注册按钮
        assert ">产品能力</a>" in html and "免费工具" in html, slug
        assert '/features/gpsr' in html and 'class="solo" href="/pricing"' in html, slug
        assert "登录" in html and "免费注册" in html, slug
        # 本地胶囊条：6 个分页链接齐备，当前页唯一高亮
        assert 'class="gnav"' in html, slug
        assert html.count('class="glink on"') == 1, slug
        for s in SLUGS:
            assert PATHS[s] in html, (slug, s)


def test_home_page_form_and_js(client):
    """主页保留免注册体检表单 + AI 对话动画 + 轨道动画。"""
    html = _get(client, "home")
    for frag in ('id="g_asin"', 'id="g_name"', 'id="g_kw"', 'id="g_platform"',
                 'id="btnGo"', "gpsr/check-guest", "chatMsgs", "class=\"orbit o1\"",
                 "aiact-banner", "30 秒 GPSR 合规体检"):
        assert frag in html, frag
    # 分页入口卡指向新落地页
    assert 'href="/gpsr-check/platforms"' in html
    assert 'href="/gpsr-check/features"' in html


def test_features_page_dynamic_assets(client):
    """功能拆解页：扫描光效 mockup + 动画流程图 + 5 个板块。"""
    html = _get(client, "features")
    assert "mk-scan" in html and "mk-dot" in html          # hero mockup 动效
    assert 'class="fl-line"' in html and "fl-node" in html  # 动画流程图
    assert html.count('class="fblock"') == 5
    assert 'id="p1"' in html and 'id="p5"' in html


def test_platforms_page_marquee_and_marks(client):
    """平台覆盖页：13 平台滚动墙 + 12 张字标卡。"""
    html = _get(client, "platforms")
    assert html.count('class="pm-chip"') == 26              # 13 × 2 无缝滚动
    assert 'aria-label="Amazon"' in html and 'aria-label="Kaufland"' in html
    assert html.count('class="site"') == 12
    assert 'href="/rules"' in html


def test_compare_and_pricing_pages(client):
    html = _get(client, "compare")
    assert "Marqetir" in html and "nowin" in html and "win" in html
    assert "€159+" in html and "No Shopify required" in html

    html = _get(client, "pricing")
    assert "€29" in html and 'class="ptier hot"' in html
    assert "€500+" in html and 'href="/pricing"' in html
    assert "10 年" in html  # 技术文件存档


def test_faq_page_and_language_variants_intact(client):
    """FAQ 6 条齐备；/pl 与 /ro 语言变体不受影响。"""
    html = _get(client, "faq")
    assert html.count("<details>") == 6
    assert "EU 2023/988" in html
    for path in ("/gpsr-check/pl", "/gpsr-check/ro"):
        assert client.get(path).status_code == 200


def test_unknown_subpage_falls_through(client):
    """未注册 slug 落到 404（显式路由，不吞语言变体路径）。"""
    assert client.get("/gpsr-check/nope").status_code == 404
