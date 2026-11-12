"""适配器注册表：12 平台 → 4 类实现（不写 13 套）。"""
from typing import Optional

import httpx

from ..capabilities import CHANNELS, channel_tier
from .allegro import AllegroAdapter
from .base import CapabilityNotSupported, ChannelAdapter
from .email import EmailChannel
from .manual import ManualAdapter
from .partial_api import PartialApiAdapter
from .regional import SpecAdapter
from .spec import endpoint_status

# 有官方文档端点、走规格驱动适配器的平台
SPEC_PLATFORMS = ("tiktok", "kaufland", "otto", "emag", "zalando", "cdiscount",
                  "fruugo", "ebay", "bol", "amazon")


def adapter_for(platform: str, payload: Optional[dict] = None,
                client: Optional[httpx.AsyncClient] = None) -> ChannelAdapter:
    p = (platform or "").strip().lower()
    if p not in CHANNELS:
        raise CapabilityNotSupported(p, "connect", "platform_unsupported",
                                     "未知平台，仅支持 13 个已登记平台")
    if p == "allegro":
        return AllegroAdapter(payload, client)
    if p in SPEC_PLATFORMS:
        return SpecAdapter(p, payload, client)
    ch = CHANNELS[p]
    if ch["mode"] == "email":
        return EmailChannel(p, payload, client)
    if ch["mode"] == "manual":
        return ManualAdapter(p, payload, client)
    return PartialApiAdapter(p, payload, client)


def describe(platform: str) -> dict:
    ch = CHANNELS.get(platform) or {}
    ep = endpoint_status(platform)
    return {
        "platform": platform,
        "tier": channel_tier(platform),
        "mode": ch.get("mode"),
        "adapter": type(adapter_for(platform)).__name__,
        "endpoint_verified": ep.get("verified"),
        "docs_url": ep.get("docs_url"),
    }
