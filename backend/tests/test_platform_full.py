"""13 平台全打通 + 可售卖：规格、适配器分派、加购包、资质开关。"""
import asyncio

import pytest

from app.billing import ADDON_CATALOG, addon_price
from app.connectors.capabilities import CHANNELS
from app.connectors.channels.allegro import AllegroAdapter
from app.connectors.channels.base import CapabilityNotSupported
from app.connectors.channels.registry import SPEC_PLATFORMS, adapter_for
from app.connectors.channels.regional import SpecAdapter
from app.connectors.channels.spec import PLATFORM_SPEC, endpoint_status


def _run(coro):
    """不 close loop：后续既有用例仍用 get_event_loop()。"""
    loop = asyncio.get_event_loop_policy().get_event_loop()
    return loop.run_until_complete(coro)


def test_all_13_platforms_have_spec():
    assert set(PLATFORM_SPEC) == set(CHANNELS)
    assert len(CHANNELS) == 13


def test_endpoint_status_has_docs_url():
    for p in CHANNELS:
        ep = endpoint_status(p)
        assert ep["verified"] in ("official", "inferred", "portal")
        assert ep["docs_url"].startswith("http")
        assert ep["base"].startswith("http")


def test_official_endpoint_count():
    kinds = [endpoint_status(p)["verified"] for p in CHANNELS]
    assert kinds.count("official") >= 9     # 至少 9 家 base+路径已官方确认
    assert kinds.count("inferred") <= 2


def test_registry_routes_all_13():
    for p in CHANNELS:
        a = adapter_for(p)
        assert a.platform == p or p in ("amazon", "amazon_us")


def test_registry_uses_spec_adapter_for_regional():
    for p in ("kaufland", "otto", "emag", "zalando", "cdiscount", "fruugo", "tiktok"):
        assert isinstance(adapter_for(p), SpecAdapter)


def test_allegro_still_dedicated():
    assert isinstance(adapter_for("allegro"), AllegroAdapter)


def test_spec_adapter_requires_credentials():
    a = SpecAdapter("kaufland", {})
    with pytest.raises(CapabilityNotSupported) as exc:
        _run(a.fetch_orders())
    assert exc.value.reason == "not_connected"


def test_amazon_requires_aws_keys_for_sigv4():
    a = adapter_for("amazon", {"client_id": "x", "client_secret": "y",
                               "refresh_token": "z"})
    with pytest.raises(CapabilityNotSupported) as exc:
        _run(a.fetch_orders())
    assert exc.value.reason == "not_connected"
    assert "aws" in exc.value.fix_hint.lower()


def test_allegro_inventory_needs_offer_id():
    a = AllegroAdapter({"offer_id_map": {}})
    with pytest.raises(CapabilityNotSupported) as exc:
        _run(a.push_inventory("SKU-1", 5))
    assert "offerId" in exc.value.fix_hint or "offer_id" in exc.value.fix_hint.lower()


def test_addon_catalog_prices():
    assert addon_price("extra_shop") == 29.0
    assert addon_price("extra_seat") == 6.0
    assert addon_price("auto_reply") == 0.90
    assert addon_price("incident") == 15.0
    assert set(ADDON_CATALOG) == {"extra_shop", "extra_seat", "auto_reply", "incident"}


def test_schema_has_provenance_field():
    from app.schemas import ProductDescriptionResponse
    fields = ProductDescriptionResponse.model_fields
    assert "provenance" in fields
