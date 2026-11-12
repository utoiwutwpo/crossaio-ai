"""13 平台授权的接口级端到端测试：保存 → 矩阵 → 校验 → 解绑。"""
import uuid

from fastapi.testclient import TestClient

from tests.conftest import register_and_login

BASE = "/api/v1/platform-auth"

ALLEGRO = {"client_id": "allegro-client-abc123",
           "client_secret": "allegro-secret-456def"}


def _auth(client):
    # 每个测试独立账号，避免共用测试库时邮箱冲突
    return register_and_login(client, f"authloop-{uuid.uuid4().hex[:8]}@example.com")


def test_matrix_requires_login(client: TestClient):
    assert client.get(f"{BASE}/matrix").status_code == 401


def test_save_then_matrix_then_delete(client: TestClient):
    h = _auth(client)

    r = client.post(f"{BASE}/allegro/credentials", json=ALLEGRO, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "connected"
    assert body["missing_fields"] == []
    assert body["unknown_fields"] == []

    m = client.get(f"{BASE}/matrix", headers=h).json()
    row = next(x for x in m["items"] if x["platform"] == "allegro")
    assert row["status"] == "connected"
    assert set(row["status_text"].keys()) == {"en", "de", "fr", "pl"}
    assert "Połączono" in row["status_text"]["pl"]
    assert set(row["text"].keys()) == {"en", "de", "fr", "pl"}

    d = client.delete(f"{BASE}/allegro/credentials", headers=h).json()
    assert d["ok"] is True
    m2 = client.get(f"{BASE}/matrix", headers=h).json()
    row2 = next(x for x in m2["items"] if x["platform"] == "allegro")
    assert row2["status"] == "unconnected"


def test_credential_never_returns_plaintext(client: TestClient):
    h = _auth(client)
    client.post(f"{BASE}/allegro/credentials", json=ALLEGRO, headers=h)
    info = client.get(f"{BASE}/allegro/credential", headers=h).json()
    raw = str(info)
    assert "allegro-secret-456def" not in raw
    assert info["fields"]["client_secret"]["set"] is True
    assert info["fields"]["client_secret"]["length"] == len(ALLEGRO["client_secret"])


def test_verify_endpoint_reports_connected(client: TestClient):
    h = _auth(client)
    client.post(f"{BASE}/bol/credentials",
                json={"client_id": "bol-client-1234",
                      "client_secret": "bol-secret-5678"}, headers=h)
    r = client.post(f"{BASE}/bol/verify", headers=h).json()
    assert r["status"] == "connected"
    assert r["live"] is None


def test_placeholder_is_flagged_not_connected(client: TestClient):
    h = _auth(client)
    r = client.post(f"{BASE}/emag/credentials",
                    json={"api_key": "your_api_key_here"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "pending"
    assert any("占位符" in c["reason"] for c in r.json()["checks"])


def test_unknown_platform_rejected(client: TestClient):
    h = _auth(client)
    assert client.post(f"{BASE}/ozon/credentials",
                       json={"api_key": "x123456789"}, headers=h).status_code == 404


def test_unconfirmed_platform_has_no_authorize_url(client: TestClient):
    h = _auth(client)
    r = client.get(f"{BASE}/tiktok/authorize-url",
                   params={"redirect_uri": "https://example.com/cb"}, headers=h)
    assert r.status_code == 422
    # 已存 Client ID 后，confirmed 平台才给出跳转地址
    client.post(f"{BASE}/allegro/credentials", json=ALLEGRO, headers=h)
    r2 = client.get(f"{BASE}/allegro/authorize-url",
                    params={"redirect_uri": "https://example.com/cb"}, headers=h)
    assert r2.status_code == 200
    assert "state=" in r2.json()["authorize_url"]
