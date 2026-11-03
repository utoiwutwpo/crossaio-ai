"""P0-3 三层透明定价与免费档限额（任务清单 Batch P0 验收点 3）。

覆盖：
- GET /billing/usage 分维度用量（daily/monthly/features/platforms/currency）
- usage 随生成调用增长、feature 分维度计数
- 平台接入配额计数
- 订阅漏斗三事件（plan_view / subscribe_click / upgrade_cta_shown）可上报
- 免费档超限 402 + 升级引导（with_compliance 兼容既有调用）
"""
import uuid

from tests.conftest import register_and_login


def _reg(client):
    h = register_and_login(client, f"p03-{uuid.uuid4().hex[:10]}@test.dev")
    return h


def test_usage_requires_login(client):
    assert client.get("/api/v1/billing/usage").status_code == 401


def test_usage_structure(client):
    h = _reg(client)
    r = client.get("/api/v1/billing/usage", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["plan"] == "free"
    assert d["currency"] == "EUR"
    assert set(d["daily"]) == {"used", "limit"}
    assert set(d["monthly"]) == {"used", "limit"}
    assert isinstance(d["features"], list)
    assert set(d["platforms"]) == {"used", "limit", "unlimited"}
    # 免费档：daily_limit=5，features 至少含 product_desc
    assert d["daily"]["limit"] == 5
    assert any(f["feature"] == "product_desc" for f in d["features"])


def test_usage_grows_with_generation(client):
    h = _reg(client)
    d0 = client.get("/api/v1/billing/usage", headers=h).json()
    assert d0["daily"]["used"] == 0

    r = client.post("/api/v1/products/descriptions/generate", headers=h, json={
        "product_name": "LED Desk Lamp", "keywords": ["lamp", "desk"],
        "platform": "amazon", "language": "en",
    })
    assert r.status_code == 200, r.text

    d1 = client.get("/api/v1/billing/usage", headers=h).json()
    assert d1["daily"]["used"] == 1
    pd = next(f for f in d1["features"] if f["feature"] == "product_desc")
    assert pd["used_today"] == 1
    assert pd["used_month"] == 1


def test_usage_platform_quota_counts_credentials(client):
    h = _reg(client)
    d0 = client.get("/api/v1/billing/usage", headers=h).json()
    assert d0["platforms"]["used"] == 0
    assert d0["platforms"]["limit"] == 1   # 免费档 1 平台

    r = client.post("/api/v1/compliance/credentials/kaufland", headers=h,
                    json={"credentials": {"client_key": "k",
                                          "secret_key": "s"}})
    assert r.status_code == 200, r.text

    d1 = client.get("/api/v1/billing/usage", headers=h).json()
    assert d1["platforms"]["used"] == 1
    assert d1["platforms"]["unlimited"] is False


def test_free_plan_over_limit_402(client):
    h = _reg(client)
    for _ in range(5):   # 免费档每天 5 次
        r = client.post("/api/v1/products/descriptions/generate", headers=h, json={
            "product_name": f"Item {uuid.uuid4().hex[:6]}", "keywords": ["toy"],
            "platform": "amazon", "language": "en",
        })
        assert r.status_code == 200, r.text
    r6 = client.post("/api/v1/products/descriptions/generate", headers=h, json={
        "product_name": "One More", "keywords": ["toy"],
        "platform": "amazon", "language": "en",
    })
    assert r6.status_code == 402
    assert "升级" in r6.json()["detail"] or "额度" in r6.json()["detail"]


def test_subscription_funnel_events_accepted(client):
    """订阅漏斗三事件可上报（公开埋点端点）；未知事件 422。"""
    for ev in ("plan_view", "subscribe_click", "upgrade_cta_shown"):
        r = client.post("/api/v1/analytics/track", json={
            "event_type": ev, "meta": {"plan": "starter"} if "click" in ev else {},
        })
        assert r.status_code == 200, f"{ev}: {r.text}"
        assert r.json()["ok"] is True

    bad = client.post("/api/v1/analytics/track",
                      json={"event_type": "not_a_real_event"})
    assert bad.status_code == 422


def test_plans_page_prices_match_backend(client):
    """核对对齐：前端定价 = 后端 PLANS（验收①核心）。

    后端为权威（USD）；前端已统一为 $。此处断言后端 plans 数据完整性
    与货币字段，前端静态页由页面回归测试覆盖。
    """
    plans = client.get("/api/v1/billing/plans").json()
    assert plans["free"]["monthly_price_usd"] == 0
    assert plans["starter"]["monthly_price_usd"] == 29
    assert plans["pro"]["monthly_price_usd"] == 49
    assert plans["business"]["monthly_price_usd"] == 149
    # 限额谓词齐全（P0-3 验收②前置）
    for p in ("free", "starter", "pro", "business"):
        cfg = plans[p]
        assert "daily_limit" in cfg and "monthly_calls" in cfg
        assert "platforms" in cfg and "features" in cfg
