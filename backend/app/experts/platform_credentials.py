"""13 平台商家自助接入注册表 — 每个平台的凭证字段、官方申请入口与门槛说明。

设计原则（诚实营销）：
- 只列该平台真实存在的凭证字段与官方申请 URL，不编造"一键接入"。
- 门槛（是否需要开发者审核、是否免费、卖家账号要求）如实标注。
- eBay 用户级走 OAuth（eBayConnection），不在粘贴流程内。
"""
from typing import Dict, List

# 每字段：(key, 中文名, 是否敏感(显示为密码框), 帮助文案)
_C = List[tuple]

PLATFORM_CRED_REGISTRY: Dict[str, dict] = {
    "amazon": {
        "label": "Amazon 欧洲站",
        "apply_url": "https://sellercentral.amazon.de/sw/user/central-developer",
        "apply_note": "Seller Central → 集成 → 开发者，注册 LWA 应用；专业卖家账户可申请，部分权限需 Amazon 审核（1~3 天）。",
        "fields": [
            ("client_id", "LWA Client ID", False, "开发者档案页 Client ID"),
            ("client_secret", "LWA Client Secret", True, "与 Client ID 同页"),
            ("refresh_token", "卖家 Refresh Token", True, "授权卖家档案后换取，长期有效"),
        ],
        "unlocks": "合规块真实写回 Amazon Listing（回填 dry_run=False）",
    },
    "amazon_us": {
        "label": "Amazon 美国站",
        "apply_url": "https://sellercentral.amazon.com/sw/user/central-developer",
        "apply_note": "同欧洲站流程；美国站需在 developer profile 选择北美市场。",
        "fields": [
            ("client_id", "LWA Client ID", False, "开发者档案页 Client ID"),
            ("client_secret", "LWA Client Secret", True, "与 Client ID 同页"),
            ("refresh_token", "卖家 Refresh Token", True, "授权后长期有效"),
        ],
        "unlocks": "美国站合规块写回 + Listing 回填",
    },
    "ebay": {
        "label": "eBay",
        "apply_url": "https://developer.ebay.com/signin",
        "apply_note": "eBay 无需商家自己申请开发者账号：平台运营方配置应用后，卖家点「去授权」完成 OAuth 即可（token 加密封存）。",
        "fields": [],  # OAuth 流程，不走粘贴表单
        "oauth": True,
        "unlocks": "买家消息实时同步 + AI 回复直发",
    },
    "allegro": {
        "label": "Allegro（波兰）",
        "apply_url": "https://developer.allegro.pl/",
        "apply_note": "developer.allegro.pl 免费注册应用即得 Client ID/Secret（测试环境 instant，正式环境自动审批）。",
        "fields": [
            ("client_id", "Client ID", False, "Allegro 应用列表页"),
            ("client_secret", "Client Secret", True, "与 Client ID 同页"),
        ],
        "unlocks": "波兰语买家消息自动导入 + 合规回复",
    },
    "otto": {
        "label": "Otto（德国）",
        "apply_url": "https://developer.otto.market/",
        "apply_note": "OTTO Marketplace 卖家可在 developer.otto.market 申请 API 访问，需卖家账号已激活。",
        "fields": [
            ("client_id", "Client ID", False, "OTTO 开发者后台"),
            ("client_secret", "Client Secret", True, "开发者后台"),
        ],
        "unlocks": "德语买家消息自动导入 + 合规回复",
    },
    "kaufland": {
        "label": "Kaufland（德/中东欧）",
        "apply_url": "https://seller.kaufland.de/",
        "apply_note": "门槛最低之一：Kaufland Seller Portal → 设置 → API 直接生成 Client-Key / Secret-Key，无需另行审核。",
        "fields": [
            ("client_key", "Client Key", False, "Seller Portal → API 设置"),
            ("secret_key", "Secret Key", True, "与 Client Key 同页生成"),
        ],
        "unlocks": "多国买家消息自动导入 + 合规回复",
    },
    "cdiscount": {
        "label": "Cdiscount（法国）",
        "apply_url": "https://dev.cdiscount.com/",
        "apply_note": "dev.cdiscount.com 注册后需绑定 Cdiscount 卖家账户，SOAP API 凭证由运营方邮件发放。",
        "fields": [
            ("api_key", "API Key", False, "Cdiscount 开发者邮件"),
            ("seller_login", "卖家登录名", False, "Cdiscount 后台账号"),
        ],
        "unlocks": "法语买家消息自动导入 + 合规回复",
    },
    "emag": {
        "label": "eMAG（罗马尼亚）",
        "apply_url": "https://marketplace.emag.eu/",
        "apply_note": "eMAG Marketplace 卖家后台 → 设置 → API 访问，生成后即时可用。",
        "fields": [
            ("api_key", "API Token", True, "eMAG 卖家后台 API 页"),
        ],
        "unlocks": "罗马尼亚语买家消息自动导入 + 合规回复",
    },
    "zalando": {
        "label": "Zalando（欧洲时尚）",
        "apply_url": "https://partners.zalando.de/",
        "apply_note": "Zalando Partner Program（zDirect）会员可申请 API 客户端，审核较严。",
        "fields": [
            ("client_id", "Client ID", False, "zDirect 后台"),
            ("client_secret", "Client Secret", True, "zDirect 后台"),
        ],
        "unlocks": "多语言买家消息自动导入 + 合规回复",
    },
    "bol": {
        "label": "bol.com（荷/比）",
        "apply_url": "https://developer.bol.com/",
        "apply_note": "developer.bol.com 用卖家账号登录创建 API 凭证（Client ID + Secret），即时生效。",
        "fields": [
            ("client_id", "Client ID", False, "bol 开发者后台"),
            ("client_secret", "Client Secret", True, "开发者后台"),
        ],
        "unlocks": "荷兰语买家消息自动导入 + 合规回复",
    },
    "walmart": {
        "label": "Walmart（美国）",
        "apply_url": "https://developer.walmart.com/",
        "apply_note": "Walmart Seller Center → 设置 → API Key 生成（卖家即时可得）。",
        "fields": [
            ("client_id", "Client ID", False, "Seller Center → API Key"),
            ("client_secret", "Client Secret", True, "同页生成"),
        ],
        "unlocks": "英语买家消息自动导入 + 合规回复",
    },
    "fruugo": {
        "label": "Fruugo（泛欧）",
        "apply_url": "https://merchant.fruugo.com/",
        "apply_note": "Fruugo Merchant Portal → 账户 → API，生成 Merchant ID + API Key。",
        "fields": [
            ("merchant_id", "Merchant ID", False, "Merchant Portal"),
            ("api_key", "API Key", True, "Merchant Portal"),
        ],
        "unlocks": "多语言买家消息自动导入 + 合规回复",
    },
    "tiktok": {
        "label": "TikTok Shop",
        "apply_url": "https://partner.tiktokshop.com/",
        "apply_note": "TikTok Shop Partner Center → 开发者 → 创建应用（个人卖家可用自用型应用）。",
        "fields": [
            ("app_key", "App Key", False, "Partner Center"),
            ("app_secret", "App Secret", True, "Partner Center"),
        ],
        "unlocks": "英语买家消息自动导入 + 合规回复",
    },
}

# 粘贴流程统一走这些 key 的平台（eBay 走 OAuth 除外）
PASTE_PLATFORMS = [p for p, cfg in PLATFORM_CRED_REGISTRY.items()
                   if not cfg.get("oauth")]


def cred_guide(platform: str) -> dict | None:
    """对外暴露的接入指南（不含任何密钥值）。"""
    cfg = PLATFORM_CRED_REGISTRY.get(platform)
    if not cfg:
        return None
    return {
        "label": cfg["label"],
        "oauth": cfg.get("oauth", False),
        "apply_url": cfg["apply_url"],
        "apply_note": cfg["apply_note"],
        "fields": [{"key": k, "label": l, "secret": s, "hint": h}
                   for k, l, s, h in cfg["fields"]],
        "unlocks": cfg["unlocks"],
    }
