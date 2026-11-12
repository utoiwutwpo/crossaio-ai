"""通道适配器：把 12 个平台抽象成同一组方法。

契约（命门）：做不到的动作必须抛 CapabilityNotSupported，不允许返回 False
让上层流程继续——否则商家会看到"已发送"而实际没发出去。
"""
from typing import Any, Dict, List, Optional

import httpx


class CapabilityNotSupported(Exception):
    """平台/套餐层面明确不支持该动作。"""

    def __init__(self, platform: str, action: str,
                 reason: str = "platform_unsupported", fix_hint: str = ""):
        self.platform = platform
        self.action = action
        self.reason = reason
        self.fix_hint = fix_hint
        super().__init__(f"{platform}.{action} unsupported: {reason}")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "action": self.action,
            "reason_code": self.reason,
            "hint": self.fix_hint,
        }


class ChannelAdapter:
    """所有适配器的基类；默认全部抛不支持，子类按能力覆盖。"""

    platform: str = ""
    mode: str = "manual"     # api / api_limited / email / manual
    tier: str = "C"
    timeout: float = 20.0

    def __init__(self, payload: Optional[dict] = None,
                 client: Optional[httpx.AsyncClient] = None):
        self.payload = payload or {}
        self._client = client

    async def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    def need(self, *keys: str) -> None:
        missing = [k for k in keys if not (self.payload.get(k) or "").strip()]
        if missing:
            raise CapabilityNotSupported(
                self.platform, "authorize", "not_connected",
                f"{self.platform} 缺少凭证字段：{', '.join(missing)}")

    # ---------- 统一接口 ----------
    async def fetch_messages(self, since: str | None = None) -> List[dict]:
        raise CapabilityNotSupported(self.platform, "read_messages", "platform_unsupported",
                                     f"{self.platform} 无公开买家消息读取接口")

    async def send_message(self, thread_id: str, text: str) -> dict:
        raise CapabilityNotSupported(self.platform, "send_message", "platform_unsupported",
                                     f"{self.platform} 无公开消息发送接口")

    async def fetch_orders(self, since: str | None = None) -> List[dict]:
        raise CapabilityNotSupported(self.platform, "read_orders", "platform_unsupported",
                                     f"{self.platform} 订单接口未实现")

    async def push_listing(self, payload: dict) -> dict:
        raise CapabilityNotSupported(self.platform, "write_listing", "platform_unsupported",
                                     f"{self.platform} listing 写回未实现")

    async def push_inventory(self, sku: str, quantity: int) -> dict:
        raise CapabilityNotSupported(self.platform, "write_inventory", "platform_unsupported",
                                     f"{self.platform} 库存写回未实现")
