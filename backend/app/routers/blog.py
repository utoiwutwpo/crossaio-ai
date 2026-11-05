"""博客内容矩阵 — 对标 Helium 10 Freedom Ticket / Blog 教育护城河。

路由前缀：/api/v1/blog
- GET  /posts        公开：已发布文章列表（?lang=en|de|fr，默认 en）
- GET  /posts/{slug} 公开：文章详情（浏览计数 +1）
- POST /posts        管理（Pro/Business）：新增文章（草稿或发布）
首次访问自动播种 3 篇英文种子文章（GPSR / 透明定价 / 多平台规则）。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db, User
from ..auth import get_current_user
from ..community_models import BlogPost

router = APIRouter()


# ---------------- 权限闸（与 summit 一致：付费套餐 = 内容运营） ----------------
_STAFF_PLANS = ("pro", "business")


def _require_staff(user: User) -> User:
    if user.plan not in _STAFF_PLANS:
        raise HTTPException(status_code=403, detail="Pro/Business plan required")
    return user


# ---------------- 请求/响应模型 ----------------
class PostCreate(BaseModel):
    slug: str = Field(min_length=3, max_length=120, pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=1, max_length=300)
    excerpt: str = ""
    body: str = ""
    author: str = "CrossAIO Team"
    tags: str = ""
    language: str = "en"           # en / de / fr
    is_published: bool = False


class PostOut(BaseModel):
    id: str
    slug: str
    language: str
    title: str
    excerpt: str
    author: str
    tags: str
    views: int
    is_published: bool
    published_at: datetime | None

    class Config:
        from_attributes = True


class PostDetailOut(PostOut):
    body: str


# ---------------- 种子内容（英文首发） ----------------
_SEED_POSTS = [
    {
        "slug": "gpsr-explained-eu-sellers-guide",
        "title": "GPSR Explained: The Complete Compliance Guide for EU Cross-Border Sellers",
        "excerpt": "The General Product Safety Regulation is now enforced at marketplace level. "
                   "Here is exactly what non-EU sellers must prepare before listings get blocked.",
        "tags": "gpsr,compliance,eu",
        "body": (
            "## Why GPSR matters now\n\n"
            "The EU General Product Safety Regulation (GPSR) replaced the old GPS Directive. "
            "Marketplaces such as Amazon, eBay, Allegro, Kaufland and bol.com are now legally "
            "required to verify compliance **before** a listing goes live. Non-compliant listings "
            "are not fined quietly - they are blocked at the feed level.\n\n"
            "## The four things every non-EU seller needs\n\n"
            "1. **An EU Responsible Person (ERP)** whose name and address appear on the listing "
            "and the product label.\n"
            "2. **Technical documentation**: test reports, risk assessment, declaration of "
            "conformity - kept for 10 years and producible within days.\n"
            "3. **Local-language safety warnings** for every market you sell in "
            "(DE, FR, PL, NL, RO...).\n"
            "4. **Traceability marking**: manufacturer, importer and batch identifiers.\n\n"
            "## The 30-second self-check\n\n"
            "Run the free CrossAIO health check (no registration needed). It reports your risk "
            "level, readiness score and the exact missing items - but does not fix them. "
            "Fixing is what the platform automates once you sign up.\n\n"
            "## What happens if you ignore it\n\n"
            "Expect listing removals, frozen payouts on repeat offences, and in the worst case "
            "a marketplace account suspension. Marketplaces carry legal liability now, so they "
            "enforce first and ask questions later.\n\n"
            "*This article is general information, not legal advice.*"
        ),
    },
    {
        "slug": "hidden-fees-localization-services",
        "title": "Hidden Fees of Listing Localization Services - and How CrossAIO Is Different",
        "excerpt": "A headline price of zero can still cost you thousands. The four fee traps "
                   "of traditional localization services, and the flat-pricing alternative.",
        "tags": "pricing,transparency,localization",
        "body": (
            "## The headline price is not the price\n\n"
            "Several established localization services advertise a free or cheap starter plan. "
            "Sellers on public review sites report discovering only afterwards that the real cost "
            "includes a **success commission on every sale**, a **per-item processing fee**, and "
            "a **monthly minimum** that applies even in months with zero sales.\n\n"
            "## The four fee traps\n\n"
            "1. **Success commission** - a percentage of revenue on every translated listing, "
            "forever.\n"
            "2. **Per-item fees** - charged per listing per month, scaling silently with your "
            "catalog size.\n"
            "3. **Monthly minimums** - you pay even when the service moves nothing.\n"
            "4. **Hard cancellation** - users report that stopping billing requires emails and "
            "phone calls, and that closing the account can leave listings altered with no revert.\n\n"
            "## How CrossAIO prices differently\n\n"
            "- **Flat monthly price. No commission, no per-item fee, no monthly minimum.**\n"
            "- **Cancel in one click**, effective immediately, self-serve.\n"
            "- **Clean exit**: export everything and your listings revert to the originals.\n"
            "- **See problems first**: the free GPSR health check shows what is broken before "
            "you ever enter a payment method.\n\n"
            "Compare the details any time on our trust page - the numbers are public."
        ),
    },
    {
        "slug": "eu-marketplace-rules-cheatsheet",
        "title": "Allegro, Kaufland, bol.com, eMAG: Listing Rules Cheat Sheet for EU Marketplaces",
        "excerpt": "Four fast-growing EU marketplaces, four different rulebooks. Title length, "
                   "required attributes, VAT display and local-language requirements in one table.",
        "tags": "allegro,kaufland,bol,emag,marketplaces",
        "body": (
            "## Why local marketplaces out-convert the big two\n\n"
            "Amazon and eBay dominate the headlines, but Allegro (PL), Kaufland (DE/AT/CZ...), "
            "bol.com (NL/BE) and eMAG (RO/HU/BG) often deliver higher conversion for localized "
            "sellers - because competition is thinner and local buyers trust local platforms.\n\n"
            "## The rule differences that get listings rejected\n\n"
            "- **Titles**: Allegro is generous but keyword-sensitive; bol.com enforces strict "
            "brand + model structure; Kaufland rejects all-caps and promo language.\n"
            "- **Attributes**: each platform has its own mandatory attribute tree - mapping "
            "once and reusing everywhere is the core CrossAIO matrix feature.\n"
            "- **Language**: all four require fluent local language; machine-translated text "
            "without review routinely gets low search ranking.\n"
            "- **GPSR fields**: responsible person and safety info are now mandatory fields "
            "on all four.\n\n"
            "## A practical rollout order\n\n"
            "Start with the marketplace whose language you can support best, prove unit "
            "economics, then expand. The CrossAIO rules library (open source, MIT) publishes "
            "each platform's checklist for free."
        ),
    },
]


def _ensure_seed(db: Session) -> None:
    """首次访问且表为空时播种英文种子文章（幂等）。"""
    if db.query(BlogPost).count() > 0:
        return
    now = datetime.utcnow()
    for p in _SEED_POSTS:
        db.add(BlogPost(
            slug=p["slug"],
            language="en",
            title=p["title"],
            excerpt=p["excerpt"],
            body=p["body"],
            author="CrossAIO Team",
            tags=p["tags"],
            is_published=True,
            published_at=now,
        ))
    db.commit()


# ---------------- 读取（公开） ----------------
@router.get("/posts", response_model=list[PostOut], summary="已发布文章列表（?lang=en|de|fr）")
def list_posts(lang: str = "en", tag: str = None, limit: int = 50,
               db: Session = Depends(get_db)):
    _ensure_seed(db)
    q = db.query(BlogPost).filter(
        BlogPost.is_published.is_(True),
        BlogPost.language == (lang if lang in ("en", "de", "fr") else "en"),
    )
    if tag:
        q = q.filter(BlogPost.tags.contains(tag))
    return q.order_by(BlogPost.published_at.desc()).limit(limit).all()


@router.get("/posts/{slug}", response_model=PostDetailOut, summary="文章详情（浏览 +1）")
def get_post(slug: str, db: Session = Depends(get_db)):
    p = db.query(BlogPost).filter(
        BlogPost.slug == slug, BlogPost.is_published.is_(True)
    ).first()
    if p is None:
        raise HTTPException(status_code=404, detail="post not found")
    p.views = (p.views or 0) + 1
    db.commit()
    db.refresh(p)
    return p


# ---------------- 管理（Pro/Business） ----------------
@router.post("/posts", response_model=PostDetailOut, summary="新增文章（草稿或发布）")
def create_post(req: PostCreate, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    _require_staff(user)
    if db.query(BlogPost).filter(BlogPost.slug == req.slug).first():
        raise HTTPException(status_code=409, detail="slug already exists")
    p = BlogPost(
        slug=req.slug,
        language=req.language,
        title=req.title,
        excerpt=req.excerpt,
        body=req.body,
        author=req.author,
        tags=req.tags,
        is_published=req.is_published,
        published_at=datetime.utcnow() if req.is_published else None,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p
