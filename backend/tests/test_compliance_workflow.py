"""组合层 + 发送前 GPSR 扫描 + 一键回填 验收"""
from app.experts.compliance_workflow import (
    is_safety_incident,
    augment_customer_reply,
    compliance_priority_reply,
    listing_compliance_block,
    MarketplaceComplianceWorkflow,
)
from app.experts.listing_backfill import build_backfill_payload


# ---------- 安全事件判定 ----------
def test_is_safety_incident_fire_true():
    assert is_safety_incident("The product caught fire!") is True


def test_is_safety_incident_injury_true():
    assert is_safety_incident("I was injured by this item") is True


def test_is_safety_incident_clean_false():
    assert is_safety_incident("Where is my order #123?") is False
    assert is_safety_incident("My package arrived late") is False


# ---------- augment：Art.50 始终 + GPSR 条件触发 ----------
def test_augment_non_safety_has_art50_no_gpsr():
    out = augment_customer_reply("Your order ships today.", "amazon", "en",
                                 "Where is my order #123?", True)
    assert "[AI Act Art.50]" in out
    assert "Safety & Compliance Information" not in out   # 无安全词 → 无 GPSR 块


def test_augment_safety_appends_gpsr_lines():
    out = augment_customer_reply("We are sorry.", "amazon", "en",
                                 "this thing caught fire", True)
    assert "[AI Act Art.50]" in out
    # amazon 要求语言含 en/de/fr → 至少出现英文安全标题
    assert "Safety & Compliance Information" in out


def test_augment_respects_disabled():
    out = augment_customer_reply("Plain.", "amazon", "en",
                                 "caught fire", False)
    assert "[AI Act Art.50]" not in out


# ---------- 合规优先回复 ----------
def test_compliance_priority_reply_has_gpsr_and_art50():
    out = compliance_priority_reply("amazon", "en", "it exploded", True)
    assert "Safety Gate" in out            # 15 天上报提示
    assert "EU Responsible Person" in out
    assert "[AI Act Art.50]" in out
    assert "Safety & Compliance Information" in out


# ---------- 平台语言特异性 ----------
def test_platform_language_specificity_allegro():
    # Allegro 覆盖 PL/CZ/HU → 安全指引须出现三种语言标题
    out = compliance_priority_reply("allegro", "pl", "zapaliło się", True)
    assert "Informacje dotyczące bezpieczeństwa" in out   # pl
    assert "Bezpečnostní informace" in out                 # cs
    assert "Biztonsági információ" in out                  # hu


# ---------- Listing 合规块（组合层 Listing 侧） ----------
def test_listing_compliance_block_returns_risk_and_block():
    g = listing_compliance_block("amazon",
                                 "Wireless Headphones",
                                 ["wireless", "bluetooth"])
    assert g["platform"] == "amazon"
    assert g["risk_level"] in ("low", "medium", "high")
    assert "block" in g and g["block"]


# ---------- 一键回填适配层 ----------
def test_backfill_payload_amazon():
    p = build_backfill_payload("amazon", "Wireless Headphones",
                               ["wireless", "bluetooth"])
    assert p["platform"] == "amazon"
    assert p["gpsr_block"]
    assert p["backfill"]["target_field"]
    assert "Selling Partner API" in p["backfill"]["api_reference"]
    assert p["auth_required"] is True


def test_backfill_payload_unknown_platform_raises():
    import pytest
    with pytest.raises(KeyError):
        build_backfill_payload("not_a_platform", "x", ["y"])


def test_workflow_instance_same_as_module():
    w = MarketplaceComplianceWorkflow()
    assert w.is_safety_incident("caught fire") is True
