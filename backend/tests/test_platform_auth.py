"""13 平台授权 + 四语种矩阵的本地校验测试（不依赖数据库与网络）。"""
import asyncio

from app.connectors.auth.providers import (build_authorize_url, validate_shape,
                                           verify_credential, verify_many)
from app.connectors.auth.spec import AUTH_SPECS, PLATFORM_ORDER, all_specs
from app.i18n import LANGS, matrix_all_locales, platform_text, platform_text_all

EXPECTED = {
    "amazon", "amazon_us", "ebay", "fruugo", "walmart",
    "cdiscount", "otto", "allegro", "emag", "kaufland",
    "bol", "zalando", "tiktok",
}

GOOD_PAYLOAD = {
    "amazon": {"client_id": "amzn1.application-oa2-client.abc123",
               "client_secret": "abcdef1234567890",
               "refresh_token": "Atzr|IwEBabcdefghijklmn"},
    "ebay": {"client_id": "AppId123", "client_secret": "Secret123456"},
    "allegro": {"client_id": "client123", "client_secret": "secret123456"},
    "bol": {"client_id": "client123", "client_secret": "secret123456"},
    "walmart": {"client_id": "client123", "client_secret": "secret123456"},
    "kaufland": {"client_key": "ckey1234", "secret_key": "skey12345678"},
    "emag": {"api_key": "emagkey123456"},
    "fruugo": {"merchant_id": "12345", "api_key": "fruugo_key_123"},
    "cdiscount": {"api_key": "cdkey123456", "seller_login": "seller01"},
}


def test_platform_count_is_13():
    assert len(PLATFORM_ORDER) == 13
    assert set(PLATFORM_ORDER) == EXPECTED
    assert len(all_specs()) == 13


def test_all_platforms_have_spec_and_docs():
    for p in PLATFORM_ORDER:
        spec = AUTH_SPECS[p]
        assert spec["fields"], f"{p} 没有凭证字段"
        assert spec["docs"].startswith("https://"), f"{p} 缺官方文档地址"
        assert spec["stage"] in ("confirmed", "unconfirmed")


def test_four_langs_cover_all_platforms():
    assert LANGS == ("en", "de", "fr", "pl")
    for p in PLATFORM_ORDER:
        texts = platform_text_all(p)
        assert set(texts.keys()) == set(LANGS)
        for lang in LANGS:
            assert texts[lang]["label"], f"{p}/{lang} 缺 label"
            assert texts[lang]["apply_note"], f"{p}/{lang} 缺 apply_note"
            assert texts[lang]["unlocks"], f"{p}/{lang} 缺 unlocks"


def test_polish_pack_is_real_polish():
    # 波兰语包不能是英文占位（抽查三个平台的首词）
    assert "Polska" in platform_text("allegro", "pl")["label"]
    assert "Niemcy" in platform_text("otto", "pl")["label"]
    assert "Połączono" in matrix_all_locales(["allegro"], {"allegro": "connected"})[0][
        "status_text"]["pl"]


def test_matrix_has_four_langs_per_row():
    statuses = {"amazon": "connected", "ebay": "unconnected"}
    rows = matrix_all_locales(PLATFORM_ORDER, statuses)
    assert len(rows) == 13
    for row in rows:
        assert set(row["status_text"].keys()) == set(LANGS)
        assert set(row["text"].keys()) == set(LANGS)


def test_shape_validation_marks_missing_fields():
    res = validate_shape("amazon", {})
    assert res["ok"] is False
    assert res["status"] == "pending"
    assert set(res["missing_fields"]) == {"client_id", "client_secret", "refresh_token"}


def test_shape_validation_accepts_complete_payload():
    res = validate_shape("amazon", GOOD_PAYLOAD["amazon"])
    assert res["ok"] is True
    assert res["status"] == "connected"
    assert all(c["ok"] for c in res["checks"])


def test_shape_validation_rejects_placeholder():
    res = validate_shape("ebay", {"client_id": "your_client_id",
                                  "client_secret": "your_client_secret"})
    assert res["ok"] is False
    assert any("占位符" in c["reason"] for c in res["checks"])


def test_shape_validation_rejects_short_secret():
    res = validate_shape("emag", {"api_key": "abc"})
    assert res["ok"] is False
    assert "长度不足" in " ".join(c["reason"] for c in res["checks"])


def test_authorize_url_only_for_confirmed_oauth_platforms():
    for p in ("ebay", "allegro"):
        url = build_authorize_url(p, "st123", "https://example.com/cb",
                                  {"client_id": "cid"})
        assert url and url.startswith("https://")
        assert "state=st123" in url
    for p in ("tiktok", "amazon", "kaufland", "fruugo"):
        assert build_authorize_url(p, "st123", "https://example.com/cb",
                                   {"client_id": "cid"}) is None


def test_verify_credential_without_live_does_not_hit_network():
    res = asyncio.get_event_loop().run_until_complete(
        verify_credential("walmart", GOOD_PAYLOAD["walmart"], live=False))
    assert res["status"] == "connected"
    assert res["live"] is None


def test_verify_many_runs_all_platforms_concurrently():
    payloads = {p: GOOD_PAYLOAD[p] for p in GOOD_PAYLOAD}
    results = asyncio.get_event_loop().run_until_complete(
        verify_many(payloads, live=False))
    assert len(results) == len(payloads)
    for platform, res in results.items():
        assert res["status"] == "connected", f"{platform} 校验未通过"


def test_unconfirmed_platforms_never_claim_live_capability():
    for p in PLATFORM_ORDER:
        spec = AUTH_SPECS[p]
        if spec["stage"] == "unconfirmed":
            assert spec["live_check"] == "shape"
            assert spec.get("token_url") is None


def test_channel_capability_matrix_covers_13():
    from app.connectors.capabilities import CHANNELS, matrix, summary
    assert len(CHANNELS) == 13
    assert set(CHANNELS) == EXPECTED
    rows = matrix()
    assert len(rows) == 13
    for row in rows:
        assert row["tier"] in ("A", "B", "C")
        assert set(row["caps"].keys()) == {
            "read_messages", "send_message", "read_orders",
            "write_listing", "write_inventory", "compliance_docs"}
        assert row["mode"] in ("api", "api_limited", "email", "manual")
    assert summary() == {"A": 2, "B": 5, "C": 6}


def test_only_tier_a_can_auto_send():
    """自动外发必须严格限定在 A 档且确认支持；tiktok 的 conditional 不算。"""
    from app.connectors.capabilities import auto_send_allowed
    allowed = [p for p in EXPECTED if auto_send_allowed(p)]
    assert allowed == ["allegro"]


def test_amazon_cannot_read_buyer_messages():
    """Amazon 只有 Permitted Messages，读买家咨询必须判 False。"""
    from app.connectors.capabilities import supports
    assert supports("amazon", "read_messages") is False
    assert supports("amazon_us", "read_messages") is False
    assert supports("amazon", "read_orders") is True


def test_conditional_values_are_not_treated_as_supported():
    from app.connectors.capabilities import supports
    assert supports("tiktok", "read_messages") is False
    assert supports("ebay", "read_messages") is False
