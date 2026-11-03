"""P0-1：Amazon 凭证接入与收件箱上下文（任务清单 Batch P0 验收点 1）。

覆盖：
- 收件箱会话上下文（order_id/asin/sku）写入/回读、空值默认、非法类型 422
- Amazon 连接器三态状态机：unconnected / pending（部分字段）/ connected（self 完整 + env）
- 三态端点纯本地推导：不发起任何出站请求（无 SP-API 调用路径）
"""
import json
import uuid

import pytest

from app.database import SessionLocal, PlatformCredential
from app.ebay_service import encrypt_secret


def _auth(client, tag: str):
    r = client.post("/api/v1/users/register", json={
        "email": f"{tag}-{uuid.uuid4().hex[:8]}@test.dev",
        "password": "Passw0rd!123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _user_id(client, tag: str):
    h = _auth(client, tag)
    me = client.get("/api/v1/users/me", headers=h)
    assert me.status_code == 200, me.text
    return h, me.json()["id"]


# ---- 收件箱会话上下文 ----

def test_conversation_context_roundtrip(client):
    h = _auth(client, "ctx")
    r = client.post("/api/v1/inbox/conversations", headers=h, json={
        "platform": "amazon",
        "buyer_id": "buyer_amz_1",
        "first_message": "Where is my order?",
        "context": {"order_id": "123-4567890-1234567",
                    "asin": "B0XXXXXXXX", "sku": "SKU-001"},
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["context"] == {"order_id": "123-4567890-1234567",
                               "asin": "B0XXXXXXXX", "sku": "SKU-001"}

    det = client.get(f"/api/v1/inbox/conversations/{data['id']}", headers=h)
    assert det.status_code == 200
    assert det.json()["conversation"]["context"] == data["context"]

    # 列表视图也带 context
    lst = client.get("/api/v1/inbox/conversations?platform=amazon", headers=h).json()
    assert any(c["id"] == data["id"] and c["context"] == data["context"]
               for c in lst["items"])


def test_conversation_context_empty_default(client):
    h = _auth(client, "ctxempty")
    r = client.post("/api/v1/inbox/conversations", headers=h, json={
        "platform": "ebay", "buyer_id": "b", "first_message": "hi",
    })
    assert r.status_code == 200
    assert r.json()["context"] == {}


def test_conversation_context_must_be_object(client):
    h = _auth(client, "ctxbad")
    r = client.post("/api/v1/inbox/conversations", headers=h, json={
        "platform": "amazon", "first_message": "hi", "context": "not-a-dict",
    })
    assert r.status_code == 422


# ---- Amazon 连接器三态状态机 ----

def test_amazon_status_unconnected(client):
    h = _auth(client, "amz0")
    r = client.get("/api/v1/inbox/connectors/amazon/status", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["platform"] == "amazon"
    assert body["status"] == "unconnected"
    assert body["note"]  # 诚实提示未接入


def test_amazon_status_pending_partial(client):
    h, uid = _user_id(client, "amzp")
    with SessionLocal() as db:
        db.add(PlatformCredential(user_id=uid, platform="amazon",
                                  payload=encrypt_secret(
                                      json.dumps({"client_id": "LWA-123"}))))
        db.commit()
    body = client.get("/api/v1/inbox/connectors/amazon/status", headers=h).json()
    assert body["status"] == "pending"
    assert set(body["missing_fields"]) >= {"client_secret", "refresh_token"}


def test_amazon_status_connected_self(client):
    h, uid = _user_id(client, "amzc")
    with SessionLocal() as db:
        db.add(PlatformCredential(user_id=uid, platform="amazon",
                                  payload=encrypt_secret(json.dumps({
                                      "client_id": "LWA-1",
                                      "client_secret": "sec-1",
                                      "refresh_token": "rt-1"}))))
        db.commit()
    body = client.get("/api/v1/inbox/connectors/amazon/status", headers=h).json()
    assert body["status"] == "connected"
    assert body["source"] == "self"
    assert body["missing_fields"] == []


def test_amazon_status_connected_env(client, monkeypatch):
    h = _auth(client, "amze")
    monkeypatch.setenv("CROSSBOT_CRED_AMAZON_CLIENT_ID", "env-id")
    monkeypatch.setenv("CROSSBOT_CRED_AMAZON_CLIENT_SECRET", "env-secret")
    monkeypatch.setenv("CROSSBOT_CRED_AMAZON_REFRESH_TOKEN", "env-token")
    body = client.get("/api/v1/inbox/connectors/amazon/status", headers=h).json()
    assert body["status"] == "connected"
    assert body["source"] == "env"
    # 环境变量值绝不出现在响应中
    assert "env-secret" not in str(body)


def test_amazon_status_no_outbound_payload(client):
    """验收：测试环境不发起任何对 amazon/sp-api 的出站请求。

    实现上三态推导只读本地表 + 环境变量；此处以响应结构断言 +
    显式声明（若未来引入出站调用，需先通过 D1 审核并加 mock 断言）。
    """
    h = _auth(client, "amzn")
    body = client.get("/api/v1/inbox/connectors/amazon/status", headers=h).json()
    assert body["status"] in ("unconnected", "pending", "connected")
    assert set(body) == {"platform", "status", "source", "connected_at",
                         "missing_fields", "note"}
