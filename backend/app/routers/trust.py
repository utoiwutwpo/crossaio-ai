"""透明定价信任模块 — 反定位 Webinterpret（费用不透明 / 难取消 / 退出残留）。

路由前缀：/api/v1/trust
- GET  /promises       公开：四大承诺（结构化，前端信任页直接消费）
- GET  /compare        公开：CrossAIO vs 传统本地化服务商对比表
- GET  /cancel-policy  公开：取消与退出政策
- POST /cancel-request 登录用户：一键取消（立即降级 free，真实生效）
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db, User
from ..auth import get_current_user
from ..billing import downgrade_to_free
from ..community_models import CancellationRequest

router = APIRouter()


# ---------------- 公开：四大承诺 ----------------
_PROMISES = [
    {
        "id": "flat-pricing",
        "title": "Transparent flat pricing",
        "detail": "No commission on sales. No per-item fee. No monthly minimum. "
                  "One flat price, published on the pricing page.",
    },
    {
        "id": "one-click-cancel",
        "title": "Cancel in one click",
        "detail": "Self-serve cancellation in your dashboard, effective immediately. "
                  "No phone calls, no retention emails, no dark patterns.",
    },
    {
        "id": "clean-exit",
        "title": "Clean exit, zero residue",
        "detail": "Export all your data at any time. When you cancel, listings revert "
                  "to your originals - nothing stays altered behind you.",
    },
    {
        "id": "check-before-pay",
        "title": "See problems before you pay",
        "detail": "The free GPSR health check shows exactly what is broken - risk level, "
                  "readiness score, missing items - before you enter any payment method.",
    },
]


@router.get("/promises", summary="四大承诺（透明定价信任页用）")
def promises():
    return {"promises": _PROMISES}


# ---------------- 公开：对比表 ----------------
@router.get("/compare", summary="CrossAIO vs 传统本地化服务商（公开事实对比）")
def compare():
    return {"rows": [
        {
            "dimension": "Pricing model",
            "traditional": "Success commission + per-item fee + monthly minimum",
            "crossaio": "Flat monthly price, all-inclusive",
        },
        {
            "dimension": "Cancellation",
            "traditional": "Email / phone request, frequently delayed",
            "crossaio": "One click in dashboard, effective immediately",
        },
        {
            "dimension": "Data on exit",
            "traditional": "Listings may remain altered after account closure",
            "crossaio": "Full export + listings revert to originals",
        },
        {
            "dimension": "Getting started",
            "traditional": "Sales demo and quote required",
            "crossaio": "Free GPSR health check, no card, no registration",
        },
        {
            "dimension": "Fee visibility",
            "traditional": "Fees disclosed in fine print after signup",
            "crossaio": "Full price list public, before signup",
        },
    ]}


@router.get("/cancel-policy", summary="取消与退出政策")
def cancel_policy():
    return {
        "effective": "immediately",
        "self_serve": True,
        "phone_call_required": False,
        "data_export": "any time, self-serve",
        "listing_revert": "originals restored on cancellation",
        "refund": "unused full months refunded on request",
    }


# ---------------- 登录：一键取消（真实生效） ----------------
class CancelRequestIn(BaseModel):
    reason: str = Field(default="", max_length=2000)


@router.post("/cancel-request", summary="一键取消订阅（立即降级 free，无需电话/邮件）")
def cancel_request(req: CancelRequestIn,
                   user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    prev_plan = user.plan          # 降级前先取快照
    result = downgrade_to_free(db, user)
    record = CancellationRequest(
        user_id=user.id,
        email=user.email,
        plan_at_cancel=prev_plan,
        reason=req.reason,
        status="effective",
    )
    db.add(record)
    db.commit()
    return {
        "status": "cancelled",
        "effective": "immediately",
        "previous_plan": prev_plan,
        "plan": result.get("plan", "free"),
        "note": "Your data stays exportable. Nothing else changes.",
    }
