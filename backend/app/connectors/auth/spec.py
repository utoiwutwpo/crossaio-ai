"""12 平台店铺授权规格表。

诚实标注（stage）：
  confirmed   —— 授权端点已在公开文档核实，允许发起真实网络校验
  unconfirmed —— 只做凭证形状校验，端点未经核实，绝不臆造 URL

github 字段记录同类开源实现的参考仓库（仅作协议形状参考，运行时不引入依赖）。
"""
from typing import Dict, List, Optional

PLATFORM_ORDER: List[str] = [
    "amazon", "ebay", "fruugo", "walmart",
    "cdiscount", "otto", "allegro", "emag", "kaufland",
    "bol", "zalando", "tiktok",
]

AUTH_SPECS: Dict[str, dict] = {
    "amazon": {
        "label": "Amazon 欧洲站",
        "auth_type": "lwa_refresh_token",
        "fields": ["client_id", "client_secret", "refresh_token"],
        "stage": "confirmed",
        "token_url": "https://api.amazon.com/auth/o2/token",
        "api_base": "https://sellingpartnerapi-eu.amazon.com",
        "docs": "https://developer-docs.amazon.com/sp-api/",
        "github": "saleweaver/python-amazon-sp-api",
        "live_check": "token",
        "scope": "",
    },
    "ebay": {
        "label": "eBay",
        "auth_type": "oauth2_code",
        "fields": ["client_id", "client_secret"],
        "stage": "confirmed",
        "authorize_url": "https://auth.ebay.com/oauth2/authorize",
        "token_url": "https://api.ebay.com/identity/v1/oauth2/token",
        "api_base": "https://api.ebay.com",
        "docs": "https://developer.ebay.com/api-docs/static/oauth-tokens.html",
        "github": "timotheus/ebaysdk-python",
        "live_check": "none",
        "scope": "https://api.ebay.com/oauth/api_scope/sell.inventory "
                 "https://api.ebay.com/oauth/api_scope/sell.messaging",
    },
    "fruugo": {
        "label": "Fruugo",
        "auth_type": "api_key",
        "fields": ["merchant_id", "api_key"],
        "stage": "unconfirmed",
        "token_url": None,
        "api_base": None,
        "docs": "https://merchant.fruugo.com/",
        "github": None,
        "live_check": "shape",
        "scope": "",
    },
    "walmart": {
        "label": "Walmart",
        "auth_type": "oauth2_client_credentials",
        "fields": ["client_id", "client_secret"],
        "stage": "confirmed",
        "token_url": "https://marketplace.walmartapis.com/v3/token",
        "api_base": "https://marketplace.walmartapis.com",
        "docs": "https://developer.walmart.com/",
        "github": "whitebox-co/walmart-marketplace-api",
        "live_check": "token",
        "scope": "",
    },
    "cdiscount": {
        "label": "Cdiscount",
        "auth_type": "legacy_key",
        "fields": ["api_key", "seller_login"],
        "stage": "unconfirmed",
        "token_url": None,
        "api_base": None,
        "docs": "https://dev.cdiscount.com/",
        "github": "yangguo306/cdiscount-sdk",
        "live_check": "shape",
        "scope": "",
    },
    "otto": {
        "label": "Otto",
        "auth_type": "oauth2_client_credentials",
        "fields": ["client_id", "client_secret"],
        "stage": "unconfirmed",
        "token_url": None,
        "api_base": None,
        "docs": "https://public-docs.live.api.otto.market/",
        "github": "otto-de/marketplace-php-sdk",
        "live_check": "shape",
        "scope": "",
    },
    "allegro": {
        "label": "Allegro",
        "auth_type": "oauth2_code",
        "fields": ["client_id", "client_secret"],
        "stage": "confirmed",
        "authorize_url": "https://allegro.pl/auth/oauth/authorize",
        "token_url": "https://allegro.pl/auth/oauth/token",
        "api_base": "https://api.allegro.pl",
        "docs": "https://developer.allegro.pl/",
        "github": "chawel/python-allegro",
        "live_check": "none",
        "scope": "allegro:api:sale:offers:read allegro:api:messaging",
    },
    "emag": {
        "label": "eMAG",
        "auth_type": "api_token",
        "fields": ["api_key"],
        "stage": "unconfirmed",
        "token_url": None,
        "api_base": None,
        "docs": "https://marketplace.emag.eu/",
        "github": "chawel/python-emag",
        "live_check": "shape",
        "scope": "",
    },
    "kaufland": {
        "label": "Kaufland Global",
        "auth_type": "header_keys",
        "fields": ["client_key", "secret_key"],
        "stage": "unconfirmed",
        "token_url": None,
        "api_base": None,
        "docs": "https://seller.kaufland.de/",
        "github": "saleweaver/python-kaufland-api",
        "live_check": "shape",
        "scope": "",
    },
    "bol": {
        "label": "bol.com",
        "auth_type": "oauth2_client_credentials",
        "fields": ["client_id", "client_secret"],
        "stage": "confirmed",
        "token_url": "https://login.bol.com/token",
        "api_base": "https://api.bol.com",
        "docs": "https://developer.bol.com/",
        "github": "pennersr/python-bol-api",
        "live_check": "token",
        "scope": "",
    },
    "zalando": {
        "label": "Zalando",
        "auth_type": "oauth2_client_credentials",
        "fields": ["client_id", "client_secret"],
        "stage": "unconfirmed",
        "token_url": None,
        "api_base": None,
        "docs": "https://partners.zalando.de/",
        "github": "sbaumeister/zalando-zdirect-client-php",
        "live_check": "shape",
        "scope": "",
    },
    "tiktok": {
        "label": "TikTok Shop",
        "auth_type": "oauth2_code",
        "fields": ["app_key", "app_secret"],
        "stage": "unconfirmed",
        "authorize_url": None,
        "token_url": None,
        "api_base": None,
        "docs": "https://partner.tiktokshop.com/",
        "github": "EcomPHP/tiktokshop-php",
        "live_check": "shape",
        "scope": "",
    },
}

# 字段中文提示（凭证中心表单用；四语种文案在 i18n 层）
FIELD_LABELS: Dict[str, str] = {
    "client_id": "Client ID",
    "client_secret": "Client Secret",
    "refresh_token": "Refresh Token",
    "client_key": "Client Key",
    "secret_key": "Secret Key",
    "api_key": "API Key",
    "seller_login": "卖家登录名",
    "merchant_id": "Merchant ID",
    "app_key": "App Key",
    "app_secret": "App Secret",
}


def get_spec(platform: str) -> Optional[dict]:
    return AUTH_SPECS.get(platform)


def all_specs() -> List[dict]:
    return [dict(AUTH_SPECS[p], platform=p) for p in PLATFORM_ORDER]


def supports_authorize_url(platform: str) -> bool:
    spec = AUTH_SPECS.get(platform) or {}
    return bool(spec.get("authorize_url"))
