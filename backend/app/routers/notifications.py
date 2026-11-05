"""【P2】站内通知闭环。

notify(db, user_id, type, title, body) 帮助函数供 watch_service / automation /
connectors 等模块复用；REST 契约：
  GET  /api/v1/notifications                 -> {"items":[...], "unread": n}
  GET  /api/v1/notifications/unread-count   -> {"unread": n}
  POST /api/v1/notifications/{id}/read     -> {"ok": true}
  POST /api/v1/notifications/read-all       -> {"ok": true, "updated": n}
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db, Notification, User

log = logging.getLogger("crossaio.notifications")
router = APIRouter()

VALID_TYPES = {"risk", "report", "reply", "writeback", "system"}


def notify(db: Session, user_id: str, type: str, title: str, body: str = "") -> Optional[Notification]:
    """写一条站内通知。type 非法时降级为 system；提交失败不阻断主流程。"""
    if not user_id:
        return None
    if type not in VALID_TYPES:
        type = "system"
    n = Notification(user_id=user_id, type=type,
                     title=(title or "")[:255], body=body or "")
    db.add(n)
    try:
        db.commit()
    except Exception:
        db.rollback()
        log.warning("通知写入失败 user=%s title=%s", user_id, title)
        return None
    return n


def _to_dict(n: Notification) -> dict:
    return {
        "id": n.id, "type": n.type, "title": n.title, "body": n.body,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "read": bool(n.read),
    }


@router.get("/notifications", summary="最近 50 条通知（按时间倒序）")
def list_notifications(user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    rows = (db.query(Notification)
            .filter(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
            .limit(50).all())
    unread = (db.query(Notification)
              .filter(Notification.user_id == user.id,
                      Notification.read == False).count())  # noqa: E712
    return {"items": [_to_dict(r) for r in rows], "unread": unread}


@router.get("/notifications/unread-count", summary="未读通知数")
def unread_count(user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    n = (db.query(Notification)
         .filter(Notification.user_id == user.id,
                 Notification.read == False).count())  # noqa: E712
    return {"unread": n}


@router.post("/notifications/{notice_id}/read", summary="标记单条通知已读")
def mark_read(notice_id: str,
              user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    n = (db.query(Notification)
         .filter(Notification.id == notice_id,
                 Notification.user_id == user.id).first())
    if not n:
        raise HTTPException(status_code=404, detail="通知不存在")
    n.read = True
    db.commit()
    return {"ok": True}


@router.post("/notifications/read-all", summary="全部标记已读")
def mark_all_read(user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    updated = (db.query(Notification)
               .filter(Notification.user_id == user.id,
                       Notification.read == False)  # noqa: E712
               .update({"read": True}))
    db.commit()
    return {"ok": True, "updated": updated}
