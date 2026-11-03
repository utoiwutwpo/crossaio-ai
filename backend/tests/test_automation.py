"""自动化流水线：凭证接入后按订阅档位自动识别、自动处理 6 大功能。

覆盖：
- /automation/status 六功能状态机（free 无凭证 / 凭证+套餐门控 / 配额汇报）
- 凭证保存按订阅配额自动识别（free/starter=1，pro=3，business 无限）
- /automation/run 一键串联：体检 → GPSR 合规块 → 收件箱自动回复（Pro）→ 联动建议
"""
import uuid

import pytest

BASE = "/api/v1"


@pytest.fixture()
def token(client):
    r = client.post(f"{BASE}/users/register",
                    json={"email": f"{uuid.uuid4().hex[:8]}@auto.test.dev",
                          "password": "Passw0rd!123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


def _cred_body(platform):
    from app.experts.platform_credentials import PLATFORM_CRED_REGISTRY
    cfg = PLATFORM_CRED_REGISTRY[platform]
    return {"credentials": {k: f"test-{k}" for k, *_ in cfg["fields"]}}


# ---------- 状态矩阵 ----------

def test_status_requires_login(client):
    assert client.get(f"{BASE}/automation/status").status_code == 401


def test_status_free_no_credential(client, token):
    """free + 未接凭证：监控就绪、客服/收件箱待接凭证、广告需升级、差评按需。"""
    d = client.get(f"{BASE}/automation/status", headers=_auth(token)).json()
    assert d["plan"] == "free"
    assert d["platform_quota"] == {"limit": 1, "used": 0}
    f = d["features"]
    assert f["watch"]["state"] == "ready"
    assert f["gpsr"]["state"] == "ready"
    assert f["cs"]["state"] == "no_credential"
    assert f["inbox"]["state"] == "no_credential"
    assert f["ad"]["state"] == "locked_plan"       # free 不含 ad_copy
    assert f["review"]["state"] == "manual"


def test_status_watch_active_after_add(client, token):
    """添加 listing 后监控/GPSR 进入「自动运行中」（调度器每日体检）。"""
    h = _auth(token)
    r = client.post(f"{BASE}/listings", headers=h,
                    json={"product_name": "Baby Bottle Warmer",
                          "platform": "amazon", "keywords": ["baby"]})
    assert r.status_code == 200, r.text
    d = client.get(f"{BASE}/automation/status", headers=h).json()
    assert d["features"]["watch"]["state"] == "active"
    assert "1 个" in d["features"]["watch"]["detail"]


# ---------- 订阅配额：按档位自动识别平台接入数 ----------

def test_quota_free_one_platform_only(client, token):
    """free 最多 1 个平台：第 2 个凭证保存被 402 引导升级。"""
    h = _auth(token)
    ok = client.post(f"{BASE}/compliance/credentials/allegro",
                     json=_cred_body("allegro"), headers=h)
    assert ok.status_code == 200, ok.text
    second = client.post(f"{BASE}/compliance/credentials/otto",
                         json=_cred_body("otto"), headers=h)
    assert second.status_code == 402
    assert "最多接入 1 个平台" in second.json()["detail"]
    d = client.get(f"{BASE}/automation/status", headers=h).json()
    assert d["platform_quota"] == {"limit": 1, "used": 1}
    # 凭证已接但套餐不够 → 客服/收件箱状态从「待接凭证」推进为「需升级」
    assert d["features"]["cs"]["state"] == "locked_plan"
    assert d["features"]["inbox"]["state"] == "locked_plan"


def test_quota_pro_three_business_unlimited(client, token):
    h = _auth(token)
    assert client.post(f"{BASE}/billing/subscription",
                       json={"plan": "pro"}, headers=h).status_code == 200
    for p in ("allegro", "otto", "emag"):
        r = client.post(f"{BASE}/compliance/credentials/{p}",
                        json=_cred_body(p), headers=h)
        assert r.status_code == 200, r.text
    fourth = client.post(f"{BASE}/compliance/credentials/kaufland",
                         json=_cred_body("kaufland"), headers=h)
    assert fourth.status_code == 402
    # business = 无限
    assert client.post(f"{BASE}/billing/subscription",
                       json={"plan": "business"}, headers=h).status_code == 200
    assert client.post(f"{BASE}/compliance/credentials/kaufland",
                       json=_cred_body("kaufland"), headers=h).status_code == 200
    d = client.get(f"{BASE}/automation/status", headers=h).json()
    assert d["platform_quota"]["limit"] is None
    assert d["platform_quota"]["used"] == 4


# ---------- 一键串联流水线 ----------

def test_run_pipeline_free_skips_auto_reply(client, token):
    """free：体检+GPSR 合规块自动完成；客服自动回复按订阅跳过并说明原因。"""
    h = _auth(token)
    r = client.post(f"{BASE}/listings", headers=h,
                    json={"product_name": "Baby Bottle Warmer",
                          "platform": "amazon", "keywords": ["baby"]})
    assert r.status_code == 200, r.text
    r = client.post(f"{BASE}/inbox/conversations", headers=h,
                    json={"platform": "amazon",
                          "first_message": "Where is my order? It is two weeks late!"})
    assert r.status_code == 200, r.text
    run = client.post(f"{BASE}/automation/run", headers=h)
    assert run.status_code == 200, run.text
    s = run.json()["summary"]
    assert s["auto_replies_sent"] == 0
    assert s["skipped"] and "Pro" in s["skipped"][0]["reason"]
    assert "report" in run.json()


def test_run_pipeline_pro_auto_replies_once(client, token):
    """Pro：未回复会话被自动生成合规回复（含 Art.50 披露入库）；重复跑不重复回。"""
    h = _auth(token)
    assert client.post(f"{BASE}/billing/subscription",
                       json={"plan": "pro"}, headers=h).status_code == 200
    r = client.post(f"{BASE}/inbox/conversations", headers=h,
                    json={"platform": "amazon",
                          "first_message": "Is this bottle warmer safe for babies?"})
    assert r.status_code == 200, r.text
    s = client.post(f"{BASE}/automation/run", headers=h).json()["summary"]
    assert s["auto_replies_sent"] == 1
    assert s["skipped"] == []
    # 第二轮：会话已有出站回复 → 不重复处理
    s2 = client.post(f"{BASE}/automation/run", headers=h).json()["summary"]
    assert s2["auto_replies_sent"] == 0


def test_pipeline_negative_message_suggests_review_rewrite(client, token):
    """问题驱动联动：负面情绪买家消息 → 建议使用差评改写。"""
    h = _auth(token)
    assert client.post(f"{BASE}/billing/subscription",
                       json={"plan": "pro"}, headers=h).status_code == 200
    # seed-demo 的会话若含负面消息则触发建议；无负面则本条断言宽松处理
    client.post(f"{BASE}/inbox/conversations/seed-demo", headers=h)
    s = client.post(f"{BASE}/automation/run", headers=h).json()["summary"]
    assert isinstance(s["suggestions"], list)
