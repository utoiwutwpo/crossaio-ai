"""EU AI Act Art.50 披露层验收"""
from app.experts.ai_act import wrap_reply, identity_text, content_marker, supported_languages
from app.experts.customer_service import CustomerServiceExpert
from app.schemas import CustomerServiceRequest


def test_identity_text_language_routing():
    assert "KI-Assistenten" in identity_text("de")
    assert "asistente de IA" in identity_text("es")
    # 未知语言回落 en
    assert "AI assistant" in identity_text("xx")


def test_wrap_reply_appends_disclosure():
    out = wrap_reply("Your order ships today.", "en", True)
    assert "Your order ships today." in out
    assert "[AI Act Art.50]" in out
    assert "AI assistant" in out


def test_wrap_reply_disabled_returns_original():
    orig = "Plain reply."
    assert wrap_reply(orig, "en", False) == orig


def test_content_marker_constant():
    assert content_marker() == "ai-generated"


def test_customer_service_injects_disclosure_german():
    expert = CustomerServiceExpert(llm=None)
    # 英文 tracking 触发词命中模板（无需 LLM），但要求德文披露
    resp = expert.handle(CustomerServiceRequest(
        customer_message="Where is my order #123-4567890-1234567?",
        language="de",
    ))
    assert "[AI Act Art.50]" in resp.reply
    assert "KI-Assistenten" in resp.reply
    assert resp.ai_act_disclosure and "KI-Assistenten" in resp.ai_act_disclosure
    assert resp.ai_generated is True
    assert "123-4567890-1234567" in resp.reply  # 订单号未被破坏


def test_customer_service_disclosure_can_be_disabled():
    expert = CustomerServiceExpert(llm=None)
    resp = expert.handle(CustomerServiceRequest(
        customer_message="Where is my order #123-4567890-1234567?",
        language="en",
        ai_act_disclosure=False,
    ))
    assert "[AI Act Art.50]" not in resp.reply
    assert resp.ai_act_disclosure is None


def test_supported_languages_nonempty():
    assert len(supported_languages()) >= 10


def test_cs_safety_incident_triggers_compliance_priority():
    expert = CustomerServiceExpert(llm=None)
    resp = expert.handle(CustomerServiceRequest(
        customer_message="Your product caught fire and I was injured!",
        language="en",
        platform="amazon",
    ))
    assert resp.gpsr_incident is True
    assert resp.needs_escalation is True
    assert resp.intent == "safety_incident"
    assert resp.policy_flags == ["gpsr_safety_incident"]
    assert "Safety Gate" in resp.reply          # GPSR 指引 + 15 天上报提示
    assert "[AI Act Art.50]" in resp.reply      # Art.50 披露
    assert resp.ai_act_disclosure and "AI assistant" in resp.ai_act_disclosure
