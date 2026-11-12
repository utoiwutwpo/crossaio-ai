"""规格驱动平台适配器（第二轮：SigV4 直连 + 6 家真实写回）。

鉴权：basic / header_keys / bearer / oauth2_cc / tiktok_sign / lwa(SigV4)
写回：allegro、amazon、ebay、kaufland、bol、walmart、emag
未实现写回的（otto/zalando/fruugo/cdiscount/tiktok）明确抛带原因的能力异常，
不假装成功。
"""
import hashlib
import hmac
import json
import time
from typing import List

import httpx

from ..aws_sign import sign_request
from .base import CapabilityNotSupported, ChannelAdapter
from .spec import PLATFORM_SPEC

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"


class SpecAdapter(ChannelAdapter):
    mode = "api"

    def __init__(self, platform: str, payload=None, client=None):
        super().__init__(payload, client)
        self.platform = platform
        self.spec = PLATFORM_SPEC.get(platform, {})
        self.tier = "B" if self.spec.get("messages_list") else "C"
        self._token = ""
        self._lwa = ""

    # ---------------- 鉴权 ----------------
    def _base(self) -> str:
        return (self.payload.get("base_url") or self.spec.get("base") or "").rstrip("/")

    def _fmt(self, value: str) -> str:
        return (value or "").format(**self.payload)

    def _map(self, sku: str) -> dict:
        m = (self.payload.get("listing_map") or {}).get(sku)
        if isinstance(m, dict):
            return m
        return {}

    async def _auth_headers(self) -> dict:
        style = self.spec.get("auth", "")
        if style in ("basic", "header_keys", "bearer", "oauth2_cc",
                     "tiktok_sign", "lwa"):
            self.need(*self.spec.get("keys", ()))
        headers = {"Accept": "application/json"}
        for k, v in (self.spec.get("headers") or {}).items():
            headers[k] = self._fmt(v) if v else (self.payload.get("correlation_id") or "crossaio")
        return headers

    async def _access_token(self) -> str:
        if self._token:
            return self._token
        url = self.payload.get("token_url") or self.spec.get("token_url")
        if not url:
            raise CapabilityNotSupported(self.platform, "authorize", "not_connected",
                                         "未配置 token_url")
        c = await self.client()
        resp = await c.post(url, data={"grant_type": "client_credentials"},
                            auth=(self.payload["client_id"], self.payload["client_secret"]))
        if resp.status_code != 200:
            raise CapabilityNotSupported(
                self.platform, "authorize", "not_connected",
                f"{self.platform} 取 token 失败 HTTP {resp.status_code}，请核对 client_id/secret")
        self._token = resp.json().get("access_token", "")
        return self._token

    async def _lwa_token(self) -> str:
        if self._lwa:
            return self._lwa
        if not self.payload.get("refresh_token"):
            raise CapabilityNotSupported(
                self.platform, "authorize", "not_connected",
                "Amazon 需 LWA refresh_token（卖家授权后由 SP-API 应用获得）")
        c = await self.client()
        resp = await c.post(LWA_TOKEN_URL, data={
            "grant_type": "refresh_token",
            "refresh_token": self.payload["refresh_token"],
            "client_id": self.payload["client_id"],
            "client_secret": self.payload["client_secret"]})
        if resp.status_code != 200:
            raise CapabilityNotSupported(
                self.platform, "authorize", "not_connected",
                f"LWA 换 token 失败 HTTP {resp.status_code}")
        self._lwa = resp.json().get("access_token", "")
        return self._lwa

    # ---------------- 请求 ----------------
    async def _request(self, method: str, path: str, *, params=None, json=None,
                       action: str = "read_orders") -> httpx.Response:
        base = self._base()
        if not base:
            raise CapabilityNotSupported(self.platform, action, "not_connected", "缺少 base_url")
        style = self.spec.get("auth", "")
        c = await self.client()
        headers = await self._auth_headers()
        auth = None
        body_bytes = b""

        if style == "basic":
            auth = (self.payload[self.spec["keys"][0]], self.payload[self.spec["keys"][1]])
        elif style == "bearer":
            headers["Authorization"] = f"Bearer {self.payload.get('access_token', '')}"
        elif style == "oauth2_cc":
            headers["Authorization"] = f"Bearer {await self._access_token()}"
        elif style == "tiktok_sign":
            ts = str(int(time.time()))
            q = {"app_key": self.payload["app_key"], "timestamp": ts,
                 "shop_cipher": self.payload.get("shop_cipher", "")}
            if params:
                q.update({k: str(v) for k, v in params.items()})
            sign_str = self.payload["app_secret"] + path + "".join(f"{k}{q[k]}" for k in sorted(q))
            if json:
                sign_str += json.dumps(json, separators=(",", ":"))
            q["sign"] = hmac.new(self.payload["app_secret"].encode(),
                                 sign_str.encode(), hashlib.sha256).hexdigest()
            params = q
            headers["x-tts-access-token"] = self.payload.get("access_token", "")
        elif style == "lwa":
            token = await self._lwa_token()
            headers["x-amz-access-token"] = token
            host = base.split("://", 1)[-1].split("/")[0]
            body_bytes = json.dumps(json, separators=(",", ":")).encode() if json else b""
            signed = sign_request(
                method=method, url_path=path, query=params or {},
                headers={"host": host, "x-amz-access-token": token},
                payload=body_bytes,
                access_key=self.payload["aws_access_key_id"],
                secret_key=self.payload["aws_secret_access_key"],
                region=self.payload.get("region", "eu-west-1"),
                service="execute-api")
            headers.update({k: v for k, v in signed.items() if k != "host"})

        resp = await c.request(method, base + path, params=params, json=json,
                               headers=headers, auth=auth, content=body_bytes or None)
        if resp.status_code >= 400:
            raise CapabilityNotSupported(
                self.platform, action, "platform_unsupported",
                f"{self.platform} {method} {path} 返回 HTTP {resp.status_code}；"
                "请在卖家后台核对权限或改用人工处理")
        return resp

    # ---------------- 订单 ----------------
    async def fetch_orders(self, since: str | None = None) -> List[dict]:
        method, path = self.spec.get("orders", ("GET", ""))
        if not path:
            raise CapabilityNotSupported(self.platform, "read_orders", "platform_unsupported",
                                         f"{self.platform} 无订单接口")
        if not self.payload:
            raise CapabilityNotSupported(self.platform, "read_orders", "not_connected",
                                         f"{self.platform} 尚未保存凭证")
        body = {"page": 1, "items_per_page": 20} if method == "POST" else None
        resp = await self._request(method, path, params={"limit": 20} if method == "GET" else None,
                                   json=body, action="read_orders")
        data = resp.json()
        rows = data.get("orders") or data.get("results") or data.get("data") or []
        if isinstance(rows, dict):
            rows = rows.get("orders") or rows.get("items") or []
        out = []
        for o in rows[:20] if isinstance(rows, list) else []:
            if not isinstance(o, dict):
                continue
            out.append({"platform": self.platform,
                        "order_id": str(o.get("order_id") or o.get("id") or o.get("orderId") or ""),
                        "status": str(o.get("status") or o.get("state") or ""),
                        "buyer": str(o.get("buyer") or o.get("customer") or ""),
                        "total": str(o.get("total") or o.get("amount") or "")})
        return out

    # ---------------- 消息 ----------------
    async def fetch_messages(self, since: str | None = None) -> List[dict]:
        if not self.spec.get("messages_list"):
            raise CapabilityNotSupported(
                self.platform, "read_messages", "platform_unsupported",
                f"{self.platform} 无公开买家消息读取接口，请在卖家后台处理")
        conv = self.payload.get("conversation_id")
        if not conv:
            raise CapabilityNotSupported(
                self.platform, "read_messages", "not_connected",
                f"{self.platform} 需先填 conversation_id")
        method, tpl = self.spec["messages_list"]
        resp = await self._request(method, tpl.format(conversation_id=conv),
                                   params={"page_size": 20}, action="read_messages")
        data = resp.json()
        rows = data.get("messages") or (data.get("data") or {}).get("messages") or []
        return [{"platform": self.platform, "external_thread_id": conv,
                 "external_message_id": str(m.get("id", "")),
                 "buyer_id": str(m.get("sender_id") or m.get("buyer_id") or ""),
                 "body": m.get("content") or m.get("text") or "",
                 "direction": "incoming" if m.get("sender_role") in (1, "buyer") else "outgoing",
                 "created_at": str(m.get("create_time", ""))} for m in rows if isinstance(m, dict)]

    async def send_message(self, thread_id: str, text: str) -> dict:
        if not self.spec.get("message_send"):
            raise CapabilityNotSupported(self.platform, "send_message",
                                         "platform_unsupported",
                                         f"{self.platform} 无公开消息发送接口")
        method, tpl = self.spec["message_send"]
        resp = await self._request(method, tpl.format(conversation_id=thread_id),
                                   json={"content": text}, action="send_message")
        data = resp.json() if resp.content else {}
        return {"platform": self.platform, "thread_id": thread_id, "sent": True,
                "raw_id": str((data.get("data") or {}).get("message_id", ""))}

    # ---------------- 库存写回 ----------------
    async def push_inventory(self, sku: str, quantity: int, **kw) -> dict:
        q = int(quantity)
        if self.platform == "allegro":
            offer_id = kw.get("offer_id") or self._map(sku).get("offer_id")
            if not offer_id:
                raise CapabilityNotSupported(self.platform, "write_inventory",
                                             "platform_unsupported",
                                             "Allegro 写库存需 offer_id（listing_map 映射）")
            await self._request("PATCH", f"/sale/product-offers/{offer_id}",
                                json={"stock": {"available": q}}, action="write_inventory")
            return {"platform": self.platform, "offer_id": offer_id, "quantity": q,
                    "written": True}

        if self.platform == "kaufland":
            unit_id = kw.get("unit_id") or self._map(sku).get("unit_id")
            if not unit_id:
                raise CapabilityNotSupported(self.platform, "write_inventory",
                                             "platform_unsupported",
                                             "Kaufland 写库存需 unit_id（listing_map 映射）")
            await self._request("PATCH", f"/units/{unit_id}",
                                json={"quantity": q}, action="write_inventory")
            return {"platform": self.platform, "unit_id": unit_id, "quantity": q,
                    "written": True}

        if self.platform == "ebay":
            await self._request("PUT", f"/sell/inventory/v1/inventory/{sku}",
                                json={"availability": {"shipToLocationAvailability":
                                                       {"quantity": q}}},
                                action="write_inventory")
            return {"platform": "ebay", "sku": sku, "quantity": q, "written": True}

        if self.platform == "walmart":
            await self._request("PUT", "/v3/inventory",
                                params={"sku": sku},
                                json={"sku": sku, "quantity": {"unit": "EACH", "amount": q}},
                                action="write_inventory")
            return {"platform": "walmart", "sku": sku, "quantity": q, "written": True}

        if self.platform == "emag":
            offer_id = self._map(sku).get("offer_id") or sku
            await self._request("POST", "/api-3/product_offer/save",
                                json={"id": offer_id, "stock": q},
                                action="write_inventory")
            return {"platform": "emag", "offer_id": offer_id, "quantity": q, "written": True}

        if self.platform == "amazon":
            await self._request("PATCH", f"/listings/2021-08-01/items/{sku}",
                                json={"productType": "PET_PRODUCT",
                                      "patches": [{"op": "replace", "path": "/attributes/fulfillment_availability",
                                                   "value": [{"fulfillment_channel_code": "DEFAULT",
                                                              "quantity": q}]}]},
                                action="write_inventory")
            return {"platform": "amazon", "sku": sku, "quantity": q, "written": True}

        if self.platform == "bol":
            offer_id = self._map(sku).get("offer_id")
            if not offer_id:
                raise CapabilityNotSupported(self.platform, "write_inventory",
                                             "platform_unsupported",
                                             "bol 改库存需 offer_id（且要带价格，走 offer 全量更新）")
            await self._request("PUT", f"/retailer/offers/{offer_id}",
                                json={"quantity": q}, action="write_inventory")
            return {"platform": "bol", "offer_id": offer_id, "quantity": q, "written": True}

        raise CapabilityNotSupported(
            self.platform, "write_inventory", "platform_unsupported",
            f"{self.platform} 无公开库存写接口或需类目 schema，请在卖家后台更新")

    # ---------------- Listing 写回 ----------------
    async def push_listing(self, payload: dict) -> dict:
        if self.platform == "allegro":
            await self._request("POST", "/sale/product-offers", json=payload, action="write_listing")
            return {"platform": "allegro", "written": True}

        if self.platform == "ebay":
            sku = payload["sku"]
            await self._request("PUT", f"/sell/inventory/v1/inventory/{sku}",
                                json=payload["inventory_item"], action="write_listing")
            resp = await self._request("POST", "/sell/inventory/v1/offer",
                                       json=payload["offer"], action="write_listing")
            offer_id = resp.json().get("offerId", "")
            if offer_id:
                await self._request("POST", f"/sell/inventory/v1/offer/{offer_id}/publish",
                                    action="write_listing")
            return {"platform": "ebay", "offer_id": offer_id, "written": True}

        if self.platform == "bol":
            resp = await self._request("POST", "/retailer/offers", json=payload,
                                       action="write_listing")
            return {"platform": "bol", "process_id":
                    str(resp.json().get("processStatusId", "")), "written": True}

        if self.platform == "kaufland":
            resp = await self._request("POST", "/units", json=payload, action="write_listing")
            return {"platform": "kaufland",
                    "unit_id": str((resp.json().get("data") or {}).get("id_unit", "")),
                    "written": True}

        if self.platform == "emag":
            resp = await self._request("POST", "/api-3/product_offer/save", json=payload,
                                       action="write_listing")
            return {"platform": "emag", "written": True,
                    "raw": str(resp.json())[:120]}

        if self.platform == "amazon":
            sku = payload["sku"]
            await self._request("PATCH", f"/listings/2021-08-01/items/{sku}",
                                json={"productType": payload.get("product_type", "PET_PRODUCT"),
                                      "patches": payload["patches"]}, action="write_listing")
            return {"platform": "amazon", "sku": sku, "written": True}

        if self.platform == "walmart":
            xml = (payload or {}).get("xml") or ""
            if not xml:
                raise CapabilityNotSupported(
                    "walmart", "write_listing", "platform_unsupported",
                    "Walmart 建品走 MP_ITEM XML feed，当前 payload 未带 XML")
            consumer_id = self.payload.get("consumer_id") or self.payload.get("client_id")
            private_key = self.payload.get("private_key") or self.payload.get("private_key_pem")
            if not (consumer_id and private_key):
                raise CapabilityNotSupported(
                    "walmart", "write_listing", "not_connected",
                    "Walmart feed 需 consumer_id + RSA private_key（WMSEC 签名）")
            headers = await self._walmart_headers(consumer_id, private_key)
            c = await self.client()
            resp = await c.post(self._base() + "/v3/feeds",
                                params={"feedType": "MP_ITEM"},
                                headers=headers,
                                files={"file": ("items.xml", xml.encode("utf-8"),
                                                "application/xml")})
            if resp.status_code >= 400:
                raise CapabilityNotSupported(
                    "walmart", "write_listing", "platform_unsupported",
                    f"Walmart feed 返回 HTTP {resp.status_code}；请核对签名/类目模板")
            data = resp.json() if resp.content else {}
            return {"platform": "walmart", "feed_id": str(data.get("feedId", "")),
                    "written": True}

        if self.platform == "otto":
            raise CapabilityNotSupported(
                "otto", "write_listing", "platform_unsupported",
                "OTTO 建品需 partner 专属 product schema，本版本只生成待提交 payload")

        raise CapabilityNotSupported(
            self.platform, "write_listing", "platform_unsupported",
            f"{self.platform} 无公开商品写接口，请在卖家后台创建")

    async def _walmart_headers(self, consumer_id: str, private_key: str) -> dict:
        import base64
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        ts = str(int(time.time() * 1000))
        key_version = str(self.payload.get("key_version") or "1")
        sign_str = f"{consumer_id}\n{ts}\n{key_version}".encode()
        key = serialization.load_pem_private_key(private_key.encode(), password=None)
        sig = key.sign(sign_str, padding.PKCS1v15(), hashes.SHA256())
        return {
            "WM_SEC.AUTH_SIGNATURE": base64.b64encode(sig).decode(),
            "WM_SEC.KEY_VERSION": key_version,
            "WM_CONSUMER.ID": consumer_id,
            "WM_CONSUMER.INTIMESTAMP": ts,
            "WM_SVC.NAME": "Walmart Marketplace",
            "WM_QOS.CORRELATION_ID": str(int(time.time())),
            "Accept": "application/xml",
        }