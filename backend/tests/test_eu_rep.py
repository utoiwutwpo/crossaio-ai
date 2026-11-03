"""欧代台账 + 合规块内嵌欧代 的接口与单元验证。"""
import os
from unittest import mock

import pytest


# ---------------- 接口层（经 test client） ----------------
def test_eu_rep_crud_and_default(client):
    h = _auth(client, "eurep1@test.com")
    # 新增一条（首条应为默认）
    r = client.post("/api/v1/eu-reps", headers=h, json={
        "company_name": "EU Compliance Ltd",
        "address": "123 Rue de la Loi, 1000 Brussels, BE",
        "email": "rep@eucompliance.eu",
    })
    assert r.status_code == 200, r.text
    rep = r.json()
    assert rep["company_name"] == "EU Compliance Ltd"
    assert rep["is_default"] is True
    rep_id = rep["id"]

    # 再加一条，默认仍是第一条（除非显式设为默认）
    r2 = client.post("/api/v1/eu-reps", headers=h, json={
        "company_name": "Second Rep GmbH", "address": "Berlin DE",
    })
    assert r2.status_code == 200
    assert r2.json()["is_default"] is False

    # 列表返回两条，默认排第一
    lst = client.get("/api/v1/eu-reps", headers=h).json()
    assert len(lst) == 2 and lst[0]["id"] == rep_id

    # 设第二条为默认
    r3 = client.post("/api/v1/eu-reps/default", headers=h, json={"rep_id": r2.json()["id"]})
    assert r3.status_code == 200 and r3.json()["is_default"] is True
    lst2 = client.get("/api/v1/eu-reps", headers=h).json()
    assert lst2[0]["id"] == r2.json()["id"] and lst2[1]["is_default"] is False

    # 删除默认 → 剩余第一条自动提升为默认
    client.delete(f"/api/v1/eu-reps/{r2.json()['id']}", headers=h)
    lst3 = client.get("/api/v1/eu-reps", headers=h).json()
    assert len(lst3) == 1 and lst3[0]["is_default"] is True


def test_gpsr_check_embeds_real_rep():
    """单元层：传入欧代单行文本，gpsr.check 的合规块内嵌真实欧代、不再用占位符。"""
    from app.experts import gpsr, eu_rep
    line = eu_rep.render_rep_line({
        "company_name": "Acme EU Rep", "address": "Paris FR",
        "email": "hello@acme.eu"})
    rep = gpsr.check("Kids Wooden Toy Train", ["toy", "wooden", "children"],
                     "amazon", eu_rep_line=line)
    block = rep["gpsr_block"]
    assert "Acme EU Rep" in block
    assert "[欧代公司名称]" not in block


def test_backfill_embeds_rep_and_ready_to_send(client):
    h = _auth(client, "eurep3@test.com")
    client.post("/api/v1/eu-reps", headers=h, json={
        "company_name": "RepCo", "address": "Madrid ES", "email": "x@rep.co",
    })
    # 无凭证 → credentials_required，但 payload 内 gpsr_block 应含欧代
    r = client.post("/api/v1/products/gpsr/backfill", headers=h, json={
        "product_name": "Bluetooth Speaker", "keywords": ["bluetooth", "speaker"],
        "platform": "ebay",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert "RepCo" in body["gpsr_block"]
    # submit 无凭证 → credentials_required
    r2 = client.post("/api/v1/products/gpsr/backfill/submit?dry_run=true",
                    headers=h, json={
                        "product_name": "Bluetooth Speaker",
                        "keywords": ["bluetooth", "speaker"], "platform": "ebay"})
    assert r2.status_code == 200 and r2.json()["status"] == "credentials_required"


# ---------------- 真实写回路径（mock 网络） ----------------
def test_real_submit_ebay_calls_requests(client):
    creds = {"oauth_token": "TOK", "sku": "SKU123"}
    payload = {"gpsr_block": "BLOCKTEXT"}
    fake_resp = mock.Mock()
    fake_resp.status_code = 204
    fake_resp.text = ""
    with mock.patch("app.experts.listing_backfill.requests.request",
                    return_value=fake_resp) as m_REQ:
        from app.experts import listing_backfill
        resp = listing_backfill.real_submit("ebay", payload, creds)
    assert resp.status_code == 204
    # 验证了真实 HTTP 调用确实被发起（method/url/headers/body）
    args, kwargs = m_REQ.call_args
    assert args[0] == "PUT"
    assert "api.ebay.com" in args[1]
    assert kwargs["headers"]["Authorization"] == "Bearer TOK"
    assert kwargs["json"]["product"]["description"] == "BLOCKTEXT"


def test_real_submit_amazon_signs_with_sigv4(client):
    creds = {"aws_key": "AKID", "aws_secret": "SECRET", "refresh_token": "RT",
             "client_id": "CID", "client_secret": "SEC", "sku": "SKU9",
             "region": "eu-west-1"}
    payload = {"gpsr_block": "BLOCK"}
    fake_token = mock.Mock(); fake_token.raise_for_status = lambda: None
    fake_token.json = lambda: {"access_token": "LWA_TOKEN"}
    fake_submit = mock.Mock(); fake_submit.status_code = 200; fake_submit.text = "ok"
    with mock.patch("app.experts.listing_backfill.requests.post",
                    return_value=fake_token) as m_post, \
         mock.patch("app.experts.listing_backfill.requests.request",
                    return_value=fake_submit) as m_req:
        from app.experts import listing_backfill
        resp = listing_backfill.real_submit("amazon", payload, creds)
    # LWA token 获取
    m_post.assert_called_once()
    # 真实 SP-API 请求带 SigV4 签名头
    args, kwargs = m_req.call_args
    assert args[0] == "PATCH"
    assert "sellingpartnerapi-eu.amazon.com" in args[1]
    assert "AWS4-HMAC-SHA256" in kwargs["headers"]["Authorization"]
    assert kwargs["headers"]["x-amz-access-token"] == "LWA_TOKEN"
    assert resp.status_code == 200


def _auth(client, email):
    r = client.post("/api/v1/users/register", json={
        "email": email, "password": "Passw0rd!123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
