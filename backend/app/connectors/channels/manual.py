"""C 档人工任务通道：无 API、无邮件的平台，落任务卡让卖家后台处理。"""
from typing import List

from .base import CapabilityNotSupported, ChannelAdapter
from ..capabilities import PLATFORM_FIX_HINT, channel_tier

# 各平台卖家后台入口（用于任务卡上的"去处理"按钮）
PLATFORM_BACKOFFICE = {
    "otto": "https://partner.otto.de/",
    "kaufland": "https://sellerportal.kaufland.de/",
    "cdiscount": "https://www.cdiscount.com/",
    "emag": "https://seller.emag.ro/",
    "zalando": "https://zDirect.zalando.de/",
    "fruugo": "https://www.fruugo.com/",
    "amazon": "https://sellercentral-europe.amazon.com/",
    "walmart": "https://sellercenter.walmart.com/",
    "bol": "https://partnerplatform.bol.com/",
    "ebay": "https://www.ebay.com/sh/ovw",
    "tiktok": "https://seller.tiktokglobalshop.com/",
    "allegro": "https://allegro.pl/",
}


class ManualAdapter(ChannelAdapter):
    mode = "manual"
    tier = "C"

    def __init__(self, platform: str, payload=None, client=None):
        super().__init__(payload, client)
        self.platform = platform
        self.tier = channel_tier(platform) or "C"

    async def fetch_messages(self, since: str | None = None) -> List[dict]:
        raise CapabilityNotSupported(
            self.platform, "read_messages", "platform_unsupported",
            PLATFORM_FIX_HINT.get(self.platform, "该平台只能人工处理"))

    async def send_message(self, thread_id: str, text: str) -> dict:
        raise CapabilityNotSupported(
            self.platform, "send_message", "platform_unsupported",
            PLATFORM_FIX_HINT.get(self.platform, "该平台只能人工处理"))

    def task_payload(self, *, buyer_message: str = "", draft: str = "",
                     order_id: str = "") -> dict:
        """生成任务卡：卖家点"去处理"跳后台，处理完标记完成。"""
        return {
            "platform": self.platform,
            "backoffice_url": PLATFORM_BACKOFFICE.get(self.platform, ""),
            "order_id": order_id,
            "customer_message": buyer_message,
            "draft_reply": draft,
            "hint": PLATFORM_FIX_HINT.get(self.platform, ""),
        }
