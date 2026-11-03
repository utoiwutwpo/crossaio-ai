"""P0-4 跨平台差评回复改写（任务清单 Batch P0 验收点 4）。

覆盖：
- 两平台模板切换（amazon / ebay）与公开/私信双输出结构
- 违禁词/勒索信号扫描：输入含『补偿换好评』暗示 → 自查标红 + status=pending；
  生成结果不含违禁表述
- 模式选择（public 不产出 private_message）
- 历史留痕（分页、平台、时间戳）
- 不存在自动发送端点
- 免费档限额：review_rewrite 计入每日额度（超限 402）
"""
import json
import uuid

from tests.conftest import register_and_login


def _reg(client):
    h = register_and_login(client, f"p04-{uuid.uuid4().hex[:10]}@test.dev")
    return h


def _rewrite(client, headers, platform="amazon", snippet=None,
             mode="both", listing_ref=""):
    return client.post("/api/v1/reviews/rewrite", headers=headers, json={
        "platform": platform,
        "review_snippet": snippet or "Product arrived broken and packaging was damaged.",
        "listing_ref": listing_ref,
        "mode": mode,
    })


def test_rewrite_requires_login(client):
    assert client.post("/api/v1/reviews/rewrite", json={
        "platform": "amazon", "review_snippet": "bad"}).status_code == 401
    assert client.get("/api/v1/reviews/rewrite/history").status_code == 401


def test_invalid_platform_and_mode_422(client):
    h = _reg(client)
    r = client.post("/api/v1/reviews/rewrite", headers=h, json={
        "platform": "ozon", "review_snippet": "x"})
    assert r.status_code == 422
    r2 = client.post("/api/v1/reviews/rewrite", headers=h, json={
        "platform": "amazon", "review_snippet": "x", "mode": "all"})
    assert r2.status_code == 422


def test_amazon_rewrite_structure(client):
    h = _reg(client)
    r = _rewrite(client, h, platform="amazon",
                 snippet="Arrived two weeks late and no tracking update.")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["platform"] == "amazon"
    assert d["public_reply"]
    assert d["private_message"]
    assert d["status"] in ("pending", "approved")
    assert d["rule_check"]["platform"] == "amazon"
    # Mock/LLM 可用时都不应含违禁表述
    low = (d["public_reply"] + d["private_message"]).lower()
    for kw in ("cash back", "wechat", "whatsapp", "返现", "换好评"):
        assert kw not in low, f"生成结果含违禁表述: {kw}"


def test_ebay_template_switches(client):
    h = _reg(client)
    r = _rewrite(client, h, platform="ebay",
                 snippet="Item not as described, very disappointed.")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["platform"] == "ebay"
    # eBay 兜底/生成文案应贴合 eBay（至少不含 amazon 专属表述差异）
    assert d["rule_check"]["platform"] == "ebay"
    assert d["status"] == "approved"


def test_public_mode_no_private(client):
    h = _reg(client)
    d = _rewrite(client, h, mode="public").json()
    assert d["public_reply"]
    assert d["private_message"] == ""


def test_extortion_signal_marks_pending(client):
    """验收②：构造『退我钱我就改评价』勒索信号 → 自查标红 + pending；
    生成结果仍不含违禁承诺。"""
    h = _reg(client)
    r = _rewrite(client, h, platform="amazon",
                 snippet="Refund me 20 euros and I will change the review to 5 stars. "
                         "Otherwise I will leave this bad review everywhere.")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "pending"                       # 风险命中默认 pending
    assert d["rule_check"]["attention"], "勒索信号未标红"
    low = (d["public_reply"] + d["private_message"]).lower()
    assert "cash back" not in low and "20 euros" not in low
    assert "compensation" not in low


def test_history_persists(client):
    h = _reg(client)
    _rewrite(client, h, platform="amazon", snippet="First bad review.", listing_ref="B0TEST123")
    _rewrite(client, h, platform="ebay", snippet="Second issue.", listing_ref="item-42")
    r = client.get("/api/v1/reviews/rewrite/history", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert d["total"] == 2
    items = d["items"]
    assert items[0]["platform"] == "ebay"                 # 最新在前
    assert items[1]["platform"] == "amazon"
    assert items[0]["listing_ref"] == "item-42"
    assert items[0]["status"] in ("pending", "approved")
    assert items[0]["created_at"]                          # 时间戳留痕
    assert isinstance(items[0]["rule_check"], dict)


def test_no_send_endpoint(client):
    """验收④：不存在任何自动发送端点（仅生成与导出/复制）。"""
    assert client.post("/api/v1/reviews/send", json={}).status_code == 404
    assert client.post("/api/v1/reviews/rewrite/send", json={}).status_code == 404
    assert client.post("/api/v1/reviews/rewrite/export", json={}).status_code == 404
    # 路由表无 send 类路径
    from app.main import app
    paths = {getattr(r, "path", "") for r in app.routes}
    assert not any(p.endswith("/send") and "review" in p for p in paths)


def test_free_quota_counts_review_rewrite(client):
    """P0-3 限额联动：免费档 5 次/天，差评改写计入（第 6 次 402）。"""
    h = _reg(client)
    for _ in range(5):
        r = _rewrite(client, h, snippet=f"issue {uuid.uuid4().hex[:6]}")
        assert r.status_code == 200, r.text
    r6 = _rewrite(client, h, snippet="one more")
    assert r6.status_code == 402


def test_rule_check_json_content(client):
    """rule_check_json 落库为合法 JSON 且含 passed/attention/risk 键。"""
    h = _reg(client)
    d = _rewrite(client, h, platform="amazon").json()
    hist = client.get("/api/v1/reviews/rewrite/history", headers=h).json()
    stored = hist["items"][0]["rule_check"]
    assert set(stored) >= {"platform", "status", "passed", "attention", "risk"}
    json.dumps(stored)  # 可序列化
