"""Stripe 收款核心逻辑

设计原则：
- 未配置 STRIPE_SECRET_KEY → 本地模拟模式（演示/联调用），路由层负责降级
- webhook 事件处理拆成纯函数，不依赖 stripe SDK，便于单测
- price_id → plan 映射来自 settings（Stripe 后台创建的三个 recurring price）
"""
from datetime import datetime

from sqlalchemy.orm import Session

from .database import User
from .config import settings

# plan → settings 里价格字段名（billing: monthly / yearly）
PRICE_FIELD = {
    ("starter", "monthly"): "stripe_price_starter",
    ("pro", "monthly"): "stripe_price_pro",
    ("business", "monthly"): "stripe_price_business",
    ("starter", "yearly"): "stripe_price_starter_year",
    ("pro", "yearly"): "stripe_price_pro_year",
    ("business", "yearly"): "stripe_price_business_year",
}


def map_price_to_plan(price_id: str) -> str | None:
    """Stripe price_id 反查套餐名；未匹配返回 None（未知价格忽略）"""
    if not price_id:
        return None
    for (plan, _billing), field in PRICE_FIELD.items():
        if getattr(settings, field, "") == price_id:
            return plan
    return None


def apply_checkout_completed(db: Session, user: User, *, plan: str,
                             customer_id: str, subscription_id: str,
                             status: str) -> None:
    """checkout.session.completed：开通套餐"""
    user.plan = plan
    user.stripe_customer_id = customer_id or ""
    user.stripe_subscription_id = subscription_id or ""
    user.stripe_status = status or "active"
    user.updated_at = datetime.utcnow()
    db.commit()


def apply_subscription_deleted(db: Session, user: User) -> None:
    """customer.subscription.deleted：降回免费版"""
    user.plan = "free"
    user.stripe_status = "canceled"
    user.stripe_subscription_id = ""
    user.updated_at = datetime.utcnow()
    db.commit()


def apply_payment_failed(db: Session, user: User) -> None:
    """invoice.payment_failed：标记欠费（保留套餐，由 retry 逻辑决定后续）"""
    user.stripe_status = "past_due"
    user.updated_at = datetime.utcnow()
    db.commit()


_STRIPE_NET_READY = False


def _configure_stripe_network() -> None:
    """Stripe SDK 出网：配了 PROXY_URL 就走代理，统一 12s 超时、最多重试 1 次。

    实测本机直连 api.stripe.com 会超时（21s 未连通），不加代理时创建 checkout 会长时间
    挂起最后 502；接上 PROXY_URL 后可正常返回。海外服务器 PROXY_URL 留空即保持直连。
    """
    global _STRIPE_NET_READY
    if _STRIPE_NET_READY:
        return
    try:
        import stripe
        stripe.max_network_retries = 1
        if settings.proxy_url:
            import httpx
            stripe.default_http_client = stripe.http_client.HTTPClient(
                "httpx-proxy",
                http_client=httpx.Client(proxy=settings.proxy_url, timeout=12.0),
            )
    except Exception:  # SDK 版本差异/依赖缺失 → 退回 SDK 默认行为，不阻断下单
        pass
    _STRIPE_NET_READY = True


def create_checkout_session(user: User, plan: str, origin: str, billing: str = "monthly") -> dict:
    """创建 Stripe Checkout Session（subscription 模式）

    billing: "monthly" | "yearly"（年付一次性扣年总价）
    返回 {"url": ..., "session_id": ...}；配置缺失时抛 ValueError。
    """
    import stripe  # 懒导入：未安装 stripe 包时仅在真实收款路径报错

    price_field = PRICE_FIELD.get((plan, billing))
    if not price_field:
        raise ValueError(f"plan '{plan}' with billing '{billing}' is not purchasable")
    if not settings.stripe_secret_key:
        raise ValueError("stripe_secret_key not configured")
    price_id = getattr(settings, price_field, "")
    if not price_id:
        raise ValueError(f"stripe price for '{plan}' not configured")

    stripe.api_key = settings.stripe_secret_key
    _configure_stripe_network()
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=user.email,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{origin}/app?checkout=success&plan={plan}&billing={billing}",
        cancel_url=f"{origin}/pricing?checkout=cancelled",
        client_reference_id=user.id,
        metadata={"user_id": user.id, "plan": plan, "billing": billing},
        subscription_data={"metadata": {"user_id": user.id, "plan": plan, "billing": billing}},
    )
    return {"url": session.url, "session_id": session.id}
