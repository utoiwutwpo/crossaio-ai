"""统一收件箱连接器骨架：连接器状态 / 批量导入 / 校验 / Kaufland 种子。"""
from tests.conftest import register_and_login


def _auth(client, email):
    return register_and_login(client, email)


def test_connectors_status_honest(client):
    """连接器状态必须诚实：eBay=api，欧洲三平台=manual + 凭证环境变量名。"""
    h = _auth(client, "conn1@test.com")
    r = client.get("/api/v1/inbox/connectors", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ebay"]["sync_mode"] == "api"
    plats = {c["platform"]: c for c in d["connectors"]}
    assert {"allegro", "otto", "kaufland"} <= set(plats)
    for key in ("allegro", "otto", "kaufland"):
        c = plats[key]
        assert c["sync_mode"] == "manual", "无凭证时必须如实标注 manual"
        assert c["credentials_ready"] is False
        assert c["required_env"], "必须给出凭证环境变量名（真实对接路径）"
        assert c["api_basis"]
        assert c["import_template"]["messages"]


def test_connector_import_allegro(client):
    h = _auth(client, "conn2@test.com")
    r = client.post("/api/v1/inbox/connectors/allegro/import", headers=h, json={
        "items": [
            {"buyer_id": "allegro_klient_01", "subject": "Zwrot",
             "messages": ["Czy mogę zwrócić towar?", "Jak długo trwa zwrot?"]},
            {"subject": "Dostawa", "messages": ["Kiedy paczka?"]},  # buyer_id 缺省自动生成
        ]})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["imported"] == 2 and d["platform"] == "allegro"

    # 导入的会话进入统一收件箱，可按平台过滤
    lst = client.get("/api/v1/inbox/conversations?platform=allegro", headers=h).json()
    assert lst["total"] >= 2
    # 首条会话：2 条消息 + 未读计数
    conv_id = d["items"][0]["id"]
    det = client.get(f"/api/v1/inbox/conversations/{conv_id}", headers=h).json()
    assert len(det["messages"]) == 2
    assert all(m["direction"] == "incoming" for m in det["messages"])


def test_connector_import_reply_uses_combo_workflow(client):
    """导入的会话回复同样过组合工作流（Art.50 + GPSR）。"""
    h = _auth(client, "conn3@test.com")
    imp = client.post("/api/v1/inbox/connectors/kaufland/import", headers=h, json={
        "items": [{"buyer_id": "k1", "subject": "Sicherheit",
                   "messages": ["Der Akku ist geschmolzen, mein Kind wurde verletzt!"]}]})
    conv_id = imp.json()["items"][0]["id"]
    rep = client.post(f"/api/v1/inbox/conversations/{conv_id}/reply", headers=h,
                      json={"message": "Der Akku ist geschmolzen!"}).json()
    assert rep["gpsr_incident"] is True
    assert rep["ai_act_disclosure"]


def test_connector_import_validation(client):
    h = _auth(client, "conn4@test.com")
    # 未知平台
    assert client.post("/api/v1/inbox/connectors/nope/import", headers=h,
                       json={"items": [{"messages": ["hi"]}]}).status_code == 404
    # 空 messages
    r = client.post("/api/v1/inbox/connectors/otto/import", headers=h,
                    json={"items": [{"buyer_id": "x"}]})
    assert r.status_code == 422
    # 空 items
    r2 = client.post("/api/v1/inbox/connectors/otto/import", headers=h, json={"items": []})
    assert r2.status_code == 422


def test_seed_demo_includes_kaufland(client):
    h = _auth(client, "conn5@test.com")
    s = client.post("/api/v1/inbox/conversations/seed-demo", headers=h)
    assert s.status_code == 200
    assert s.json()["seeded"] >= 5
    lst = client.get("/api/v1/inbox/conversations?platform=kaufland", headers=h).json()
    assert lst["total"] >= 1
