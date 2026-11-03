"""回填凭证接线层测试：无凭证 → credentials_required；有凭证+dry_run → ready_to_send。"""
import os

from app.experts.listing_backfill import (
    build_backfill_payload,
    get_credentials,
    submit_backfill_payload,
)


def _clear_creds():
    for k in list(os.environ):
        if k.startswith("CROSSBOT_CRED_"):
            os.environ.pop(k)


def test_build_backfill_payload_structure():
    p = build_backfill_payload("amazon", "Baby Monitor", ["camera", "wifi"])
    assert p["platform"] == "amazon"
    assert p["gpsr_block"]
    assert p["backfill"]["target_field"]
    assert p["backfill"]["api_reference"]
    assert p["auth_required"] is True


def test_get_credentials_absent():
    _clear_creds()
    assert get_credentials("amazon") is None


def test_get_credentials_present():
    _clear_creds()
    os.environ["CROSSBOT_CRED_AMAZON_TOKEN"] = "tok-xyz"
    try:
        creds = get_credentials("amazon")
        assert creds == {"token": "tok-xyz"}
    finally:
        os.environ.pop("CROSSBOT_CRED_AMAZON_TOKEN", None)


def test_submit_no_credentials_returns_blocked():
    _clear_creds()
    p = build_backfill_payload("amazon", "Baby Monitor", ["camera"])
    res = submit_backfill_payload("amazon", p)
    assert res["status"] == "credentials_required"
    assert res["platform"] == "amazon"
    assert res["backfill"] is not None


def test_submit_with_credentials_dry_run_ready():
    _clear_creds()
    os.environ["CROSSBOT_CRED_AMAZON_TOKEN"] = "test-token-123"
    try:
        p = build_backfill_payload("amazon", "Baby Monitor", ["camera"])
        res = submit_backfill_payload("amazon", p, dry_run=True)
        assert res["status"] == "ready_to_send"
        assert res["dry_run"] is True
        assert res["request"]["headers"]["Authorization"] == "Bearer test-token-123"
        assert res["request"]["method"] == "PATCH"
    finally:
        os.environ.pop("CROSSBOT_CRED_AMAZON_TOKEN", None)


def test_submit_real_path_uses_requests(monkeypatch):
    """凭证就绪且 dry_run=False 时，应尝试发起真实请求（用 stub 验证调用而非真联网）。"""
    _clear_creds()
    os.environ["CROSSBOT_CRED_EBAY_OAUTH_TOKEN"] = "tok"
    try:
        import app.experts.listing_backfill as lb
        fake = type("R", (), {"status_code": 200, "text": "{}"})()
        monkeypatch.setattr(lb.requests, "request", lambda *a, **k: fake)
        p = build_backfill_payload("ebay", "Baby Monitor", ["camera"])
        res = submit_backfill_payload("ebay", p, dry_run=False)
        assert res["status"] == "submitted"
        assert res["http_status"] == 200
    finally:
        os.environ.pop("CROSSBOT_CRED_EBAY_OAUTH_TOKEN", None)
