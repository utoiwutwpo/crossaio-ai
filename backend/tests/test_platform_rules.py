"""平台原生 GPSR 规则层（零竞品差异化）+ 付费墙 验证。"""
import pytest

from app.experts import platform_rules as pr
from app.experts import compliance_workflow as cw


# ---------------- 单元层 ----------------
def test_native_platforms_cover_ee_se():
    """东欧/南欧深耕平台均有原生规则（miravia 未在注册表，暂不含）。"""
    native = pr.list_native_rule_platforms()
    for p in ("allegro", "emag", "cdiscount", "otto", "kaufland", "bol"):
        assert p in native


def test_rules_card_fields_complete():
    for p in pr.list_native_rule_platforms():
        card = pr.platform_rules_card(p)
        assert card["native_rules"] is True
        assert card["policy_name"] and card["policy_url"].startswith("http")
        assert card["authority"] and card["enforcement"]
        assert card["rule_count"] >= 2
        assert card["warning_language_count"] >= 1


def test_generic_platform_fallback():
    card = pr.platform_rules_card("amazon")
    assert card["native_rules"] is False
    assert "2023/988" in card["policy_name"]


def test_allegro_native_block_polish_header_and_rep():
    nb = pr.native_compliance_block(
        "allegro", "Kids Wooden Toy Train", ["toy", "wooden", "children"],
        eu_rep={"company_name": "Acme PL Rep", "address": "Warsaw PL",
                "email": "rep@acme.eu"})
    block = nb["block"]
    assert "INFORMACJE O BEZPIECZEŃSTWIE PRODUKTU" in block   # 波兰语平台原生头部
    assert "Osoba odpowiedzialna w UE: Acme PL Rep" in block   # 原生欧代行 + 真实欧代
    assert "[欧代公司名称]" not in block
    assert "OSTRZEŻENIE" in block                              # 波兰语窒息警示
    assert "UOKiK" in block                                    # 当地监管机构
    assert nb["native_rules"] is True
    assert "pl" in nb["block_languages"]


def test_emag_native_block_romanian():
    nb = pr.native_compliance_block("emag", "USB Charger 20W", ["charger", "usb"])
    assert "INFORMAȚII DE SIGURANȚĂ A PRODUSULUI" in nb["block"]
    assert "ANPC" in nb["block"]
    assert "ro" in nb["block_languages"]


def test_cdiscount_native_block_french_toubon():
    nb = pr.native_compliance_block("cdiscount", "Button Cell Watch",
                                    ["watch", "battery"])
    assert "INFORMATIONS DE SÉCURITÉ PRODUIT" in nb["block"]
    assert "DGCCRF" in nb["block"]
    assert "fr" in nb["block_languages"]


def test_unknown_platform_rejected():
    with pytest.raises(Exception):
        pr.platform_rules_card("not_a_platform")


def test_workflow_uses_native_block_when_available():
    """组合层 Listing 合规块：native 平台优先用平台原生规则。"""
    res = cw.listing_compliance_block(
        "allegro", "Kids Toy", ["toy"], eu_rep_line="Acme, Warsaw PL, a@b.eu")
    assert res["native_rules"] is True
    assert "INFORMACJE O BEZPIECZEŃSTWIE" in res["block"]
    assert res["native_meta"]  # 带平台原生元数据


def test_workflow_generic_platform_still_works():
    res = cw.listing_compliance_block("amazon", "Kids Toy", ["toy"])
    assert res["native_rules"] is False
    assert res["block"]  # 通用块仍生成


# ---------------- 接口层（付费墙：合规即付费理由） ----------------
def _auth(client: "object", email: str, plan: str = "free") -> dict:
    r = client.post("/api/v1/users/register", json={
        "email": email, "password": "Passw0rd!123"})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    if plan != "free":
        client.post("/api/v1/billing/subscription", headers=h,
                    json={"plan": plan})
    return h


def test_native_block_paywall_free(client):
    h = _auth(client, "nativefree@test.com")
    r = client.post("/api/v1/products/gpsr/native-block", headers=h, json={
        "product_name": "Kids Toy", "keywords": ["toy"], "platform": "allegro"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["unlocked"] is False            # free：只给规则卡
    assert d["rules_card"]["policy_name"]
    assert "native_block" not in d
    assert d["upsell_note"]                  # 付费钩子带违规后果


def test_native_block_unlocked_for_starter(client):
    h = _auth(client, "nativestarter@test.com", plan="starter")
    r = client.post("/api/v1/products/gpsr/native-block", headers=h, json={
        "product_name": "Kids Toy", "keywords": ["toy"], "platform": "allegro"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["unlocked"] is True
    nb = d["native_block"]
    assert "INFORMACJE O BEZPIECZEŃSTWIE" in nb["block"]
    assert nb["native_rules"] is True
    assert "upsell_note" not in d


def test_guest_check_embeds_platform_rules_in_upsell(client, monkeypatch):
    """游客体检 upsell 提示带平台原生规则（政策名/监管机构/后果）。"""
    # 绕过每 IP 限流（全量套件中 test_gpsr 已用满 3 次/IP）
    from app.routers import products as products_router
    monkeypatch.setattr(products_router, "_guest_rate_ok", lambda ip: True)
    r = client.post("/api/v1/products/gpsr/check-guest", json={
        "product_name": "Kids Toy", "keywords": ["toy"], "platform": "emag"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert "eMAG" in d["upsell_note"] or "siguranță" in d["upsell_note"]
    assert "ANPC" in d["upsell_note"]
