"""12 平台通道能力注册表。

用途：把"这个平台能不能读买家消息、能不能发回复、能不能改 listing"变成数据，
让 UI 自动降级（按钮置灰并给出原因），让订阅档位按"能力"而不是"平台数量"计费。

取值约定（诚实标注，不假装已知）：
  True            已确认支持
  False           已确认不支持，或平台无此能力
  "permitted_only" 仅允许特定类别（如 Amazon 仅 Permitted Messages）
  "legacy"         仅老接口支持（如 eBay Trading API）
  "unverified"     有官方 API 但该能力未坐实
  "conditional"    需额外资质/审核

tier 含义：
  A 可程序化收发买家消息
  B 只能部分操作（可发不可读 / 只能订单类 / 待核实）
  C 无公开消息 API，只能邮件或人工
"""
from typing import Dict, List, Optional

CAPABILITY_KEYS: tuple = (
    "read_messages",     # 读买家消息
    "send_message",      # 发回复
    "read_orders",       # 读订单
    "write_listing",     # 写 listing
    "write_inventory",   # 写库存
    "compliance_docs",   # 上传合规文档（GPSR 安全信息等）
)

CHANNEL_MODES: Dict[str, str] = {
    "api": "官方 API 直连",
    "api_limited": "官方 API 受限（仅特定消息类别）",
    "email": "邮件通知解析",
    "manual": "仅卖家后台人工操作",
}

CHANNELS: Dict[str, dict] = {
    "amazon": {
        "tier": "B", "mode": "api_limited",
        "caps": {"read_messages": False, "send_message": "permitted_only",
                 "read_orders": True, "write_listing": True,
                 "write_inventory": True, "compliance_docs": False},
        "note": "SP-API 仅 Permitted Messages，买家咨询无公开读取接口",
    },
    "ebay": {
        "tier": "B", "mode": "api",
        "caps": {"read_messages": "legacy", "send_message": "legacy",
                 "read_orders": True, "write_listing": True,
                 "write_inventory": True, "compliance_docs": False},
        "note": "消息能力依赖 Trading API 老接口，需单独申请权限",
    },
    "fruugo": {
        "tier": "C", "mode": "api",
        "caps": {"read_messages": False, "send_message": False,
                 "read_orders": True, "write_listing": "unverified",
                 "write_inventory": "unverified", "compliance_docs": False},
        "note": "Product/Order API 用 Basic 鉴权；Order 端点只在零售商支持门户内可见",
    },
    "walmart": {
        "tier": "B", "mode": "api",
        "caps": {"read_messages": "unverified", "send_message": "unverified",
                 "read_orders": True, "write_listing": True,
                 "write_inventory": True, "compliance_docs": False},
        "note": "订单/listing 有 API；买家消息能力未坐实",
    },
    "cdiscount": {
        "tier": "C", "mode": "api",
        "caps": {"read_messages": False, "send_message": False,
                 "read_orders": True, "write_listing": "unverified",
                 "write_inventory": "unverified", "compliance_docs": False},
        "note": "走 Octopia Seller API（api.octopia-io.net/seller/v2/orders），消息仍在后台",
    },
    "otto": {
        "tier": "C", "mode": "api",
        "caps": {"read_messages": False, "send_message": False,
                 "read_orders": True, "write_listing": "unverified",
                 "write_inventory": "unverified", "compliance_docs": False},
        "note": "OTTO Market API v2 可读订单（OAuth2 client_credentials），客服消息走后台",
    },
    "allegro": {
        "tier": "A", "mode": "api",
        "caps": {"read_messages": True, "send_message": True,
                 "read_orders": True, "write_listing": True,
                 "write_inventory": True, "compliance_docs": False},
        "note": "REST /messaging 可读可回，13 个里唯一确定能全自动的",
    },
    "emag": {
        "tier": "C", "mode": "api",
        "caps": {"read_messages": False, "send_message": False,
                 "read_orders": True, "write_listing": True,
                 "write_inventory": True, "compliance_docs": False},
        "note": "api-3 订单与 product_offer/save 已接；客服消息在后台",
    },
    "kaufland": {
        "tier": "C", "mode": "api",
        "caps": {"read_messages": False, "send_message": False,
                 "read_orders": True, "write_listing": True,
                 "write_inventory": True, "compliance_docs": False},
        "note": "v2 /orders 可读、POST /units 建品、PATCH /units/{id} 改库存；没有聊天通道",
    },
    "bol": {
        "tier": "B", "mode": "api",
        "caps": {"read_messages": "unverified", "send_message": "unverified",
                 "read_orders": True, "write_listing": True,
                 "write_inventory": True, "compliance_docs": False},
        "note": "Retailer API 订单/offer 可用；客服消息能力待核实",
    },
    "zalando": {
        "tier": "C", "mode": "api",
        "caps": {"read_messages": False, "send_message": False,
                 "read_orders": True, "write_listing": "unverified",
                 "write_inventory": "unverified", "compliance_docs": False},
        "note": "zDirect Orders API 可读订单（OAuth2），需 Go Live 资质；客服走后台",
    },
    "tiktok": {
        "tier": "A", "mode": "api",
        "caps": {"read_messages": "conditional", "send_message": "conditional",
                 "read_orders": True, "write_listing": True,
                 "write_inventory": True, "compliance_docs": False},
        "note": "Partner API 有消息能力，需合作方资质审核",
    },
}

TIER_TEXT: Dict[str, str] = {
    "A": "可程序化收发买家消息",
    "B": "部分可用（可发不可读 / 待核实）",
    "C": "无公开消息 API，只能邮件或人工",
}

# 能力不足时给商家看的人话（不是技术错误码）
PLATFORM_FIX_HINT: Dict[str, str] = {
    "amazon": "Amazon SP-API 仅支持订单事务消息（Permitted Messages），读不到买家主动咨询，请去 Seller Central 处理",
    "ebay": "eBay 消息能力依赖 Trading API 老接口，需单独申请权限并逐店授权",
    "walmart": "Walmart 订单/listing 可用，买家消息能力未核实，请在 Seller Center 处理",
    "bol": "bol 订单与 offer 可用，客服消息接口未核实，请在卖家后台处理",
    "otto": "OTTO 无公开卖家消息 API，请在 Partner Portal 处理",
    "kaufland": "Kaufland Seller API 无消息接口，请在卖家后台处理",
    "cdiscount": "Cdiscount 订单走 Octopia API 可同步；买家消息请在卖家后台处理",
    "emag": "eMAG 消息在卖家后台，API 未覆盖",
    "zalando": "Zalando zDirect 需合作伙伴资质，客服请在后台处理",
    "fruugo": "Fruugo 无公开消息 API，订单以邮件/文件流转",
    "tiktok": "TikTok Shop 消息能力需 Partner 资质审核通过后才能自动外发",
    "allegro": "",
}


def get_channel(platform: str) -> Optional[dict]:
    return CHANNELS.get(platform)


def channel_tier(platform: str) -> Optional[str]:
    ch = CHANNELS.get(platform) or {}
    return ch.get("tier")


def supports(platform: str, capability: str) -> bool:
    """严格判定：只有 True 才算支持，任何带条件的取值都返回 False。"""
    ch = CHANNELS.get(platform) or {}
    return (ch.get("caps") or {}).get(capability) is True


def auto_send_allowed(platform: str) -> bool:
    """能否在无人确认的情况下自动发送回复。

    只有 A 档且 send_message 为 True 才允许；tiktok 的 conditional 不算，
    避免资质未批就自动外发。
    """
    return supports(platform, "send_message") and channel_tier(platform) == "A"


def auto_reply_available(platform: str) -> bool:
    """能否生成"可直接发送"的回复（含需人工确认的情形）。"""
    return supports(platform, "send_message")


def matrix() -> List[dict]:
    rows = []
    for platform, ch in CHANNELS.items():
        rows.append({
            "platform": platform,
            "tier": ch["tier"],
            "tier_text": TIER_TEXT.get(ch["tier"], ""),
            "mode": ch["mode"],
            "mode_text": CHANNEL_MODES.get(ch["mode"], ""),
            "caps": dict(ch["caps"]),
            "auto_send": auto_send_allowed(platform),
            "note": ch["note"],
        })
    return rows


def summary() -> Dict[str, int]:
    counts: Dict[str, int] = {"A": 0, "B": 0, "C": 0}
    for ch in CHANNELS.values():
        counts[ch["tier"]] = counts.get(ch["tier"], 0) + 1
    return counts
