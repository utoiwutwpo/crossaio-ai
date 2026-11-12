"""I0–I5 六单元验收测试（不依赖数据库与网络）。"""
import hashlib

from app.billing import PLANS, can_auto_reply, can_auto_writeback
from app.connectors.capabilities import CHANNELS, auto_send_allowed
from app.connectors.channels.allegro import AllegroAdapter
from app.connectors.channels.regional import SpecAdapter
from app.connectors.channels.manual import ManualAdapter
from app.connectors.channels.partial_api import PartialApiAdapter
from app.connectors.channels.registry import adapter_for
from app.entitlements import can_act
from app.experts.compliance_workflow import is_safety_incident
from app.experts.content_provenance import build_provenance
from app.experts.customer_service import CustomerServiceExpert
from app.schemas import CustomerServiceRequest


class FakeUser:
    def __init__(self, plan="pro", uid="u-test"):
        self.plan = plan
        self.id = uid


expert = CustomerServiceExpert()


# ---------------- I0 ----------------
def test_german_lawyer_hits_legal_redline():
    r = expert.handle(CustomerServiceRequest(
        customer_message="Wenn Sie nicht erstatten, gehe ich zu meinem Rechtsanwalt.",
        platform="allegro", language="de"))
    assert "legal_action" in r.policy_flags
    assert r.needs_escalation is True


def test_polish_lawyer_hits_legal_redline():
    r = expert.handle(CustomerServiceRequest(
        customer_message="Zamówienie uszkodzone, idę do adwokata i sądu.",
        platform="allegro", language="pl"))
    assert "legal_action" in r.policy_flags


def test_no_fabricated_delivery_promise():
    r = expert.handle(CustomerServiceRequest(
        customer_message="Where is my order 12345678?", platform="allegro"))
    assert "3-7" not in r.reply
    assert "已发货" not in r.reply
    assert r.needs_escalation is True
    assert "missing_order_facts" in r.policy_flags


def test_no_fabricated_return_window():
    r = expert.handle(CustomerServiceRequest(
        customer_message="I want a refund", platform="allegro"))
    assert "30 天" not in r.reply and "30-day" not in r.reply
    assert r.needs_escalation is True


def test_return_window_from_seller_policy():
    r = expert.handle(CustomerServiceRequest(
        customer_message="I want a refund", platform="allegro",
        return_window_days=14))
    assert "14" in r.reply
    assert r.needs_escalation is False


# ---------------- I1 ----------------
def test_amazon_cannot_send_message():
    d = can_act(None, FakeUser("business"), "amazon", "send_message")
    assert d["allowed"] is False
    assert d["reason_code"] == "platform_unsupported"
    assert "Permitted Messages" in d["hint"] or "Seller Central" in d["hint"]


def test_tiktok_conditional_is_not_auto_sendable():
    d = can_act(None, FakeUser("business"), "tiktok", "auto_send")
    assert d["allowed"] is False
    assert d["reason_code"] == "platform_unsupported"


def test_free_plan_cannot_auto_send_allegro():
    d = can_act(None, FakeUser("free"), "allegro", "auto_send")
    assert d["allowed"] is False
    assert d["reason_code"] == "plan_required"


def test_pro_plan_can_auto_send_allegro():
    d = can_act(None, FakeUser("pro"), "allegro", "auto_send")
    assert d["allowed"] is True


def test_agentic_feed_business_only():
    assert can_act(None, FakeUser("business"), "amazon", "agentic_feed")["allowed"] is True
    assert can_act(None, FakeUser("pro"), "amazon", "agentic_feed")["reason_code"] == "plan_required"


def test_redline_hold_blocks_send():
    d = can_act(None, FakeUser("business"), "allegro", "auto_send",
                redline_flags=["legal_action"])
    assert d["allowed"] is False and d["reason_code"] == "redline_hold"


def test_slots_sum_to_22_for_full_coverage():
    weights = sum(3 if CHANNELS[p]["tier"] == "A" else
                  2 if CHANNELS[p]["tier"] == "B" else 1 for p in CHANNELS)
    assert weights == 22
    assert PLANS["business"]["slots"] == 22


def test_billing_auto_gates_are_capability_aware():
    u = FakeUser("pro")
    assert can_auto_reply(u, "allegro") is True
    assert can_auto_reply(u, "amazon") is False
    assert can_auto_writeback(u, "amazon") is True       # listing 写能力存在
    assert can_auto_reply(FakeUser("free"), "allegro") is False


# ---------------- I2 ----------------
def test_adapter_routing_covers_four_modes():
    assert isinstance(adapter_for("allegro"), AllegroAdapter)
    assert isinstance(adapter_for("amazon"), SpecAdapter)   # LWA + SigV4
    assert isinstance(adapter_for("cdiscount"), SpecAdapter)   # Octopia API
    assert isinstance(adapter_for("otto"), SpecAdapter)       # OTTO Market API
    assert isinstance(adapter_for("walmart"), PartialApiAdapter)


def test_manual_adapter_task_payload_has_backoffice():
    t = ManualAdapter("otto").task_payload(buyer_message="hi", draft="draft")
    assert t["platform"] == "otto"
    assert t["backoffice_url"].startswith("http")
    assert t["draft_reply"] == "draft"


# ---------------- I4 ----------------
def test_safety_incident_detection():
    assert is_safety_incident("The pan caught fire and burned my hand") is True
    assert is_safety_incident("Die Pfanne hat Feuer gefangen") is True
    assert is_safety_incident("Where is my order?") is False


def test_only_allegro_is_auto_sendable():
    assert auto_send_allowed("allegro") is True
    assert auto_send_allowed("tiktok") is False
    assert auto_send_allowed("amazon") is False


# ---------------- I5 ----------------
def test_provenance_has_hash_and_iptc_field():
    p = build_provenance("Hello listing", model="glm-4", platform="allegro")
    expected = "sha256:" + hashlib.sha256("Hello listing".encode()).hexdigest()
    assert p["content_hash"] == expected
    assert p["ai_generated"] is True
    assert "trainedAlgorithmicMedia" in p["xmp_fields"]["Iptc4xmpExt:DigitalSourceType"]
    assert p["c2pa_manifest"]["signed"] is False
