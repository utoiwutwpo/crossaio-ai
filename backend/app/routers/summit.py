"""虚拟峰会模块 — 对标 Helium 10 / Prosper Show 活动闭环。

路由前缀：/api/v1/summit
- GET  /info          公开：峰会信息 + 日程 + 报名数（落地页用）
- POST /register      公开：报名（带 UTM 归因，复用现有范式）
- GET  /registrations 管理（付费套餐）：报名列表
- POST /sessions      管理（付费套餐）：新增日程
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session

from ..database import get_db, User
from ..auth import get_current_user
from ..community_models import SummitRegistration, SummitSession

router = APIRouter()


# ---------------- 权限闸（MVP：付费套餐即视为运营人员） ----------------
# 生产应接入 RBAC / 角色字段，此处先用 plan 做最小可用闸，避免报名数据泄露给免费用户。
_STAFF_PLANS = ("pro", "business")


def _require_staff(user: User) -> User:
    if user.plan not in _STAFF_PLANS:
        raise HTTPException(status_code=403, detail="需 Pro/Business 套餐权限")
    return user


# ---------------- 模型 ----------------
class SummitRegister(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    company: str = ""
    utm_source: str = ""
    utm_medium: str = ""
    utm_campaign: str = ""


class SessionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    speaker: str = ""
    room: str = "main"
    starts_at: str = None  # ISO 时间字符串
    description: str = ""


class SessionOut(BaseModel):
    id: str
    title: str
    speaker: str
    room: str
    starts_at: datetime | None
    description: str

    class Config:
        from_attributes = True


class RegistrationOut(BaseModel):
    id: str
    name: str
    email: str
    company: str
    utm_source: str
    utm_medium: str
    utm_campaign: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------- 公开 ----------------
# 多语峰会文案：英文首发，保留 de / fr（欧洲多语 en/de/fr）
_SUMMIT_META = {
    "en": {
        "title": "Europe Cross-Border Compliance Summit",
        "tagline": "GPSR compliance · multi-platform localization · European growth — hosted by CrossAIO",
    },
    "de": {
        "title": "Europe Cross-Border Compliance Summit",
        "tagline": "GPSR-Konformität · Multi-Plattform-Lokalisierung · Europäisches Wachstum — von CrossAIO",
    },
    "fr": {
        "title": "Sommet Europe Cross-Border Compliance",
        "tagline": "Conformité GPSR · localisation multiplateforme · croissance européenne — par CrossAIO",
    },
}


@router.get("/info", summary="峰会信息 + 日程 + 报名数（落地页用；?lang=en|de|fr）")
def summit_info(lang: str = "en", db: Session = Depends(get_db)):
    lang = lang if lang in _SUMMIT_META else "en"
    meta = _SUMMIT_META[lang]
    sessions = (
        db.query(SummitSession)
        .order_by(SummitSession.starts_at)
        .all()
    )
    reg_count = db.query(SummitRegistration).count()
    return {
        "lang": lang,
        "title": meta["title"],
        "tagline": meta["tagline"],
        "registration_count": reg_count,
        "sessions": [SessionOut.model_validate(s) for s in sessions],
    }


@router.post("/register", summary="峰会报名（带 UTM 归因）")
def register(req: SummitRegister, db: Session = Depends(get_db)):
    r = SummitRegistration(
        name=req.name,
        email=req.email,
        company=req.company,
        utm_source=req.utm_source,
        utm_medium=req.utm_medium,
        utm_campaign=req.utm_campaign,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"id": r.id, "status": "registered", "email": r.email}


# ---------------- 管理（付费套餐） ----------------
@router.get("/registrations", response_model=list[RegistrationOut], summary="报名列表")
def list_registrations(user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    _require_staff(user)
    regs = db.query(SummitRegistration).order_by(SummitRegistration.created_at.desc()).all()
    return regs


@router.post("/sessions", response_model=SessionOut, summary="新增峰会日程")
def add_session(req: SessionCreate, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    _require_staff(user)
    s = SummitSession(
        title=req.title,
        speaker=req.speaker,
        room=req.room,
        starts_at=req.starts_at,
        description=req.description,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s
