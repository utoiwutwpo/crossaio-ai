"""AI 客服消息处理与对话记录 + P0-4 跨平台差评回复改写"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db, User, CustomerServiceConversation, ReviewRewriteLog
from ..schemas import (
    CustomerServiceRequest, CustomerServiceResponse, ReviewRewriteRequest,
    ReviewRewriteResponse,
)
from ..auth import get_current_user
from ..experts.customer_service import CustomerServiceExpert
from ..experts.review_rewrite import ReviewRewriteExpert
from ..billing import check_and_record_usage
from ..services.compliance_context import build_compliance_context

router = APIRouter()
expert = CustomerServiceExpert()
rewrite_expert = ReviewRewriteExpert()

# 【P0-4】差评改写独立路由组：/api/v1/reviews/rewrite（清单端点路径）
reviews_router = APIRouter()

VALID_REWRITE_PLATFORMS = ("amazon", "ebay")
VALID_REWRITE_MODES = ("public", "private", "both")


@router.post("/messages", response_model=CustomerServiceResponse,
             summary="处理一条买家咨询")
def handle_message(
    req: CustomerServiceRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 【P0-2】合规×运营一体化：注入该用户最近一次未通过体检结论（无审计自动降级）
    ctx = build_compliance_context(db, user.id)
    check_and_record_usage(db, user, "customer_service",
                           with_compliance=ctx["found"])
    result = expert.handle(req, compliance_block=ctx["prompt_block"])
    if ctx["found"]:
        result.compliance_note = ctx["display_block"]["text"]
        result.related_audit_id = ctx["audit_id"]
    db.add(CustomerServiceConversation(
        user_id=user.id,
        customer_message=req.customer_message,
        ai_response=result.reply,
        intent=result.intent,
        sentiment=result.sentiment,
        needs_escalation=result.needs_escalation,
        related_audit_id=ctx["audit_id"],
    ))
    db.commit()
    return result


@router.get("/conversations", summary="对话历史（分页）")
def list_conversations(
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = (
        db.query(CustomerServiceConversation)
        .filter(CustomerServiceConversation.user_id == user.id)
        .order_by(CustomerServiceConversation.created_at.desc())
    )
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "items": [
            {
                "id": r.id,
                "customer_message": r.customer_message,
                "ai_response": r.ai_response,
                "intent": r.intent,
                "sentiment": r.sentiment,
                "needs_escalation": r.needs_escalation,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }


# ================= P0-4 跨平台差评回复改写（只生成/导出，无自动发送端点） =================
@reviews_router.post("/rewrite", response_model=ReviewRewriteResponse,
                     summary="【P0-4】差评回复改写（公开回复 + 私信安抚 + 规则自查）")
def rewrite_review(
    req: ReviewRewriteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    platform = (req.platform or "").strip().lower()
    mode = (req.mode or "both").strip().lower()
    if platform not in VALID_REWRITE_PLATFORMS:
        raise HTTPException(422, f"platform 仅支持 {list(VALID_REWRITE_PLATFORMS)}")
    if mode not in VALID_REWRITE_MODES:
        raise HTTPException(422, f"mode 仅支持 {list(VALID_REWRITE_MODES)}")

    # P0-3 免费档限额：review_rewrite 计入每日/月度用量
    check_and_record_usage(db, user, "review_rewrite")

    result = rewrite_expert.rewrite(
        db, platform, req.review_snippet.strip(),
        listing_ref=(req.listing_ref or "").strip(), mode=mode)

    row = ReviewRewriteLog(
        user_id=user.id,
        platform=result["platform"],
        listing_ref=result["listing_ref"],
        review_snippet=result["review_snippet"],
        public_reply=result["public_reply"],
        private_message=result["private_message"],
        rule_check_json=__import__("json").dumps(
            result["rule_check"], ensure_ascii=False),
        status=result["status"],
    )
    db.add(row)
    db.commit()

    return ReviewRewriteResponse(
        id=row.id,
        platform=result["platform"],
        listing_ref=result["listing_ref"],
        review_snippet=result["review_snippet"],
        public_reply=result["public_reply"],
        private_message=result["private_message"],
        rule_check=result["rule_check"],
        status=result["status"],
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@reviews_router.get("/rewrite/history", summary="【P0-4】差评改写历史（分页留痕）")
def rewrite_history(
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = (
        db.query(ReviewRewriteLog)
        .filter(ReviewRewriteLog.user_id == user.id)
        .order_by(ReviewRewriteLog.created_at.desc())
    )
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    import json as _json
    return {
        "total": total,
        "page": page,
        "items": [
            {
                "id": r.id,
                "platform": r.platform,
                "listing_ref": r.listing_ref,
                "review_snippet": r.review_snippet[:200],
                "public_reply": r.public_reply,
                "private_message": r.private_message,
                "rule_check": _json.loads(r.rule_check_json or "{}"),
                "status": r.status,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }
