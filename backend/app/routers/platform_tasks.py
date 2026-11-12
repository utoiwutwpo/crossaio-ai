"""任务卡：B/C 档平台无法 API 处理的动作，落成卖家可勾选的待办。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..connectors.capabilities import PLATFORM_FIX_HINT, channel_tier
from ..connectors.channels.manual import PLATFORM_BACKOFFICE
from ..database import PlatformTask, get_db, User

router = APIRouter()


class TaskCreate(BaseModel):
    platform: str
    kind: str = "message"
    external_ref: str = ""
    customer_message: str = Field(default="", max_length=4000)
    draft_reply: str = ""
    note: str = ""


@router.get("", summary="任务卡列表（default 只看未完成）")
def list_tasks(status: str = "open", page: int = 1, page_size: int = 20,
               user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    q = db.query(PlatformTask).filter(PlatformTask.user_id == user.id)
    if status != "all":
        q = q.filter(PlatformTask.status == status)
    q = q.order_by(PlatformTask.created_at.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "items": [{
        "id": t.id, "platform": t.platform, "kind": t.kind,
        "external_ref": t.external_ref, "customer_message": t.customer_message,
        "draft_reply": t.draft_reply, "backoffice_url": t.backoffice_url,
        "status": t.status, "note": t.note, "created_at": t.created_at,
    } for t in rows]}


@router.post("", summary="创建任务卡（平台不支持 API 时降级）")
def create_task(req: TaskCreate, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    p = req.platform.strip().lower()
    if p not in PLATFORM_BACKOFFICE:
        raise HTTPException(422, f"未知平台：{p}")
    task = PlatformTask(
        user_id=user.id, platform=p, kind=req.kind,
        external_ref=req.external_ref, customer_message=req.customer_message,
        draft_reply=req.draft_reply, note=req.note,
        backoffice_url=PLATFORM_BACKOFFICE.get(p, ""),
    )
    db.add(task)
    db.commit()
    return {"id": task.id, "platform": p, "tier": channel_tier(p),
            "hint": PLATFORM_FIX_HINT.get(p, ""),
            "backoffice_url": task.backoffice_url}


@router.post("/{task_id}/done", summary="标记任务完成")
def done(task_id: str, user: User = Depends(get_current_user),
         db: Session = Depends(get_db)):
    t = (db.query(PlatformTask)
         .filter(PlatformTask.id == task_id, PlatformTask.user_id == user.id).first())
    if not t:
        raise HTTPException(404, "任务不存在")
    t.status = "done"
    db.commit()
    return {"ok": True, "id": t.id, "status": t.status}
