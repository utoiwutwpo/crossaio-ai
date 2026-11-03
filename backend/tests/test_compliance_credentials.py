"""工作台平台凭证接入提示：GET /api/v1/compliance/credentials。

覆盖：登录必校验、Amazon 环境变量缺失/就绪两态、eBay 应用级+用户级两层状态、
不回显任何密钥值。
"""
import os
import uuid

import pytest

EMAIL = "cred@test.dev"


@pytest.fixture()
def token(client):
    r = client.post("/api/v1/users/register",
                    json={"email": f"{uuid.uuid4().hex[:8]}{EMAIL}",
                          "password": "Passw0rd!123"})
    return r.json()["access_token"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


def test_credentials_requires_login(client):
    assert client.get("/api/v1/compliance/credentials").status_code == 401


def test_credentials_reports_amazon_missing(client, token):
    """默认环境未配置 CROSSBOT_CRED_AMAZON_* → 未就绪且给出缺失键。"""
    d = client.get("/api/v1/compliance/credentials", headers=_auth(token)).json()
    amz = d["amazon_sp_api"]
    assert amz["ready"] is False
    assert set(amz["missing"]) <= {"CLIENT_ID", "CLIENT_SECRET", "REFRESH_TOKEN"}
    assert amz["env_prefix"] == "CROSSBOT_CRED_AMAZON_"
    assert len(amz["required"]) == 3
    assert all(r["env"].startswith("CROSSBOT_CRED_AMAZON_") for r in amz["required"])
    assert "回填" in amz["unlocks"] or "写回" in amz["unlocks"]


def test_credentials_amazon_ready_with_env(client, token, monkeypatch):
    """三个环境变量齐 → ready=True，且响应不含任何密钥值。"""
    monkeypatch.setenv("CROSSBOT_CRED_AMAZON_CLIENT_ID", "sekrit-id")
    monkeypatch.setenv("CROSSBOT_CRED_AMAZON_CLIENT_SECRET", "sekrit-secret")
    monkeypatch.setenv("CROSSBOT_CRED_AMAZON_REFRESH_TOKEN", "sekrit-token")
    d = client.get("/api/v1/compliance/credentials", headers=_auth(token)).json()
    assert d["amazon_sp_api"]["ready"] is True
    assert d["amazon_sp_api"]["missing"] == []
    body = str(d)
    assert "sekrit" not in body  # 绝不回显密钥值


def test_credentials_ebay_two_layers(client, token):
    """eBay 双层状态诚实上报：应用级凭证与用户级授权分开。"""
    d = client.get("/api/v1/compliance/credentials", headers=_auth(token)).json()
    eb = d["ebay_oauth"]
    assert set(eb) >= {"ready", "app_configured", "user_connected", "unlocks"}
    # 测试环境未配应用凭证也未授权 → 两层都是 False，ready 必为 False
    assert eb["ready"] == (eb["app_configured"] and eb["user_connected"])
    assert eb["connect_url"] == "/api/v1/ebay/auth-url"


def test_credentials_all_ready_flag_consistent(client, token, monkeypatch):
    """all_ready = 13 平台全部就绪（含 eBay OAuth 与各自助凭证）。"""
    d = client.get("/api/v1/compliance/credentials", headers=_auth(token)).json()
    assert d["all_ready"] == all(p["ready"] for p in d["platforms"].values())
    # 未接入任何凭证时 all_ready 必为 False（不虚报）
    assert d["all_ready"] is False


# ---- 13 平台商家自助接入（粘贴凭证 → AES-256 加密封存） ----

def test_credentials_cover_all_13_platforms(client, token):
    from app.experts.platform_credentials import PLATFORM_CRED_REGISTRY
    d = client.get("/api/v1/compliance/credentials", headers=_auth(token)).json()
    assert set(d["platforms"]) == set(PLATFORM_CRED_REGISTRY)
    assert len(d["platforms"]) == 13
    for slug, p in d["platforms"].items():
        assert p["guide"]["apply_url"].startswith("https://")
        assert p["unlocks"]
        if p["oauth"]:
            assert slug == "ebay"
        else:
            assert p["guide"]["fields"], f"{slug} 粘贴平台必须有字段定义"


def test_self_service_save_and_ready(client, token):
    """Kaufland 自助粘贴 Client-Key/Secret-Key → ready(source=self)，不回显明文。"""
    h = _auth(token)
    body = {"credentials": {"client_key": "ka-client-123",
                            "secret_key": "ka-secret-456"}}
    r = client.post("/api/v1/compliance/credentials/kaufland",
                    headers=h, json=body)
    assert r.status_code == 200 and r.json()["ok"] is True
    # 明文密钥绝不出现在任何响应里
    assert "ka-secret-456" not in str(r.json())
    d = client.get("/api/v1/compliance/credentials", headers=h).json()
    ka = d["platforms"]["kaufland"]
    assert ka["ready"] is True and ka["connected"] is True
    assert ka["source"] == "self"
    assert "ka-secret-456" not in str(d)


def test_self_service_missing_field_rejected(client, token):
    """缺字段 → 422 且指出缺失字段名。"""
    r = client.post("/api/v1/compliance/credentials/kaufland",
                    headers=_auth(token),
                    json={"credentials": {"client_key": "only-one"}})
    assert r.status_code == 422
    assert "secret_key" in r.json()["detail"]


def test_self_service_unknown_platform_404(client, token):
    r = client.post("/api/v1/compliance/credentials/nope",
                    headers=_auth(token), json={"credentials": {"a": "b"}})
    assert r.status_code == 404


def test_ebay_not_pasteable_oauth_only(client, token):
    """eBay 走 OAuth 授权流程，拒绝粘贴凭证。"""
    r = client.post("/api/v1/compliance/credentials/ebay",
                    headers=_auth(token),
                    json={"credentials": {"client_id": "x"}})
    assert r.status_code == 400
    assert "OAuth" in r.json()["detail"]


def test_self_service_delete_disconnects(client, token):
    h = _auth(token)
    client.post("/api/v1/compliance/credentials/kaufland", headers=h,
                json={"credentials": {"client_key": "k", "secret_key": "s"}})
    r = client.delete("/api/v1/compliance/credentials/kaufland", headers=h)
    assert r.status_code == 200
    d = client.get("/api/v1/compliance/credentials", headers=h).json()
    assert d["platforms"]["kaufland"]["ready"] is False
    # 重复删除 → 404
    assert client.delete("/api/v1/compliance/credentials/kaufland",
                         headers=h).status_code == 404


def test_self_service_upsert_overwrites(client, token):
    """同平台重复保存 = 更新而非新增（unique user+platform）。"""
    h = _auth(token)
    for secret in ("first", "second"):
        r = client.post("/api/v1/compliance/credentials/kaufland",
                        headers=h,
                        json={"credentials": {"client_key": "k",
                                              "secret_key": secret}})
        assert r.status_code == 200
    d = client.get("/api/v1/compliance/credentials", headers=h).json()
    assert d["platforms"]["kaufland"]["connected"] is True
