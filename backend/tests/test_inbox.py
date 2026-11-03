"""跨平台统一收件箱：聚合视图 + 合规客服回复（组合层在出站消息生效）。"""
import pytest


def _auth(client, email):
    r = client.post("/api/v1/users/register", json={
        "email": email, "password": "Passw0rd!123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_inbox_seed_and_list(client):
    h = _auth(client, "inbox1@test.com")
    s = client.post("/api/v1/inbox/conversations/seed-demo", headers=h)
    assert s.status_code == 200, s.text
    assert s.json()["seeded"] >= 4 and s.json()["demo"] is True

    lst = client.get("/api/v1/inbox/conversations", headers=h).json()
    assert lst["total"] >= 4
    # 平台分布覆盖多个平台
    assert len(lst["platform_distribution"]) >= 3


def test_inbox_filter_by_platform(client):
    h = _auth(client, "inbox2@test.com")
    client.post("/api/v1/inbox/conversations/seed-demo", headers=h)
    lst = client.get("/api/v1/inbox/conversations?platform=allegro", headers=h).json()
    assert lst["total"] >= 1
    assert all(c["platform"] == "allegro" for c in lst["items"])


def test_reply_applies_combination_layer(client):
    h = _auth(client, "inbox3@test.com")
    # 新建一个 eBay 会话，内容是安全事件（充电器起火伤人）
    c = client.post("/api/v1/inbox/conversations", headers=h, json={
        "platform": "ebay",
        "buyer_id": "buyer_x",
        "subject": "安全事件",
        "first_message": "The charger caught fire and my son was hurt!",
    }).json()
    conv_id = c["id"]

    det = client.get(f"/api/v1/inbox/conversations/{conv_id}", headers=h).json()
    assert det["conversation"]["platform"] == "ebay"
    assert len(det["messages"]) == 1

    # 回复该安全事件 → 应触发合规优先回复（gpsr_incident=True）+ Art.50 披露
    rep = client.post(f"/api/v1/inbox/conversations/{conv_id}/reply", headers=h,
                      json={"message": "The charger caught fire and my son was hurt!"}).json()
    assert rep["gpsr_incident"] is True
    assert rep["ai_act_disclosure"]  # Art.50 当地语言披露已注入
    assert "Safety Gate" in rep["reply"] or "15" in rep["reply"]

    # 会话消息流现在有：买家原消息 + 出站回复
    det2 = client.get(f"/api/v1/inbox/conversations/{conv_id}", headers=h).json()
    assert len(det2["messages"]) == 3  # 原消息(来自create) + 买家消息(reply内) + 出站(reply内)? 见下
    out_msgs = [m for m in det2["messages"] if m["direction"] == "outgoing"]
    assert len(out_msgs) == 1 and out_msgs[0]["gpsr_incident"] is True
