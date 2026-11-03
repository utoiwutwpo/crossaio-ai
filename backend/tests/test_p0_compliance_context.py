"""P0-2 合规×运营一体化：体检结论注入描述生成 / 客服话术（任务清单 Batch P0 验收点 2）。

覆盖：
- 无审计 → 降级普通模式（compliance_note=None，不报错）
- 审计未通过（medium/high）→ 描述/客服响应带合规提示块 + related_audit_id
- 审计已通过（low）→ 不注入
- 平台收窄匹配（allegro 审计不注入 amazon 描述）
- usage_logs.with_compliance 标记正确
"""
import uuid

from tests.conftest import register_and_login
from app.database import SessionLocal, UsageLog, User

HIGH_RISK = {"product_name": "Portable Charger Power Bank",
             "keywords": ["charger", "power bank", "battery"],
             "platform": "amazon"}
LOW_RISK = {"product_name": "Cotton Socks",
            "keywords": ["socks", "cotton"],
            "platform": "amazon"}


def _reg(client):
    h = register_and_login(client, f"p02-{uuid.uuid4().hex[:10]}@test.dev")
    return h


def _audit(client, h, body, platform=None):
    payload = dict(body)
    if platform:
        payload["platform"] = platform
    r = client.post("/api/v1/compliance/audit", json=payload, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _audit_id(client, h, product_name=None):
    rows = client.get("/api/v1/compliance/audits", headers=h).json()["items"]
    if product_name:
        rows = [x for x in rows if x["product_name"] == product_name]
    assert rows, "应至少有一条体检记录"
    return rows[0]["id"]


def _last_usage_flag(client, email: str) -> bool:
    with SessionLocal() as db:
        u = db.query(User).filter(User.email == email).first()
        if not u:
            return False
        row = (db.query(UsageLog)
               .filter(UsageLog.user_id == u.id)
               .order_by(UsageLog.created_at.desc()).first())
        return bool(row and row.with_compliance)


# ---- 描述生成 ----

def test_desc_no_audit_fallback(client):
    h = _reg(client)
    r = client.post("/api/v1/products/descriptions/generate", headers=h, json={
        "product_name": "LED Desk Lamp", "keywords": ["lamp", "desk"],
        "platform": "amazon", "language": "en",
    })
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["compliance_note"] is None
    assert d["related_audit_id"] is None


def test_desc_with_unpassed_audit_injected(client):
    h = _reg(client)
    rep = _audit(client, h, HIGH_RISK)           # 高风险 → 未通过
    assert rep["risk_level"] in ("medium", "high")
    r = client.post("/api/v1/products/descriptions/generate", headers=h, json={
        "product_name": "Portable Charger Power Bank",
        "keywords": ["charger", "power bank"],
        "platform": "amazon", "language": "en",
    })
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["compliance_note"] and "未通过" in d["compliance_note"]
    assert d["related_audit_id"] == _audit_id(client, h, "Portable Charger Power Bank")
    assert "待补项" in d["compliance_note"]


def test_desc_with_passed_audit_not_injected(client):
    h = _reg(client)
    rep = _audit(client, h, LOW_RISK)            # 低风险 → 已通过
    assert rep["risk_level"] == "low"
    r = client.post("/api/v1/products/descriptions/generate", headers=h, json={
        "product_name": "Cotton Socks", "keywords": ["socks"],
        "platform": "amazon", "language": "en",
    })
    assert r.status_code == 200, r.text
    assert r.json()["compliance_note"] is None


def test_desc_platform_scoped(client):
    h = _reg(client)
    _audit(client, h, HIGH_RISK, platform="allegro")   # 只有 allegro 审计
    # amazon 描述：平台不匹配 → 不注入
    r = client.post("/api/v1/products/descriptions/generate", headers=h, json={
        "product_name": "Portable Charger Power Bank",
        "keywords": ["charger"],
        "platform": "amazon", "language": "en",
    })
    assert r.status_code == 200
    assert r.json()["compliance_note"] is None
    # allegro 描述：命中 → 注入
    r2 = client.post("/api/v1/products/descriptions/generate", headers=h, json={
        "product_name": "Portable Charger Power Bank",
        "keywords": ["charger"],
        "platform": "allegro", "language": "pl",
    })
    assert r2.status_code == 200
    assert r2.json()["compliance_note"] is not None


# ---- 客服话术 ----

def _upgrade_to_pro(client, headers) -> None:
    from app.database import SessionLocal, User
    token = headers["Authorization"].split()[-1]
    # 从 /users/me 取 email，再改库
    me = client.get("/api/v1/users/me", headers=headers).json()
    with SessionLocal() as db:
        u = db.query(User).filter(User.email == me["email"]).first()
        u.plan = "pro"
        db.commit()


def test_cs_with_unpassed_audit_injected(client):
    h = _reg(client)
    _upgrade_to_pro(client, h)
    _audit(client, h, HIGH_RISK)
    r = client.post("/api/v1/customer-service/messages", headers=h, json={
        "customer_message": "Is this charger safe for airplane travel?",
        "platform": "amazon", "language": "en",
    })
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["compliance_note"] and "未通过" in d["compliance_note"]
    assert d["related_audit_id"] == _audit_id(client, h)


def test_cs_no_audit_fallback(client):
    h = _reg(client)
    _upgrade_to_pro(client, h)
    r = client.post("/api/v1/customer-service/messages", headers=h, json={
        "customer_message": "Where is my package?",
        "platform": "amazon", "language": "en",
    })
    assert r.status_code == 200, r.text
    assert r.json()["compliance_note"] is None


# ---- usage_logs 标记 ----

def test_usage_log_with_compliance_flag(client):
    email = f"p02flag-{uuid.uuid4().hex[:10]}@test.dev"
    h = register_and_login(client, email)
    # 无审计 → with_compliance=False
    client.post("/api/v1/products/descriptions/generate", headers=h, json={
        "product_name": "LED Desk Lamp", "keywords": ["lamp"],
        "platform": "amazon", "language": "en",
    })
    assert _last_usage_flag(client, email) is False

    # 有未通过审计 → with_compliance=True
    _audit(client, h, HIGH_RISK)
    client.post("/api/v1/products/descriptions/generate", headers=h, json={
        "product_name": "Portable Charger Power Bank",
        "keywords": ["charger"],
        "platform": "amazon", "language": "en",
    })
    assert _last_usage_flag(client, email) is True
