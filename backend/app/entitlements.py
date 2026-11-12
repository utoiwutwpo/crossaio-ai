"""双闸校验：套餐 entitlement × 平台 capability。

任何触达平台的动作，先过两道闸；任一不过就返回明确拒绝码与修复提示，
绝不给"假装成功"。UI 用同一份判定决定按钮是否置灰。
"""
from typing import Dict, List, Optional

from .billing import SLOT_WEIGHTS, plan_config
from .connectors.capabilities import (
    CHANNELS,
    PLATFORM_FIX_HINT,
    auto_send_allowed,
    channel_tier,
    supports,
)

REASONS = (
    "ok",                    # 放行
    "plan_required",         # 套餐/接入位不足
    "platform_unsupported",  # 平台能力不支持
    "quota_exceeded",        # 配额用完
    "redline_hold",          # 红线/安全事件，强制人工
    "not_connected",         # 该平台尚未接入凭证
)

# 动作 → 该动作要求的平台能力（None = 平台无关）
ACTION_CAPABILITY: Dict[str, Optional[str]] = {
    "read_messages": "read_messages",
    "send_message": "send_message",
    "auto_send": "send_message",
    "read_orders": "read_orders",
    "write_listing": "write_listing",
    "write_inventory": "write_inventory",
    "compliance_docs": "compliance_docs",
    "content_gen": None,
    "review_rewrite": None,
    "agentic_feed": None,
    "connect": None,
}

# 动作 → 允许的套餐（按"该功能值多少钱"划分，而不是按平台个数）
ACTION_PLANS: Dict[str, set] = {
    "read_messages": {"free", "starter", "pro", "business"},
    "read_orders": {"free", "starter", "pro", "business"},
    "content_gen": {"free", "starter", "pro", "business"},
    "review_rewrite": {"free", "starter", "pro", "business"},
    "connect": {"free", "starter", "pro", "business"},
    "send_message": {"pro", "business"},
    "auto_send": {"pro", "business"},
    "write_listing": {"pro", "business"},
    "write_inventory": {"pro", "business"},
    "compliance_docs": {"pro", "business"},
    "agentic_feed": {"business"},
}

ACTION_TEXT = {
    "read_messages": "读取买家消息",
    "send_message": "发送回复",
    "auto_send": "自动发送回复",
    "read_orders": "读取订单",
    "write_listing": "写回 listing",
    "write_inventory": "写回库存",
    "compliance_docs": "上传合规文档",
    "content_gen": "生成商品内容",
    "review_rewrite": "差评改写",
    "agentic_feed": "Agentic 商品 feed",
    "connect": "接入平台",
}

def platform_weight(platform: str) -> int:
    return SLOT_WEIGHTS.get(channel_tier(platform) or "C", 1)


def used_slots(db, user_id: str) -> int:
    """已接入平台的接入位占用（按已保存凭证的平台计）。"""
    if db is None:
        return 0
    from .database import PlatformCredential
    rows = db.query(PlatformCredential).filter(
        PlatformCredential.user_id == user_id).all()
    total = 0
    for r in rows:
        total += platform_weight(r.platform)
    return total


def plan_slots(user, db=None) -> int:
    base = int(plan_config(getattr(user, "plan", "free")).get("slots", 2))
    return base + addon_slots(db, getattr(user, "id", ""))


def addon_slots(db, user_id: str) -> int:
    """extra_shop 每个 +1 接入位。"""
    if db is None or not user_id:
        return 0
    from .database import AddOnPurchase
    rows = (db.query(AddOnPurchase)
            .filter(AddOnPurchase.user_id == user_id,
                    AddOnPurchase.kind == "extra_shop",
                    AddOnPurchase.status == "active").all())
    return sum(int(r.qty or 0) for r in rows)


def addon_credits(db, user, kind: str) -> int:
    """auto_reply / incident 的加购余额（购买量减去已消耗的 UsageEvent）。"""
    if db is None or user is None:
        return 0
    from .database import AddOnPurchase, UsageEvent
    bought = sum(int(r.qty or 0) for r in
                 db.query(AddOnPurchase)
                 .filter(AddOnPurchase.user_id == user.id,
                         AddOnPurchase.kind == ("auto_reply" if kind == "auto_reply" else "incident"),
                         AddOnPurchase.status == "active").all())
    used_kind = "auto_reply_unit" if kind == "auto_reply" else "incident_addon"
    used = (db.query(UsageEvent)
            .filter(UsageEvent.user_id == user.id,
                    UsageEvent.kind == used_kind).count())
    return max(0, bought - used)


def consume_addon(db, user, kind: str, *, ref_id: str = "") -> bool:
    """扣一次加购额度（auto_reply / incident）。余额不足返回 False，不静默扣。"""
    if db is None or user is None:
        return False
    if addon_credits(db, user, kind) <= 0:
        return False
    from .database import UsageEvent
    db.add(UsageEvent(user_id=user.id,
                      kind=("auto_reply_unit" if kind == "auto_reply" else "incident_addon"),
                      qty=1, ref_id=ref_id))
    return True


def _credential_payload(db, user_id: str, platform: str) -> dict:
    if db is None or not user_id:
        return {}
    from .database import PlatformCredential
    row = (db.query(PlatformCredential)
           .filter(PlatformCredential.user_id == user_id,
                   PlatformCredential.platform == platform).first())
    if not row:
        return {}
    try:
        from .ebay_service import decrypt_secret
        import json
        raw = decrypt_secret(row.payload)
        data = json.loads(raw) if isinstance(raw, str) else (raw or {})
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def partner_approved(db, user, platform: str) -> bool:
    """TikTok 等 conditional 平台：资质已批才放行消息能力。"""
    if platform != "tiktok" or user is None:
        return False
    return bool(_credential_payload(db, getattr(user, "id", ""), platform)
                .get("partner_approved"))


def fix_hint(platform: str, action: str, reason: str,
             *, slots_total: int = 0, slots_used: int = 0) -> str:
    if reason == "platform_unsupported":
        base = PLATFORM_FIX_HINT.get(platform, "该平台不支持此 API 动作")
        return base or f"{platform} 不支持「{ACTION_TEXT.get(action, action)}」"
    if reason == "plan_required":
        if action == "connect":
            weight = platform_weight(platform)
            return (f"接入 {platform} 需 {weight} 个接入位（{channel_tier(platform)} 档），"
                    f"当前已用 {slots_used}/{slots_total}，请升级套餐或加购接入位")
        action_name = ACTION_TEXT.get(action, action)
        if ACTION_PLANS.get(action, set()) == {"business"}:
            return f"「{action_name}」为 Business 专属；升级 Business 后可用"
        return (f"「{action_name}」需 Pro 及以上；"
                f"免费/Starter 可生成草稿，发送前需人工确认")
    if reason == "quota_exceeded":
        return "今日/本月额度已用完，明日恢复或升级套餐"
    if reason == "redline_hold":
        return "命中红线或安全事件，AI 不得外发，请人工审核后处理"
    if reason == "not_connected":
        return f"{platform} 尚未接入凭证，请先在凭证中心完成授权"
    return ""


def can_act(db, user, platform: str, action: str, *,
            redline_flags: Optional[List[str]] = None,
            quota_left: Optional[int] = None) -> Dict:
    """返回 {allowed, reason_code, hint, platform, action, tier}。

    db 可为 None（纯单元测试时跳过接入位检查）。
    """
    p = (platform or "").strip().lower()
    act = (action or "").strip().lower()
    result = {
        "allowed": False, "reason_code": "ok", "hint": "",
        "platform": p, "action": act, "tier": channel_tier(p),
    }

    def deny(reason: str, **kw) -> Dict:
        result["reason_code"] = reason
        result["hint"] = fix_hint(p, act, reason, **kw)
        return result

    if act not in ACTION_CAPABILITY:
        return deny("platform_unsupported")

    if not p or p not in CHANNELS:
        return deny("platform_unsupported")

    # 闸零：红线/安全事件优先于一切
    if redline_flags and act in ("send_message", "auto_send"):
        return deny("redline_hold")

    # 闸一：平台能力（严格判定，仅 True 通过；TikTok 资质已批可解锁消息）
    cap = ACTION_CAPABILITY.get(act)
    tiktok_ok = partner_approved(db, user, p)
    if cap and not supports(p, cap):
        if not (tiktok_ok and cap in ("read_messages", "send_message", "write_listing",
                                      "write_inventory")):
            return deny("platform_unsupported")

    if act == "auto_send" and not (auto_send_allowed(p) or tiktok_ok):
        return deny("platform_unsupported")

    # 闸二：套餐（套餐不含时，先看加购包额度）
    plan = getattr(user, "plan", "free")
    if plan not in ACTION_PLANS.get(act, set()):
        if act in ("send_message", "auto_send") and addon_credits(db, user, "auto_reply") > 0:
            pass
        else:
            return deny("plan_required")

    # 闸二补充：接入位（仅 connect 与"未接入"判定）
    if act == "connect":
        total = plan_slots(user, db)
        used = used_slots(db, getattr(user, "id", ""))
        if used + platform_weight(p) > total:
            return deny("plan_required", slots_total=total, slots_used=used)

    # 闸三：配额
    if quota_left is not None and quota_left <= 0:
        return deny("quota_exceeded")

    result["allowed"] = True
    result["reason_code"] = "ok"
    return result


def matrix_for_user(db, user) -> Dict:
    """当前套餐下，12 平台各动作的放行矩阵（供 UI 预判按钮状态）。"""
    items = []
    for p in CHANNELS:
        acts = {}
        for act in ("read_messages", "send_message", "auto_send",
                    "write_listing", "write_inventory"):
            d = can_act(db, user, p, act)
            acts[act] = {"allowed": d["allowed"], "href": d["hint"]}
        items.append({
            "platform": p,
            "tier": channel_tier(p),
            "weight": platform_weight(p),
            "actions": acts,
        })
    return {
        "plan": getattr(user, "plan", "free"),
        "slots_total": plan_slots(user, db),
        "slots_used": used_slots(db, getattr(user, "id", "")),
        "items": items,
    }
