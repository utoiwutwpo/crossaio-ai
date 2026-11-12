"""
计费与用量模块
- 套餐定义（免费 / Starter / Pro / Business）
- 每日免费额度 + 月度额度
- 用量记录走数据库（本地 SQLite 即用）；生产可切 Redis 计数器
- Stripe 集成做成可选依赖：未配置 Key 时 create/upgrade 走"本地模拟"，
  生产配置 Key 后走真实 Stripe Billing
"""
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .database import UsageLog, User

PLANS: dict = {
    "free": {
        "monthly_price_usd": 0,
        "monthly_price_eur": 0,
        "daily_limit": 5,
        "monthly_calls": 150,          # 5 × 30
        "platforms": 1,
        "slots": 2,                    # 接入位：A=3 / B=2 / C=1
        "features": ["product_desc", "review_rewrite"],   # P0-4：差评改写纳入免费试用（共享日限）
        "email_frequency": "none",     # 不发日报邮件
        "auto_writeback": False,       # 不自动写回
        "auto_reply": False,           # 不自动回复买家消息
        "realtime_alerts": False,
        # 【P0】订阅驱动的自动体检频率：
        # manual=免费手动；daily=每日 1 次；daily_xN=每日多次（≥8h 一轮）；realtime=近实时事件触发
        "automation_frequency": "manual",
    },
    "starter": {
        "monthly_price_usd": 29,
        "monthly_price_eur": 29,
        "daily_limit": 50,
        "monthly_calls": 1000,
        "platforms": 1,
        "slots": 6,
        "features": ["product_desc", "review_rewrite"],
        "email_frequency": "weekly",   # 每周一发
        "auto_writeback": False,       # 提供复制粘贴，不自动写回
        "auto_reply": False,
        "realtime_alerts": False,
        "automation_frequency": "daily",
    },
    "pro": {
        "monthly_price_usd": 49,
        "monthly_price_eur": 49,
        "daily_limit": 200,
        "monthly_calls": None,         # 无限（仍有日限流保护）
        "platforms": 3,
        "slots": 20,
        "features": ["product_desc", "customer_service", "ad_copy", "review_rewrite",
                     "listing_gen", "gpsr_closure"],
        "email_frequency": "daily",    # 每日发
        # 生成待提交 payload；真实写入仍需平台凭证 + 人工确认（不是"已接入自动写回"）
        "auto_writeback": True,
        "auto_reply": True,            # 生成回复草稿；A 档平台可自动发送
        "realtime_alerts": False,
        "automation_frequency": "daily_xN",
    },
    "business": {
        "monthly_price_usd": 149,
        "monthly_price_eur": 149,
        "daily_limit": 1000,
        "monthly_calls": None,
        "platforms": None,             # 无限
        "slots": 22,                   # 13 个全接（2×3 + 5×2 + 6×1）
        "features": ["product_desc", "customer_service", "ad_copy", "api_access",
                     "review_rewrite", "listing_gen", "gpsr_closure", "agentic_feed"],
        "email_frequency": "daily",    # 每日 + 实时预警
        "auto_writeback": True,
        "auto_reply": True,            # A 档平台自动发送；B/C 档仍降级为任务卡
        "realtime_alerts": True,
        "automation_frequency": "realtime",
    },
}

# 各频率档对应的"距上次自动运行多久才再次自动跑"间隔（秒）。
# free/manual 不自动跑；starter 每日 1 次；pro 每 8h（每日约 3 次）；business 每 10min（近实时）。
# 接入位权重：不同档位平台的接入与维护成本差 3 倍以上
SLOT_WEIGHTS = {"A": 3, "B": 2, "C": 1}

AUTOMATION_INTERVALS = {
    "manual": None,
    "daily": 24 * 3600,
    "daily_xN": 8 * 3600,
    "realtime": 10 * 60,
}


def plan_config(plan: str) -> dict:
    return PLANS.get(plan, PLANS["free"])


def has_feature(user: User, feature: str) -> bool:
    """检查用户套餐是否包含某功能（如 customer_service / ad_copy / api_access）。"""
    cfg = plan_config(user.plan)
    return feature in cfg["features"]


def can_auto_writeback(user: User, platform: str | None = None) -> bool:
    """是否允许写回平台。

    套餐是闸一，平台能力是闸二：给了 platform 就必须同时满足该平台的写能力，
    否则返回 False（避免把 Amazon 之类的受限平台当成可写）。
    """
    if not plan_config(user.plan).get("auto_writeback", False):
        return False
    if platform is None:
        return True
    from .connectors.capabilities import supports
    return supports(platform, "write_listing")


def can_auto_reply(user: User, platform: str | None = None) -> bool:
    """是否允许自动回复买家消息。

    platform 缺省时只判套餐（向后兼容既有调用点）；给了 platform 就必须
    同时满足"该平台可自动外发"，即只有 A 档且已确认支持发送的平台。
    """
    if not plan_config(user.plan).get("auto_reply", False):
        return False
    if platform is None:
        return True
    from .connectors.capabilities import auto_send_allowed
    return auto_send_allowed(platform)


def email_frequency(user: User) -> str:
    """日报邮件频率：none / weekly / daily。"""
    return plan_config(user.plan).get("email_frequency", "none")


def automation_frequency(user: User) -> str:
    """【P0】订阅驱动的自动体检频率：
    manual / daily / daily_xN / realtime。"""
    return plan_config(user.plan).get("automation_frequency", "manual")


def automation_interval_seconds(user: User):
    """【P0】该用户套餐自动体检的最小间隔秒数；manual 返回 None（不自动跑）。"""
    return AUTOMATION_INTERVALS.get(automation_frequency(user))


def usage_today(db: Session, user_id: str) -> int:
    return (
        db.query(UsageLog)
        .filter(UsageLog.user_id == user_id, UsageLog.log_date == date.today())
        .count()
    )


def usage_this_month(db: Session, user_id: str) -> int:
    today = date.today()
    return (
        db.query(UsageLog)
        .filter(
            UsageLog.user_id == user_id,
            UsageLog.log_date >= today.replace(day=1),
        )
        .count()
    )


def check_and_record_usage(db: Session, user: User, feature: str,
                           *, with_compliance: bool = False) -> None:
    """检查额度并记录一次调用；超限抛 402。

    with_compliance: 【P0-2】本次调用是否带合规体检上下文（用于统计）。
    默认 False，向后兼容全部既有调用点。
    """
    cfg = plan_config(user.plan)

    if feature not in cfg["features"] and "all" not in cfg["features"]:
        raise HTTPException(
            status_code=402,
            detail=f"当前套餐（{user.plan}）不含「{feature}」功能，请升级套餐",
        )

    used_today = usage_today(db, user.id)
    if used_today >= cfg["daily_limit"]:
        raise HTTPException(
            status_code=402,
            detail=f"今日免费额度已用完（{cfg['daily_limit']} 次/天），明日恢复或升级套餐",
        )

    monthly = cfg["monthly_calls"]
    if monthly is not None and usage_this_month(db, user.id) >= monthly:
        raise HTTPException(
            status_code=402,
            detail=f"本月调用次数已达上限（{monthly} 次），请升级套餐",
        )

    db.add(UsageLog(user_id=user.id, feature=feature,
                    with_compliance=with_compliance))
    db.commit()


def upgrade_plan_local(db: Session, user: User, plan: str) -> dict:
    """本地模拟升级（Stripe 未配置时的降级路径，用于联调/演示）
    生产环境中此函数由 Stripe webhook 回调替代。
    """
    if plan not in ("starter", "pro", "business"):
        raise HTTPException(status_code=400, detail="无效套餐")
    user.plan = plan
    user.stripe_status = "active_local"
    db.commit()
    return {"success": True, "plan": plan, "mode": "local_mock"}


def downgrade_to_free(db: Session, user: User) -> dict:
    user.plan = "free"
    user.stripe_status = "canceled"
    db.commit()
    return {"success": True, "plan": "free"}


# ================= 加购包（可单独购买，不强制升级套餐） =================
ADDON_CATALOG = {
    "extra_shop": {"name": "额外店铺接入位（+1）", "unit_price_usd": 29.0,
                   "unit": "店", "effect": "slots",
                   "note": "每个 A 档平台占 3 位，B 档 2 位，C 档 1 位"},
    "extra_seat": {"name": "额外坐席（+1 人）", "unit_price_usd": 6.0,
                   "unit": "位", "effect": "seat",
                   "note": "团队账号，同工作台协作"},
    "auto_reply": {"name": "自动回复次数（+1 单）", "unit_price_usd": 0.90,
                   "unit": "单", "effect": "auto_reply_credit",
                   "note": "套餐不含自动发送时按单计费，先扣加购额度"},
    "incident": {"name": "事故闭环次数（+1 次）", "unit_price_usd": 15.0,
                 "unit": "次", "effect": "incident_credit",
                 "note": "GPSR 安全事件档案 + 15 天倒计时处置"},
}


def addon_price(kind: str) -> float:
    return float((ADDON_CATALOG.get(kind) or {}).get("unit_price_usd", 0.0))
