"""Academy 模块 — Helium 10 Freedom Ticket 机制的代码化：
教育护城河（结构化课程）→ 术语同化（课程全程用 CrossAIO 术语讲课 + 统一术语表）
→ 自然获客（结业证书公开验证页，学员晒证书即品牌传播）。

路由前缀：/api/v1/academy
- GET  /courses                     公开：课程列表（?lang=en|de|fr）
- GET  /courses/{slug}              公开：课程详情 + 课时目录（含预览标记）
- GET  /lessons/{slug}              课时正文：免费课全开；pro 课仅预览课开放，
                                    其余对 free 用户返回缺口式付费墙（teaser）
- POST /lessons/{slug}/complete     登录：标记课时完成
- GET  /my-progress                 登录：按课程汇总学习进度
- POST /courses/{slug}/certificate  登录：完成全部课时后颁发证书
- GET  /verify/{cert_code}          公开：证书验证（获客页数据源，带品牌 CTA）
- GET  /glossary                    公开：CrossAIO 统一术语表（术语同化的 API 载体）
"""
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db, User
from ..auth import get_current_user, get_optional_user
from ..community_models import (AcademyCourse, AcademyLesson,
                                AcademyProgress, AcademyCertificate)

router = APIRouter()

_STAFF_PLANS = ("pro", "business")

# CrossAIO 术语表 —— 术语同化的单一数据源：课程/博客/论坛/峰会全站引用这些词，
# 用户学会用它们思考合规问题后，自然搜索/推荐这些词 → 品牌词自然获客。
_GLOSSARY = [
    {"term": "Readiness Score", "definition": "CrossAIO's 0-100 score of how ready a listing "
        "is to pass marketplace compliance checks. Introduced in GPSR Bootcamp Lesson 6."},
    {"term": "Risk Level", "definition": "Low / Medium / High classification of a listing's "
        "regulatory exposure, produced by every CrossAIO audit."},
    {"term": "Gap Report", "definition": "The list of exactly what is missing (documents, "
        "labels, warnings) after a Compliance Audit. Free tier shows gaps; paid fixes them."},
    {"term": "EU Responsible Person (ERP)", "definition": "The legally required EU-based "
        "entity printed on listings and labels. CrossAIO stores and reuses yours in the ERP vault."},
    {"term": "Compliance Matrix", "definition": "CrossAIO's one-input table that maps a product "
        "to the attribute trees of all 13 supported marketplaces at once."},
    {"term": "Listing Watch", "definition": "Daily automated monitoring that catches listing "
        "drift (edited titles, dropped attributes, removed safety info) before it costs sales."},
    {"term": "AI Inbox", "definition": "CrossAIO's unified buyer-message inbox with "
        "multilingual AI replies in Art. 50-safe wording."},
    {"term": "Warning Pack", "definition": "Market-specific, local-language safety warning "
        "texts generated per country (DE/FR/PL/NL/RO...)."},
]


def _seed(db: Session) -> None:
    """首次访问播种 2 门英文课程（幂等）。课程正文全程使用 CrossAIO 术语 → 术语同化。"""
    if db.query(AcademyCourse).count() > 0:
        return
    c1 = AcademyCourse(
        slug="gpsr-compliance-bootcamp", language="en",
        title="GPSR Compliance Bootcamp", emoji="🛡️", level="free",
        is_published=True, sort_order=1,
        summary="Six practical lessons: from what GPSR legally requires to reading your "
                "Readiness Score like a pro. Free, forever.",
    )
    c2 = AcademyCourse(
        slug="listing-matrix-mastery", language="en",
        title="Multi-Platform Listing Matrix Mastery", emoji="🧩", level="pro",
        is_published=True, sort_order=2,
        summary="How to publish one product to 13 EU marketplaces without 13 rewrites. "
                "Lesson 1 free; full course with Pro.",
    )
    db.add(c1); db.add(c2); db.flush()

    l1 = [
        ("what-gpsr-requires", "What GPSR Actually Requires",
         "GPSR replaced the old General Product Safety Directive, and marketplaces are now "
         "legally liable for what they host. Practically, that means one thing: **before** your "
         "listing goes live, the platform must see compliance signals - an EU Responsible "
         "Person, traceability marking, technical documentation on request, and local-language "
         "safety warnings.\n"
         "In CrossAIO terms, every product you audit gets a **Risk Level** (Low / Medium / High) "
         "and a **Readiness Score** from 0 to 100. The score is not vanity - marketplaces "
         "increasingly behave as if it were a gate.\n"
         "By the end of this bootcamp you will run your own **Compliance Audit**, read the "
         "**Gap Report**, and know precisely which of the four GPSR pillars your catalog is missing.",
         12),
        ("eu-responsible-person", "The EU Responsible Person: Your Legal Anchor",
         "Non-EU sellers cannot self-declare under GPSR. You need an **EU Responsible Person "
         "(ERP)** - an EU-established entity that holds your compliance documentation and whose "
         "name and address must appear on the listing and the product label.\n"
         "Common mistakes: printing a freight forwarder's address (not legal), using an ERP for "
         "one SKU family across unrelated product categories, and forgetting to update the ERP "
         "after a supplier change.\n"
         "CrossAIO keeps your ERP details in a reusable vault and stamps them into every "
         "localized listing automatically - so an ERP change is one edit, not 400 listing edits.",
         10),
        ("technical-documentation", "Technical Documentation: The 10-Year Perspective",
         "GPSR requires technical documentation - test reports, risk assessment, declaration of "
         "conformity - to be **kept for 10 years** and produced to a market surveillance "
         "authority 'within a reasonable time'. In enforcement practice, 'reasonable' means "
         "days, not weeks.\n"
         "Build a per-product doc set at onboarding, not per-incident. In CrossAIO, each audit "
         "links the missing documents in the **Gap Report**, so the checklist is generated for "
         "you instead of remembered.\n"
         "Rule of thumb: if a document cannot be retrieved in one click, treat it as missing.",
         10),
        ("local-language-warnings", "Local-Language Safety Warnings That Pass",
         "Safety information must be provided in the language of each market where the product "
         "is sold. English-only warnings fail in DE, FR, PL, NL and RO - and marketplaces now "
         "scan for this automatically.\n"
         "CrossAIO generates a **Warning Pack** per country: legally-shaped local-language "
         "warning texts matched to your product category, ready to paste into listing fields or "
         "artwork.\n"
         "Two rules: never machine-translate warnings without a compliance-shaped template, and "
         "never reuse a competitor's wording (their errors become your liability).",
         10),
        ("first-compliance-audit", "Hands-On: Run Your First Compliance Audit",
         "Time to practice. Open the CrossAIO workbench, paste a product name and marketplace, "
         "and run a **Compliance Audit**. You will get a **Risk Level**, a **Readiness Score**, "
         "and a **Gap Report** listing every missing pillar.\n"
         "The free tier shows the full gap list but does not fix it - that is deliberate. Read "
         "the gaps first; decide whether fixing is your job or ours. The audit is free and "
         "repeatable, so run it on your three best-selling SKUs before continuing.",
         12),
        ("reading-readiness-score", "Reading Your Readiness Score Like a Pro",
         "The **Readiness Score** weights four pillars: ERP presence, documentation, "
         "traceability marking, and local-language warnings. A score below 60 means the listing "
         "is realistically blockable on strict platforms (Kaufland, bol.com); 60-85 usually "
         "passes now but breaks at the next rule update.\n"
         "Professionals track the **trend**, not the snapshot: schedule the daily **Listing "
         "Watch** and watch your score react to edits. When every SKU sits above 85, you are "
         "not just compliant - you are unhurable by the next enforcement wave.\n"
         "This completes the bootcamp. Your certificate unlocks below - and yes, it is meant "
         "for your LinkedIn.",
         10),
    ]
    l2 = [
        ("why-one-listing-fails", "Why One Listing Never Fits 13 Marketplaces",
         "Amazon, eBay, Allegro, Kaufland, bol.com, eMAG, Cdiscount, Otto... each platform "
         "enforces its own title structure, attribute tree, category taxonomy and language "
         "quality bar. The industry answer - 'translate the Amazon listing' - is why localized "
         "listings rank poorly and get rejected.\n"
         "The CrossAIO approach is the **Compliance Matrix**: you maintain one master product "
         "record, and the matrix maps it into each platform's attribute tree. This course shows "
         "you how to build a master record that survives 13 platforms. Lesson 1 is the free "
         "preview - the remaining lessons need Pro.",
         12),
        ("attribute-trees", "Attribute Trees: Map Once, Publish Everywhere",
         "Each marketplace's attribute tree (brand, model, material, safety fields...) is where "
         "most listings silently fail: a missing mandatory attribute means rejection or search "
         "invisibility. In the **Compliance Matrix**, you fill each attribute once with a "
         "platform-neutral value; CrossAIO projects it into every platform's format.",
         14),
        ("listing-watch", "Listing Watch: Catch Drift Before It Costs You",
         "Marketplace edits, competitor complaints and platform rule updates silently degrade "
         "live listings. **Listing Watch** re-audits your matrix daily and alerts on drift - "
         "dropped safety fields, edited titles, changed attribute values - with a diff against "
         "your master record.",
         12),
        ("ai-inbox", "The AI Inbox: Buyers in Five Languages, Art.50-Safe",
         "Post-sale compliance now includes responding to buyer messages in local language "
         "within marketplace SLAs. CrossAIO's **AI Inbox** unifies messages across platforms "
         "and drafts multilingual replies with Article 50-safe wording - meaning the AI's "
         "output is reviewed and attributed per EU AI Act transparency rules.",
         12),
    ]
    for i, (slug, title, body, dur) in enumerate(l1):
        db.add(AcademyLesson(course_id=c1.id, slug=slug, title=title, body=body,
                             duration_min=dur, is_free_preview=True, sort_order=i))
    for i, (slug, title, body, dur) in enumerate(l2):
        db.add(AcademyLesson(course_id=c2.id, slug=slug, title=title, body=body,
                             duration_min=dur, is_free_preview=(i == 0), sort_order=i))
    db.commit()


# ---------------- 课程（公开） ----------------
@router.get("/courses", summary="课程列表（?lang=en|de|fr）")
def list_courses(lang: str = "en", db: Session = Depends(get_db)):
    _seed(db)
    courses = (db.query(AcademyCourse)
               .filter(AcademyCourse.is_published.is_(True),
                       AcademyCourse.language == (lang if lang in ("en", "de", "fr") else "en"))
               .order_by(AcademyCourse.sort_order).all())
    return [{"id": c.id, "slug": c.slug, "title": c.title, "summary": c.summary,
             "emoji": c.emoji, "level": c.level, "lesson_count": len(c.lessons)}
            for c in courses]


@router.get("/courses/{slug}", summary="课程详情 + 课时目录")
def course_detail(slug: str, db: Session = Depends(get_db)):
    c = db.query(AcademyCourse).filter(AcademyCourse.slug == slug).first()
    if c is None or not c.is_published:
        raise HTTPException(status_code=404, detail="course not found")
    return {
        "slug": c.slug, "title": c.title, "summary": c.summary,
        "emoji": c.emoji, "level": c.level,
        "lessons": [{"slug": l.slug, "title": l.title, "duration_min": l.duration_min,
                     "is_free_preview": l.is_free_preview, "sort_order": l.sort_order}
                    for l in c.lessons],
    }


# ---------------- 课时（含缺口式付费墙） ----------------
@router.get("/lessons/{slug}", summary="课时正文（pro 课非预览课对 free 用户返回 teaser）")
def lesson_detail(slug: str, user: User | None = Depends(get_optional_user),
                  db: Session = Depends(get_db)):
    l = db.query(AcademyLesson).filter(AcademyLesson.slug == slug).first()
    if l is None:
        raise HTTPException(status_code=404, detail="lesson not found")
    c = l.course
    has_access = (c.level == "free" or l.is_free_preview
                  or (user is not None and user.plan in _STAFF_PLANS))
    if has_access:
        return {"slug": l.slug, "title": l.title, "body": l.body,
                "duration_min": l.duration_min, "course_slug": c.slug,
                "course_title": c.title, "paywalled": False}
    # 缺口式付费墙：给足结构与前 2 段，不给全文（与免费体检同款心理）
    teaser = "\n\n".join(l.body.split("\n\n")[:2])
    return {"slug": l.slug, "title": l.title, "body": teaser,
            "duration_min": l.duration_min, "course_slug": c.slug,
            "course_title": c.title, "paywalled": True,
            "upgrade_url": "/pricing",
            "paywall_note": "This lesson is part of the Pro academy. "
                            "Lesson 1 is free - upgrade to unlock all lessons."}


# ---------------- 进度（登录） ----------------
class CompleteIn(BaseModel):
    pass  # 保留请求体扩展位


@router.post("/lessons/{slug}/complete", summary="标记课时完成")
def complete_lesson(slug: str, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    l = db.query(AcademyLesson).filter(AcademyLesson.slug == slug).first()
    if l is None:
        raise HTTPException(status_code=404, detail="lesson not found")
    exists = (db.query(AcademyProgress)
              .filter(AcademyProgress.user_id == user.id,
                      AcademyProgress.lesson_id == l.id).first())
    if not exists:
        db.add(AcademyProgress(user_id=user.id, lesson_id=l.id))
        db.commit()
    total = len(l.course.lessons)
    done = (db.query(AcademyProgress)
            .join(AcademyLesson, AcademyProgress.lesson_id == AcademyLesson.id)
            .filter(AcademyProgress.user_id == user.id,
                    AcademyLesson.course_id == l.course_id).count())
    return {"lesson": slug, "course_progress": f"{done}/{total}"}


@router.get("/my-progress", summary="我的学习进度（按课程汇总）")
def my_progress(user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    rows = (db.query(AcademyLesson.course_id,
                     db.func.count(AcademyProgress.id))
            .outerjoin(AcademyProgress,
                       (AcademyProgress.lesson_id == AcademyLesson.id)
                       & (AcademyProgress.user_id == user.id))
            .group_by(AcademyLesson.course_id).all())
    out = []
    for course_id, done in rows:
        c = db.get(AcademyCourse, course_id)
        if c is None:
            continue
        total = len(c.lessons)
        cert = (db.query(AcademyCertificate)
                .filter(AcademyCertificate.user_id == user.id,
                        AcademyCertificate.course_id == c.id).first())
        out.append({"course_slug": c.slug, "course_title": c.title,
                    "done": done, "total": total,
                    "percent": round(done * 100 / total) if total else 0,
                    "certificate": cert.cert_code if cert else None})
    return {"courses": out}


# ---------------- 证书（结业即获客钩子） ----------------
@router.post("/courses/{slug}/certificate", summary="完成全部课时后颁发证书")
def issue_certificate(slug: str, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    c = db.query(AcademyCourse).filter(AcademyCourse.slug == slug).first()
    if c is None or not c.is_published:
        raise HTTPException(status_code=404, detail="course not found")
    total = len(c.lessons)
    done = (db.query(AcademyProgress)
            .join(AcademyLesson, AcademyProgress.lesson_id == AcademyLesson.id)
            .filter(AcademyProgress.user_id == user.id,
                    AcademyLesson.course_id == c.id).count())
    if total == 0 or done < total:
        raise HTTPException(status_code=400,
                            detail=f"Course not finished yet ({done}/{total})")
    existing = (db.query(AcademyCertificate)
                .filter(AcademyCertificate.user_id == user.id,
                        AcademyCertificate.course_id == c.id).first())
    if existing:
        return {"cert_code": existing.cert_code, "issued_at": str(existing.issued_at),
                "verify_url": f"/academy/verify/{existing.cert_code}", "already": True}
    cert = AcademyCertificate(
        cert_code="XA-" + uuid4().hex[:10].upper(),
        user_id=user.id, course_id=c.id,
        learner_name=user.full_name or user.email.split("@")[0],
        course_title=c.title,
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return {"cert_code": cert.cert_code, "learner_name": cert.learner_name,
            "course_title": cert.course_title,
            "verify_url": f"/academy/verify/{cert.cert_code}"}


@router.get("/verify/{cert_code}", summary="公开证书验证（获客页数据源，带品牌 CTA）")
def verify_certificate(cert_code: str, db: Session = Depends(get_db)):
    cert = (db.query(AcademyCertificate)
            .filter(AcademyCertificate.cert_code == cert_code.upper()).first())
    if cert is None:
        return {"valid": False}
    return {"valid": True, "learner_name": cert.learner_name,
            "course_title": cert.course_title, "issued_at": str(cert.issued_at),
            "cta": "Earn your GPSR Compliance certificate - free bootcamp at CrossAIO"}


# ---------------- 术语表（术语同化的统一数据源） ----------------
@router.get("/glossary", summary="CrossAIO 统一术语表（课程/博客/论坛全站引用）")
def glossary():
    return {"terms": _GLOSSARY}
