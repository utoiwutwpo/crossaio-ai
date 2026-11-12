"""写回与真实探测：用本地 stub HTTP 服务验证请求真的发出去、响应真的解析。"""
import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.connectors.channels.base import CapabilityNotSupported
from app.connectors.channels.regional import SpecAdapter
from app.connectors.live_probe import probe_platform

CALLS = []


class Handler(BaseHTTPRequestHandler):
    def _log(self):
        CALLS.append((self.command, self.path, self.headers.get("Authorization", "")))

    def do_GET(self):
        self._log()
        body = json.dumps({"orders": [{"order_id": "A-1", "status": "PAID"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self._log()
        if self.path.endswith("/token"):
            body = b'{"access_token":"tok","expires_in":3600}'
        else:
            body = b"{}"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_PUT(self):
        self._log()
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    do_PATCH = do_PUT

    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def stub():
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}"
    srv.shutdown()


def _run(coro):
    return asyncio.get_event_loop_policy().get_event_loop().run_until_complete(coro)


def test_ebay_inventory_really_calls_api(stub):
    CALLS.clear()
    a = SpecAdapter("ebay", {"access_token": "tkn", "base_url": stub})
    res = _run(a.push_inventory("SKU-9", 7))
    assert res["written"] is True and res["quantity"] == 7
    assert any(c[0] == "PUT" and "/sell/inventory/v1/inventory/SKU-9" in c[1]
               for c in CALLS)


def test_bol_listing_really_calls_api(stub):
    CALLS.clear()
    a = SpecAdapter("bol", {"client_id": "c", "client_secret": "s",
                            "base_url": stub, "token_url": stub + "/token"})
    res = _run(a.push_listing({"ean": "123", "price": 9.9, "quantity": 3}))
    assert res["written"] is True
    assert any(c[0] == "POST" and "/retailer/offers" in c[1] for c in CALLS)


def test_kaufland_unit_patch_uses_unit_id(stub):
    CALLS.clear()
    a = SpecAdapter("kaufland", {"client_key": "k", "secret_key": "s",
                                 "base_url": stub,
                                 "listing_map": {"SKU-1": {"unit_id": "u-1"}}})
    res = _run(a.push_inventory("SKU-1", 12))
    assert res["unit_id"] == "u-1" and res["written"] is True
    assert any(c[0] == "PATCH" and "/units/u-1" in c[1] for c in CALLS)


def test_probe_marks_live_only_on_real_2xx(stub):
    res = _run(probe_platform("ebay", {"access_token": "t", "base_url": stub}))
    assert res["live"] is True and res["status"] == "connected"


def test_probe_without_credentials_is_not_connected():
    res = _run(probe_platform("otto", {}))
    assert res["live"] is False and res["status"] == "not_connected"


def test_unsupported_writeback_states_reason():
    with pytest.raises(CapabilityNotSupported) as e1:
        _run(SpecAdapter("tiktok", {"app_key": "k", "app_secret": "s"}).push_inventory("S", 1))
    assert e1.value.reason == "platform_unsupported"

    with pytest.raises(CapabilityNotSupported) as e2:
        _run(SpecAdapter("otto", {"client_id": "a", "client_secret": "b"}).push_listing({}))
    assert "schema" in e2.value.fix_hint


def test_amazon_uses_sigv4_and_lwa():
    a = SpecAdapter("amazon", {"client_id": "cid", "client_secret": "sec",
                               "refresh_token": "rt", "aws_access_key_id": "AKID",
                               "aws_secret_access_key": "SK"})
    import inspect
    src = inspect.getsource(type(a)._request)
    assert "sign_request" in src and "x-amz-access-token" in src
