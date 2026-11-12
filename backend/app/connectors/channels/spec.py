"""12 平台端点规格（按官方文档整理，标注可信级别）。

verified:
  official  官方文档明确给出 base URL + 路径
  inferred  官方文档给出 base URL 与资源/动作规则，路径按规则推导，首次接入需实测
  portal    端点只在零售支持门户内可见，先留可覆盖配置

所有 base_url 都允许凭证里覆盖（如 sandbox / 站点域名不同）。
"""
from typing import Dict

PLATFORM_SPEC: Dict[str, dict] = {
    "amazon": {
        "base": "https://sellingpartnerapi-eu.amazon.com",
        "auth": "lwa",
        "keys": ("client_id", "client_secret", "refresh_token",
                 "aws_access_key_id", "aws_secret_access_key"),
        "orders": ("GET", "/orders/v0/orders"),
        "messages_list": None,
        "message_send": None,
        "inventory": ("PATCH", "/listings/2021-08-01/items/{sku}"),
        "docs_url": "https://developer-docs.amazon.com/sp-api/",
        "verified": "official",
        "note": "SP-API 仅 Permitted Messages；订单需 AWS SigV4 签名",
    },
    "ebay": {
        "base": "https://api.ebay.com",
        "auth": "bearer",
        "keys": ("access_token",),
        "orders": ("GET", "/sell/fulfillment/v1/order"),
        "messages_list": None,
        "message_send": None,
        "inventory": ("POST", "/sell/inventory/v1/bulkUpdateInventory"),
        "docs_url": "https://developer.ebay.com/api-docs/",
        "verified": "official",
        "note": "消息仍需 Trading API（XML），本版本不接",
    },
    "fruugo": {
        "base": "https://api.fruugo.com",
        "auth": "basic",
        "keys": ("merchant_id", "api_key"),
        "orders": ("GET", "/orders"),
        "messages_list": None,
        "message_send": None,
        "inventory": None,
        "docs_url": "https://developer.fruugo.com/",
        "verified": "portal",
        "note": "Product API 用 Basic；Order API 文档在零售商支持门户，路径需实测",
    },
    "walmart": {
        "base": "https://marketplace.walmartapis.com",
        "auth": "header_keys",
        "keys": ("client_id", "client_secret"),
        "headers": {"WM_QOS.CORRELATION_ID": "", "WM_SVC.NAME": "Walmart Marketplace"},
        "orders": ("GET", "/v3/orders"),
        "messages_list": None,
        "message_send": None,
        "inventory": ("PUT", "/v3/inventory"),
        "docs_url": "https://developer.walmart.com/",
        "verified": "official",
        "note": "需 WMSEC 签名；买家消息未开放",
    },
    "cdiscount": {
        "base": "https://api.octopia-io.net",
        "auth": "header_keys",
        "keys": ("seller_login", "api_key"),
        "headers": {"SellerId": "{seller_login}", "Authorization": "Bearer {api_key}"},
        "orders": ("GET", "/seller/v2/orders"),
        "messages_list": None,
        "message_send": None,
        "inventory": ("POST", "/seller/v2/offers/stock"),
        "docs_url": "https://developer.octopia-io.net/api-reference/orders-management/",
        "verified": "official",
        "note": "Cdiscount 走 Octopia API；库存接口路径按 offer 管理推导",
    },
    "otto": {
        "base": "https://api.otto.market",
        "auth": "oauth2_cc",
        "keys": ("client_id", "client_secret"),
        "token_url": "https://api.otto.market/v1/token",
        "orders": ("GET", "/v2/orders"),
        "messages_list": None,
        "message_send": None,
        "inventory": ("PUT", "/v1/products/relevancy"),
        "docs_url": "https://api.otto.market/docs/about-the-api/api-guides/",
        "verified": "official",
        "note": "Bearer token；库存走产品接口，非库存单接口",
    },
    "allegro": {
        "base": "https://api.allegro.pl",
        "auth": "oauth2_refresh",
        "keys": ("client_id", "client_secret", "refresh_token"),
        "token_url": "https://allegro.pl/auth/oauth/token",
        "orders": ("GET", "/order/checkout-forms"),
        "messages_list": ("GET", "/messaging/threads"),
        "message_send": ("POST", "/messaging/threads/{thread_id}/messages"),
        "inventory": ("PATCH", "/sale/product-offers/{offer_id}"),
        "listing": ("POST", "/sale/product-offers"),
        "docs_url": "https://developer.allegro.pl/documentation",
        "verified": "official",
        "note": "唯一可读可回消息的平台；写回需 offerId 映射",
    },
    "emag": {
        "base": "https://marketplace-api.emag.ro",
        "auth": "basic",
        "keys": ("username", "password"),
        "orders": ("POST", "/api-3/order/read"),
        "messages_list": None,
        "message_send": None,
        "inventory": ("POST", "/api-3/product_offer/save"),
        "docs_url": "https://marketplace.emag.hu/infocenter/emag-academy/api-documentation/",
        "verified": "inferred",
        "note": "v4 文档为 resource/action 规则（order read/save/count），路径按规则推导",
    },
    "kaufland": {
        "base": "https://sellerapi.kaufland.com/v2",
        "auth": "header_keys",
        "keys": ("client_key", "secret_key"),
        "headers": {"Client-Key": "{client_key}", "Secret-Key": "{secret_key}"},
        "orders": ("GET", "/orders"),
        "messages_list": None,
        "message_send": None,
        "inventory": ("PUT", "/units/{unit_id}"),
        "ticket": ("POST", "/tickets"),
        "docs_url": "https://sellerapi.kaufland.com/?page=rest-api",
        "verified": "official",
        "note": "有 /tickets 可开单联系买家，但不是聊天通道",
    },
    "bol": {
        "base": "https://api.bol.com",
        "auth": "oauth2_cc",
        "keys": ("client_id", "client_secret"),
        "token_url": "https://login.bol.com/token",
        "headers": {"Accept": "application/vnd.retailer.v10+json"},
        "orders": ("GET", "/retailer/orders"),
        "messages_list": None,
        "message_send": None,
        "inventory": ("PUT", "/retailer/offers/stock"),
        "docs_url": "https://api.bol.com/retailer/public/Retailer-API/v10/reference/",
        "verified": "official",
        "note": "OAuth2 client_credentials 取 token；客服消息无公开接口",
    },
    "zalando": {
        "base": "https://api.merchants.zalando.com",
        "auth": "oauth2_cc",
        "keys": ("client_id", "client_secret", "merchant_id"),
        "token_url": "https://api.merchants.zalando.com/auth/token",
        "orders": ("GET", "/merchants/{merchant_id}/orders"),
        "messages_list": None,
        "message_send": None,
        "inventory": ("PATCH", "/merchants/{merchant_id}/stock"),
        "docs_url": "https://developers.merchants.zalando.com/docs/api-overview.html",
        "verified": "official",
        "note": "OAuth2 + Accept vnd.api+json；需 Go Live 资质",
    },
    "tiktok": {
        "base": "https://open-api.tiktokglobalshop.com",
        "auth": "tiktok_sign",
        "keys": ("app_key", "app_secret", "access_token", "shop_cipher"),
        "orders": ("GET", "/order/202309/orders/search"),
        "messages_list": ("GET", "/customer_service/202309/conversations/{conversation_id}/messages"),
        "message_send": ("POST", "/customer_service/202309/conversations/{conversation_id}/messages"),
        "inventory": ("POST", "/product/202309/products/{product_id}/inventory"),
        "docs_url": "https://partner.tiktokshop.com/docv2/page/send-message-202309",
        "verified": "official",
        "note": "消息需 Customer Service scope + 会话窗口未关闭；需 Partner 资质",
    },
}

VERIFIED_TEXT = {
    "official": "端点已在官方文档确认",
    "inferred": "base 与规则已确认，具体路径待首次实测",
    "portal": "端点仅在零售商支持门户内可见",
}


def spec_for(platform: str) -> dict:
    return PLATFORM_SPEC.get(platform, {})


def endpoint_status(platform: str) -> dict:
    s = spec_for(platform)
    if not s:
        return {"platform": platform, "verified": "unknown", "text": "未登记"}
    return {
        "platform": platform,
        "verified": s.get("verified", "inferred"),
        "text": VERIFIED_TEXT.get(s.get("verified"), "未登记"),
        "base": s.get("base", ""),
        "docs_url": s.get("docs_url", ""),
        "note": s.get("note", ""),
    }
