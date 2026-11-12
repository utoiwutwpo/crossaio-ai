"""B 档适配器：有官方 API 但消息能力受限（permitted_only / legacy / unverified）。

设计取舍：本版本不伪造订单与消息数据。能做的（有凭证 + 已实现）才做，
其余一律抛 CapabilityNotSupported 并给出"去哪个后台处理"的具体指引。
"""
from .base import CapabilityNotSupported, ChannelAdapter
from ..capabilities import CHANNELS, PLATFORM_FIX_HINT


class PartialApiAdapter(ChannelAdapter):
    mode = "api_limited"

    def __init__(self, platform: str, payload=None, client=None):
        super().__init__(payload, client)
        self.platform = platform
        self.tier = (CHANNELS.get(platform) or {}).get("tier", "B")

    def _hint(self, action: str) -> str:
        return PLATFORM_FIX_HINT.get(self.platform, "") or \
            f"{self.platform} 不支持该动作，请在卖家后台处理"

    async def fetch_messages(self, since: str | None = None):
        raise CapabilityNotSupported(self.platform, "read_messages",
                                     "platform_unsupported", self._hint("read_messages"))

    async def send_message(self, thread_id: str, text: str):
        raise CapabilityNotSupported(self.platform, "send_message",
                                     "platform_unsupported", self._hint("send_message"))

    async def fetch_orders(self, since: str | None = None):
        raise CapabilityNotSupported(
            self.platform, "read_orders", "platform_unsupported",
            f"{self.platform} 订单拉取需额外签名密钥（如 SP-API 的 AWS 凭证），"
            "本版本请用平台后台导出 CSV 后导入")

    async def push_listing(self, payload: dict):
        raise CapabilityNotSupported(
            self.platform, "write_listing", "platform_unsupported",
            f"{self.platform} 写回需平台特定签名与类目 schema，本版本输出待提交 payload")

    async def push_inventory(self, sku: str, quantity: int):
        raise CapabilityNotSupported(
            self.platform, "write_inventory", "platform_unsupported",
            f"{self.platform} 库存写回需 offer/SKU 映射，请在后台调整")
