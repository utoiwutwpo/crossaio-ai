"""Allegro A 档适配器：12 个平台里唯一能读能回全自动的一家。

端点（官方 REST，公开文档）：
  token   POST https://allegro.pl/auth/oauth/token
  threads GET  https://api.allegro.pl/messaging/threads
  messages GET/POST https://api.allegro.pl/messaging/threads/{threadId}/messages
  orders  GET  https://api.allegro.pl/order/checkout-forms
"""
from typing import List

import httpx

from .base import CapabilityNotSupported, ChannelAdapter

TOKEN_URL = "https://allegro.pl/auth/oauth/token"
API_BASE = "https://api.allegro.pl"
ACCEPT = "application/vnd.allegro.public.v1+json"


class AllegroAdapter(ChannelAdapter):
    platform = "allegro"
    mode = "api"
    tier = "A"

    def __init__(self, payload=None, client=None):
        super().__init__(payload, client)
        self._token: str = ""

    async def _access_token(self) -> str:
        if self._token:
            return self._token
        self.need("client_id", "client_secret", "refresh_token")
        c = await self.client()
        resp = await c.post(
            TOKEN_URL,
            data={"grant_type": "refresh_token",
                  "refresh_token": self.payload["refresh_token"]},
            auth=(self.payload["client_id"], self.payload["client_secret"]),
        )
        if resp.status_code != 200:
            raise CapabilityNotSupported(
                self.platform, "authorize", "not_connected",
                f"Allegro token 刷新失败（HTTP {resp.status_code}），请重新从凭证中心授权")
        data = resp.json()
        self._token = data.get("access_token", "")
        if not self._token:
            raise CapabilityNotSupported(self.platform, "authorize", "not_connected",
                                         "Allegro 未返回 access_token")
        return self._token

    async def _get(self, path: str, params: dict | None = None) -> dict:
        token = await self._access_token()
        c = await self.client()
        resp = await c.get(API_BASE + path, params=params or {},
                           headers={"Authorization": f"Bearer {token}", "Accept": ACCEPT})
        if resp.status_code >= 400:
            raise CapabilityNotSupported(
                self.platform, "read_messages", "platform_unsupported",
                f"Allegro {path} 返回 HTTP {resp.status_code}")
        return resp.json()

    async def fetch_messages(self, since: str | None = None) -> List[dict]:
        """拉最近会话及其消息，归一化为统一结构。"""
        data = await self._get("/messaging/threads", {"limit": 20})
        out: List[dict] = []
        for thread in data.get("threads", [])[:20]:
            tid = thread.get("id")
            if not tid:
                continue
            msgs = await self._get(f"/messaging/threads/{tid}/messages", {"limit": 20})
            for m in msgs.get("messages", []):
                out.append({
                    "platform": self.platform,
                    "external_thread_id": tid,
                    "external_message_id": m.get("id", ""),
                    "buyer_id": (m.get("author") or {}).get("login", ""),
                    "subject": thread.get("subject", ""),
                    "body": m.get("text", ""),
                    "direction": "incoming" if m.get("author", {}).get("isInterlocutor") else "outgoing",
                    "created_at": m.get("createdAt", ""),
                })
        return out

    async def send_message(self, thread_id: str, text: str) -> dict:
        token = await self._access_token()
        c = await self.client()
        resp = await c.post(
            f"{API_BASE}/messaging/threads/{thread_id}/messages",
            json={"text": text},
            headers={"Authorization": f"Bearer {token}", "Accept": ACCEPT},
        )
        if resp.status_code >= 400:
            raise CapabilityNotSupported(
                self.platform, "send_message", "platform_unsupported",
                f"Allegro 回帖失败 HTTP {resp.status_code}，请手工在后台回复")
        data = resp.json() if resp.content else {}
        return {"platform": self.platform, "thread_id": thread_id,
                "message_id": data.get("id", ""), "sent": bool(data.get("id"))}

    async def fetch_orders(self, since: str | None = None) -> List[dict]:
        data = await self._get("/order/checkout-forms", {"limit": 20})
        return [{
            "platform": self.platform,
            "order_id": o.get("id", ""),
            "status": o.get("status", ""),
            "buyer": ((o.get("buyer") or {}).get("login", "")),
            "total": ((o.get("summary") or {}).get("totalToPay") or {}).get("amount", ""),
        } for o in data.get("checkoutForms", [])]

    async def push_listing(self, payload: dict) -> dict:
        """POST /sale/product-offers：payload 必须是完整 productSet（缺字段会 422）。"""
        token = await self._access_token()
        c = await self.client()
        resp = await c.post(f"{API_BASE}/sale/product-offers", json=payload,
                            headers={"Authorization": f"Bearer {token}", "Accept": ACCEPT})
        if resp.status_code >= 400:
            raise CapabilityNotSupported(
                self.platform, "write_listing", "platform_unsupported",
                f"Allegro 建 offer 失败 HTTP {resp.status_code}（多为缺 productSet 必填字段）")
        data = resp.json() if resp.content else {}
        return {"platform": self.platform, "offer_id": data.get("id", ""),
                "written": bool(data.get("id"))}

    async def push_inventory(self, sku: str, quantity: int, **kw) -> dict:
        """PATCH /sale/product-offers/{offerId}：官方推荐改库存方式。"""
        offer_id = kw.get("offer_id") or self.payload.get("offer_id_map", {}).get(sku)
        if not offer_id:
            raise CapabilityNotSupported(
                self.platform, "write_inventory", "platform_unsupported",
                "Allegro 改库存需 offerId；请在凭证里填 offer_id_map 映射")
        token = await self._access_token()
        c = await self.client()
        resp = await c.patch(
            f"{API_BASE}/sale/product-offers/{offer_id}",
            json={"stock": {"available": int(quantity)}},
            headers={"Authorization": f"Bearer {token}", "Accept": ACCEPT},
        )
        if resp.status_code >= 400:
            raise CapabilityNotSupported(
                self.platform, "write_inventory", "platform_unsupported",
                f"Allegro 改库存失败 HTTP {resp.status_code}")
        return {"platform": self.platform, "offer_id": offer_id,
                "quantity": int(quantity), "written": True}
