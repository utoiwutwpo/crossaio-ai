"""一键合规体检（GPSR 付费闭环）：游客限频 / 免费摘要 / 付费交付物 / 欧代联动 / 历史。"""
from tests.conftest import register_and_login

BODY = {
    "product_name": "Kids Building Blocks Toy",
    "keywords": ["toy", "puzzle", "kids"],
    "platform": "allegro",
}


def test_guest_audit_free_summary(client):
    """游客体检：免登录出摘要，不含付费交付物。"""
    r = client.post("/api/v1/compliance/audit-guest", json=BODY)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["unlocked"] is False
    assert d["risk_level"] in ("low", "medium", "high")
    assert 0 <= d["compliance_score"] <= 100
    assert d["gaps"], "缺项清单不应为空"
    assert d["platform_card"]["policy_name"], "应带平台原生规则卡"
    assert d["safety_gate_protocol"]["window"] == "15 天"
    # 付费交付物不下发
    assert "rep_marking" not in d
    assert "tech_file_checklist" not in d
    assert "warnings_pack" not in d
    assert d["upsell_note"]


def test_guest_audit_rate_limited(client):
    # 限频计数器是进程内共享的，先清空保证确定性
    from app.routers import compliance
    compliance._GUEST_HITS.clear()
    for _ in range(3):
        rr = client.post("/api/v1/compliance/audit-guest", json=BODY)
        assert rr.status_code == 200
    r4 = client.post("/api/v1/compliance/audit-guest", json=BODY)
    assert r4.status_code == 429
    assert "3" in r4.json()["detail"]


def test_paid_audit_unlocks_deliverables(client):
    """付费用户：解锁欧代标注 / 技术文件清单 / 警示语包 / 合规块。"""
    headers = register_and_login(client, "audit_paid@test.com")
    # 提升为付费套餐（直接改库；billing 通道由订阅测试覆盖）
    from app.database import SessionLocal, User
    db = SessionLocal()
    u = db.query(User).filter(User.email == "audit_paid@test.com").first()
    u.plan = "starter"
    db.commit()
    db.close()

    # 先配置欧代 → 报告应内嵌真实欧代（不再有占位符）
    rep = client.post("/api/v1/eu-reps", headers=headers, json={
        "company_name": "EU Comply GmbH", "address": "Hauptstr. 1, Berlin",
        "email": "rep@eucomply.de", "is_default": True,
    })
    assert rep.status_code == 200, rep.text

    r = client.post("/api/v1/compliance/audit", json=BODY, headers=headers)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["unlocked"] is True
    # 欧代标注：真实信息 + 三处标注指引
    rm = d["rep_marking"]
    assert rm["configured"] is True
    assert "EU Comply GmbH" in rm["rep_line"]
    places = {p["place"] for p in rm["marking_places"]}
    assert places == {"product", "packaging", "listing"}
    # 技术文件清单：8 项且含保存年限
    tf = d["tech_file_checklist"]
    assert len(tf) == 8
    assert any(i["item"] == "eu_rep_agreement" for i in tf)
    assert all(i["retention"] for i in tf)
    # 警示语包：allegro 覆盖 PL/CZ/HU → 至少 pl 语言
    wp = d["warnings_pack"]
    assert any(w["lang"] == "pl" for w in wp)
    assert all(w["lines"] for w in wp)
    # 合规块内嵌欧代、无占位符
    assert "EU Comply GmbH" in d["gpsr_block"]
    assert "[欧代公司名称]" not in d["gpsr_block"]
    assert not d.get("upsell_note"), "付费版不应再出现升级提示"


def test_free_user_audit_no_deliverables_but_saved(client):
    """免费登录用户：摘要版 + 体检历史落库。"""
    headers = register_and_login(client, "audit_free@test.com")
    r = client.post("/api/v1/compliance/audit", json=BODY, headers=headers)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["unlocked"] is False
    assert "rep_marking" not in d

    h = client.get("/api/v1/compliance/audits", headers=headers)
    assert h.status_code == 200
    items = h.json()["items"]
    assert len(items) >= 1
    assert items[0]["platform"] == "allegro"
    assert items[0]["compliance_score"] == d["compliance_score"]


def test_audit_unknown_platform_404(client):
    headers = register_and_login(client, "audit_404@test.com")
    r = client.post("/api/v1/compliance/audit",
                    json={**BODY, "platform": "nope"}, headers=headers)
    assert r.status_code == 404
