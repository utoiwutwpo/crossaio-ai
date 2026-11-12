"""政策周报订阅 API — 前缀 /api/v1/newsletter

POST /subscribe     {email, source, lang, page} → 落库（幂等）+ 配了 SMTP 才发确认信
GET  /unsubscribe   ?token=<subscriber.id>     → 一键退订
GET  /count                                    → 订阅人数（运营/dashboard 用）

设计约束：
- 不存明文 IP，只存 sha256 前 32 位，用于粗粒度防刷判断。
- 邮箱已存在时不报错，直接返回「已在名单」，避免前端重复提交报错。
- SMTP 未配置时 mailer 内部静默跳过，接口仍返回成功（先把名单收下来）。
"""
import hashlib
import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..mailer import send_email
from ..newsletter_models import NewsletterSubscriber

router = APIRouter()
log = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,}$")

CONFIRM_HTML = (
    "<p>你的 CrossAIO 政策周报已开通，每周三一封。</p>"
    "<p>只写你在卖的那几个平台：字数口径、必填项、合规块、申诉窗口改了什么，"
    "以及会影响哪些 SKU。</p>"
    "<p>不想继续收，点这里退订：{unsub}</p>"
)


class SubscribeIn(BaseModel):
    email: str = Field(..., max_length=255)
    source: str = Field(default="home", max_length=50)
    lang: str = Field(default="zh", max_length=10)
    page: str = Field(default="", max_length=200)


@router.post("/subscribe")
def subscribe(payload: SubscribeIn, request: Request, db: Session = Depends(get_db)):
    email = (payload.email or "").strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")

    ip = (request.client.host if request.client else "") or ""
    row = db.query(NewsletterSubscriber).filter(NewsletterSubscriber.email == email).first()

    if row is not None:
        if row.unsubscribed:
            row.unsubscribed = False
            row.source = (payload.source or row.source or "home")[:50]
            db.commit()
            return {"ok": True, "state": "resubscribed",
                    "message": "已重新订阅，本周三起继续收到"}
        return {"ok": True, "state": "exists",
                "message": "这个邮箱已经在名单里，周三照常送达"}

    sub = NewsletterSubscriber(
        email=email,
        source=(payload.source or "home")[:50],
        lang=(payload.lang or "zh")[:10],
        page=(payload.page or "")[:200],
        ip_hash=hashlib.sha256(ip.encode()).hexdigest()[:32] if ip else "",
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    if settings.smtp_host:
        try:
            unsub = "/api/v1/newsletter/unsubscribe?token=%s" % sub.id
            send_email(email, "CrossAIO 政策周报已开通", CONFIRM_HTML.format(unsub=unsub))
        except Exception as exc:            # 发信失败不影响订阅结果
            log.warning("周报确认信发送失败 %s: %s", email, exc)

    return {"ok": True, "state": "created", "message": "已订阅，本周三起每周一封"}


@router.get("/unsubscribe")
def unsubscribe(token: str = Query(..., min_length=8, max_length=64),
                db: Session = Depends(get_db)):
    row = db.query(NewsletterSubscriber).filter(NewsletterSubscriber.id == token).first()
    if row is None:
        raise HTTPException(status_code=404, detail="订阅记录不存在")
    row.unsubscribed = True
    db.commit()
    return {"ok": True, "message": "已退订，不会再收到政策周报"}


@router.get("/count")
def count(db: Session = Depends(get_db)):
    total = db.query(func.count(NewsletterSubscriber.id)).scalar() or 0
    active = (db.query(func.count(NewsletterSubscriber.id))
              .filter(NewsletterSubscriber.unsubscribed.is_(False)).scalar() or 0)
    return {"total": total, "active": active}
