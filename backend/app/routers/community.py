"""社区论坛 CRUD — 对标 Helium 10 Seller Connect Forum（forum.helium10.com）。

路由前缀：/api/v1/community
公开读；写操作需登录（get_current_user）。删除限作者本人。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db, User
from ..auth import get_current_user
from ..community_models import CommunityThread, CommunityReply, AcademyCertificate

router = APIRouter()


# ---------------- 社区分类目录（按跨境平台分子类别） ----------------
# 设计原则：分类主轴 = 卖家实际开店的市场平台（Helium 10 Seller Connect 同款思路），
# 不按国家拆分，只按平台归类；另设 Topics 承接跨平台横向话题（合规、定价、物流、本地化）。
PLATFORM_CATALOG = [
    # —— 市场平台 ——
    {"category": "amazon", "label": "Amazon", "emoji": "🇪🇺", "group": "Marketplaces"},
    {"category": "ebay", "label": "eBay", "emoji": "🇪🇺", "group": "Marketplaces"},
    {"category": "kaufland", "label": "Kaufland", "emoji": "🇩🇪", "group": "Marketplaces"},
    {"category": "otto", "label": "Otto", "emoji": "🇩🇪", "group": "Marketplaces"},
    {"category": "zalando", "label": "Zalando", "emoji": "🇩🇪", "group": "Marketplaces"},
    {"category": "cdiscount", "label": "Cdiscount", "emoji": "🇫🇷", "group": "Marketplaces"},
    {"category": "fnac", "label": "Fnac", "emoji": "🇫🇷", "group": "Marketplaces"},
    {"category": "allegro", "label": "Allegro", "emoji": "🇵🇱", "group": "Marketplaces"},
    {"category": "bol-com", "label": "bol.com", "emoji": "🇳🇱", "group": "Marketplaces"},
    {"category": "wallapop", "label": "Wallapop", "emoji": "🇪🇸", "group": "Marketplaces"},
    {"category": "aliexpress", "label": "AliExpress", "emoji": "🌏", "group": "Marketplaces"},
    {"category": "etsy", "label": "Etsy", "emoji": "🌏", "group": "Marketplaces"},
    {"category": "temu", "label": "Temu", "emoji": "🌏", "group": "Marketplaces"},
    {"category": "shein", "label": "SHEIN", "emoji": "🌏", "group": "Marketplaces"},
    {"category": "shopify", "label": "Shopify / DTC", "emoji": "🚀", "group": "Marketplaces"},
    {"category": "own-store", "label": "Own webshop", "emoji": "🛒", "group": "Marketplaces"},
    # —— 横向话题（跨平台） ——
    {"category": "compliance", "label": "GPSR & compliance", "emoji": "📋", "group": "Topics"},
    {"category": "pricing", "label": "Pricing & fees", "emoji": "💶", "group": "Topics"},
    {"category": "logistics", "label": "Shipping & VAT", "emoji": "📦", "group": "Topics"},
    {"category": "localization", "label": "Localization", "emoji": "🌍", "group": "Topics"},
    {"category": "general", "label": "All marketplaces", "emoji": "💬", "group": "Topics"},
]
CATEGORY_INDEX = {p["category"]: p for p in PLATFORM_CATALOG}


# ---------------- 请求/响应模型 ----------------
class ThreadCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=10000)
    category: str = "general"
    language: str = "en"   # en / de / fr（英文首发，欧洲多语）
    tags: str = ""


class ReplyCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class CertBadge(BaseModel):
    cert_code: str
    course_title: str


class ThreadOut(BaseModel):
    id: str
    user_id: str
    author_name: str
    category: str
    language: str
    title: str
    body: str
    tags: str
    reply_count: int
    is_pinned: bool
    created_at: datetime
    author_certs: list[CertBadge] = []   # Academy 证书徽章（打通论坛身份）

    class Config:
        from_attributes = True


class ReplyOut(BaseModel):
    id: str
    thread_id: str
    author_name: str
    body: str
    created_at: datetime
    author_certs: list[CertBadge] = []

    class Config:
        from_attributes = True


# ---------------- 证书徽章（Academy × 论坛身份打通） ----------------
def _attach_certs(db: Session, items: list) -> dict:
    """给 thread/reply ORM 对象挂 author_certs（每人最新 2 枚），返回映射。

    传播链设计：徽章展示 cert_code，点击跳公开验证页
    /academy#verify/{cert_code} —— 每个帖子都是证书的获客入口。
    """
    ids = {i.user_id for i in items if getattr(i, "user_id", None)}
    if not ids:
        return {}
    rows = (db.query(AcademyCertificate)
            .filter(AcademyCertificate.user_id.in_(ids))
            .order_by(AcademyCertificate.issued_at.desc())
            .all())
    m: dict = {}
    for c in rows:
        lst = m.setdefault(c.user_id, [])
        if len(lst) < 2:
            lst.append({"cert_code": c.cert_code, "course_title": c.course_title})
    for i in items:
        i.author_certs = m.get(i.user_id, [])
    return m


# ---------------- 读取 ----------------
@router.get("/categories", summary="社区版块及帖子数（平台目录 + 计数）")
def categories(db: Session = Depends(get_db)):
    """返回完整平台目录（即使 0 帖也展示）+ 实时计数 + 分组，供侧边栏渲染。"""
    rows = dict(
        db.query(CommunityThread.category, func.count(CommunityThread.id))
        .group_by(CommunityThread.category)
        .all()
    )
    out = []
    for p in PLATFORM_CATALOG:
        out.append({**p, "count": rows.get(p["category"], 0)})
    # 兼容历史自定义分类
    for c, n in rows.items():
        if c not in CATEGORY_INDEX:
            out.append({"category": c, "label": c.replace("-", " ").title(),
                        "emoji": "💬", "group": "Topics", "count": n})
    return out


@router.get("/platforms", summary="平台目录（发帖时选择平台用）")
def platforms():
    return [{"category": p["category"], "label": p["label"], "emoji": p["emoji"], "group": p["group"]}
            for p in PLATFORM_CATALOG]


@router.get("/threads", response_model=list[ThreadOut], summary="帖子列表（可按平台/语言筛选 + 排序 + 分页）")
def list_threads(category: str = None, lang: str = None, sort: str = "latest",
                 limit: int = 50, offset: int = 0,
                 db: Session = Depends(get_db)):
    q = db.query(CommunityThread)
    if category:
        q = q.filter(CommunityThread.category == category)
    if lang:
        q = q.filter(CommunityThread.language == lang)
    if sort == "hot":
        q = q.order_by(CommunityThread.is_pinned.desc(), CommunityThread.reply_count.desc(),
                       CommunityThread.created_at.desc())
    elif sort == "unanswered":
        q = q.order_by(CommunityThread.is_pinned.desc(), CommunityThread.reply_count.asc(),
                       CommunityThread.created_at.desc())
    else:
        q = q.order_by(CommunityThread.is_pinned.desc(), CommunityThread.created_at.desc())
    threads = (
        q.offset(offset)
        .limit(limit)
        .all()
    )
    _attach_certs(db, threads)
    return threads


@router.get("/threads/{tid}", summary="帖子详情 + 全部回复")
def get_thread(tid: str, db: Session = Depends(get_db)):
    thread = db.get(CommunityThread, tid)
    if thread is None:
        raise HTTPException(status_code=404, detail="帖子不存在")
    replies = (
        db.query(CommunityReply)
        .filter(CommunityReply.thread_id == tid)
        .order_by(CommunityReply.created_at)
        .all()
    )
    _attach_certs(db, [thread] + replies)
    return {
        "thread": ThreadOut.model_validate(thread),
        "replies": [ReplyOut.model_validate(r) for r in replies],
    }


# ---------------- 写入（需登录） ----------------
@router.post("/threads", response_model=ThreadOut, summary="发帖")
def create_thread(req: ThreadCreate, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    t = CommunityThread(
        user_id=user.id,
        author_name=user.full_name or user.email.split("@")[0],
        category=req.category,
        language=req.language,
        title=req.title,
        body=req.body,
        tags=req.tags,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    _attach_certs(db, [t])
    return t


@router.post("/threads/{tid}/replies", response_model=ReplyOut, summary="回帖")
def add_reply(tid: str, req: ReplyCreate, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    thread = db.get(CommunityThread, tid)
    if thread is None:
        raise HTTPException(status_code=404, detail="帖子不存在")
    r = CommunityReply(
        thread_id=tid,
        user_id=user.id,
        author_name=user.full_name or user.email.split("@")[0],
        body=req.body,
    )
    db.add(r)
    thread.reply_count = (thread.reply_count or 0) + 1
    db.commit()
    db.refresh(r)
    _attach_certs(db, [r])
    return r


@router.delete("/threads/{tid}", summary="删帖（仅作者本人）")
def delete_thread(tid: str, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    thread = db.get(CommunityThread, tid)
    if thread is None:
        raise HTTPException(status_code=404, detail="帖子不存在")
    if thread.user_id != user.id:
        raise HTTPException(status_code=403, detail="仅作者可删除")
    db.delete(thread)  # 级联删除回复
    db.commit()
    return {"ok": True}
