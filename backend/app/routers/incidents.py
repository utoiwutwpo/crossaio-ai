"""事故闭环接口：检测、列表、关闭。"""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..automation.incident_pipeline import build_incident
from ..database import IncidentRecord, get_db, User

router = APIRouter()


class IncidentRequest(BaseModel):
    platform: str = "amazon"
    message: str = Field(..., min_length=1, max_length=4000)
    sku: str = ""
    product_name: str = ""
    language: str = "en"


@router.post("/detect", summary="识别安全事件并生成闭环产物（档案/下架/上报倒计时）")
def detect(req: IncidentRequest, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    from ..entitlements import addon_credits, consume_addon
    if getattr(user, "plan", "free") != "business" and addon_credits(db, user, "incident") <= 0:
        raise HTTPException(402, detail={
            "reason_code": "plan_required",
            "hint": "事故闭环属 Business 能力；非 Business 需先购买 incident 加购（$15/次）",
            "action": "incident",
        })
    result = build_incident(db, user, platform=req.platform, message=req.message,
                            sku=req.sku, product_name=req.product_name,
                            language=req.language)
    if result.get("is_incident"):
        try:
            consume_addon(db, user, "incident", ref_id=result.get("incident_id", ""))
            db.commit()
        except Exception:
            db.rollback()
    return result


@router.get("", summary="事故档案列表")
def list_incidents(page: int = 1, page_size: int = 20,
                   user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    q = (db.query(IncidentRecord).filter(IncidentRecord.user_id == user.id)
         .order_by(IncidentRecord.created_at.desc()))
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "items": [{
        "id": r.id, "platform": r.platform, "sku": r.sku,
        "status": r.status, "severity": r.severity,
        "deadline_at": r.deadline_at, "created_at": r.created_at,
    } for r in rows]}


@router.get("/{incident_id}", summary="事故档案详情")
def detail(incident_id: str, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    r = (db.query(IncidentRecord)
         .filter(IncidentRecord.id == incident_id,
                 IncidentRecord.user_id == user.id).first())
    if not r:
        raise HTTPException(404, "事故档案不存在")
    return {"id": r.id, "status": r.status,
            "dossier": json.loads(r.dossier_json or "{}"),
            "deadline_at": r.deadline_at}


@router.post("/{incident_id}/close", summary="关闭事故档案（需先完成上报评估）")
def close(incident_id: str, user: User = Depends(get_current_user),
          db: Session = Depends(get_db)):
    r = (db.query(IncidentRecord)
         .filter(IncidentRecord.id == incident_id,
                 IncidentRecord.user_id == user.id).first())
    if not r:
        raise HTTPException(404, "事故档案不存在")
    r.status = "closed"
    db.commit()
    return {"ok": True, "id": r.id, "status": r.status}
