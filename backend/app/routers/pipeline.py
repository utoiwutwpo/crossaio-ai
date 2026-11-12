"""一条流水线把四个版块串起来（用户视角：接入店铺 → 按订阅跑通）。

真实边界：
- 内容生成：任何套餐可用，受用量额度约束；不需要平台凭证。
- Agentic 问答：Business（`agentic_feed`）。
- 合规×事故：Business 内含；非 Business 走 incident 加购（$15/次）。
- AI 客服：回复只出草稿，不自动发；真发送属 Pro/Business（`send_message`）。
- 写回：只出 payload / 端点，真推需要该平台凭证 + SKU 映射，未接入时明确标注。
"""
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import User, get_db, ProductDescription
from ..schemas import ProductDescriptionRequest
from ..experts.product_description import ProductDescriptionExpert
from ..experts.platform_registry import platform_config
from ..experts.gpsr import required_languages
from ..experts.agentic_feed import build_qa
from ..experts.listing_push import build_listing_payload
from ..automation.incident_pipeline import build_incident
from ..billing import check_and_record_usage
from ..entitlements import ACTION_PLANS, addon_credits
from ..services.compliance_context import build_compliance_context
from ..platform_auth import get_connected_platforms

router = APIRouter()
expert = ProductDescriptionExpert()

LANGS = ["en", "de", "fr", "pl", "es", "it", "nl"]
SAFETY_HINTS = ["起火", "烧", "灼", "漏电", "短路", "冒烟", "爆炸", "起火", "bed bug",
                "fire", "burn", "smoke", "shock", "explode", "overheat", "unsafe",
                "choking", "strangl", "chemical", "recall"]


def _plan_ok(user: User, action: str) -> bool:
    return getattr(user, "plan", "free") in ACTION_PLANS.get(action, set())


def _market_langs(platform: str) -> List[str]:
    """该平台覆盖市场实际需要的语种（用于语种接入体检）。"""
    try:
        return required_languages(platform)
    except Exception:
        return ["en"]


def _lang_state(platform: str, lang: str) -> Dict:
    need = _market_langs(platform)
    if lang in need:
        return {"ok": True, "reason": "该平台市场官方语种"}
    if lang == "en":
        return {"ok": True, "reason": "英语可作跨境通用稿，非本地强制语言"}
    return {"ok": False, "reason": "该平台不覆盖 %s 市场；本地语言为 %s" % (lang, "/".join(need))}


class RunReq(BaseModel):
    product_name: str
    keywords: List[str] = []
    platforms: List[str] = []
    languages: List[str] = ["en"]
    sku: str = ""


@router.get("/pipeline/overview", summary="流水线总览：店铺授权 × 订阅 × 四段状态")
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    connected = sorted(get_connected_platforms(db, user.id))
    plan = getattr(user, "plan", "free")

    stages = [
        {"key": "content", "label": "① AI 商品内容（一次性输入，多平台多语种）",
         "state": "ready", "detail": "任何套餐可生成；按用量额度计量"},
        {"key": "agentic", "label": "② Agentic 2026（成稿转买家问答对）",
         "state": "ready" if _plan_ok(user, "agentic_feed") else "locked",
         "detail": "Business 专属" if not _plan_ok(user, "agentic_feed") else "Business 已含"},
        {"key": "incident", "label": "③ 合规×事故（安全特征扫描 → 档案/倒计时）",
         "state": "ready" if (plan == "business" or addon_credits(db, user, "incident") > 0) else "locked",
         "detail": "Business 内含" if plan == "business" else
                   ("可用加购额度 %d 次" % addon_credits(db, user, "incident") if addon_credits(db, user, "incident") > 0
                    else "非 Business 需 incident 加购（$15/次）")},
        {"key": "cs", "label": "④ AI 客服（成稿 → 高频问题 → 回复草稿）",
         "state": "ready" if _plan_ok(user, "send_message") else "locked",
         "detail": "只出草稿，点发送才回平台" if _plan_ok(user, "send_message") else "自动回复需 Pro 及以上"},
    ]
    live_stages = [s for s in stages if s["state"] == "ready"]
    return {
        "plan": plan,
        "connected": connected,
        "connected_count": len(connected),
        "missing": [p for p in ["amazon", "ebay", "fruugo", "walmart", "cdiscount",
                                "otto", "allegro", "emag", "kaufland", "bol", "zalando", "tiktok"]
                    if p not in connected],
        "stages": stages,
        "runnable": len(live_stages),
        "next_step": ("先去「平台凭证接入中心」保存至少一个平台凭证" if not connected
                      else "可直接一键跑通 %d/%d 段；未解锁的段按订阅升级或加购" % (len(live_stages), len(stages))),
    }


def _scan_safety(text: str) -> Optional[str]:
    low = (text or "").lower()
    for kw in SAFETY_HINTS:
        if kw.lower() in low:
            return kw
    return None


@router.post("/pipeline/run", summary="一键串四段：内容 → Agentic → 合规事故 → 客服草稿")
def run(req: RunReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plats = [p for p in dict.fromkeys(req.platforms)][:9]
    langs = [l for l in dict.fromkeys(req.languages or ["en"])][:7]
    if not req.product_name.strip():
        raise HTTPException(422, detail="产品名不能为空")
    if not plats or not langs:
        raise HTTPException(422, detail="至少选择一个平台与一个语种")

    connected = get_connected_platforms(db, user.id)
    items: List[Dict] = []
    errors: List[Dict] = []
    quota_hit = None

    for lang in langs:
        for platform in plats:
            if quota_hit:
                errors.append({"platform": platform, "language": lang, "error": quota_hit})
                continue
            ctx = build_compliance_context(db, user.id, platform=platform, product_name=req.product_name)
            try:
                check_and_record_usage(db, user, "product_desc", with_compliance=ctx["found"])
            except HTTPException as e:
                quota_hit = "额度不足：%s" % (e.detail if isinstance(e.detail, str) else "用量已满")
                errors.append({"platform": platform, "language": lang, "error": quota_hit})
                continue

            single = ProductDescriptionRequest(
                product_name=req.product_name, keywords=req.keywords,
                platform=platform, language=lang, tone="professional")
            gen = None
            last_err = None
            for _attempt in range(3):
                try:
                    gen = expert.generate(single, compliance_block=ctx["prompt_block"])
                    break
                except Exception as e:
                    last_err = e
            if gen is None:
                errors.append({"platform": platform, "language": lang,
                               "error": "生成失败：%s" % last_err})
                continue

            gen.platform = platform
            rec = ProductDescription(
                user_id=user.id, product_name=req.product_name, platform=platform,
                language=gen.language, tone="professional", title=gen.title,
                bullet_points=[b.model_dump() for b in gen.bullet_points],
                description=gen.description, search_terms=gen.search_terms,
                optimization_score=gen.optimization_score,
                platform_compliant=gen.platform_compliant,
                related_audit_id=ctx["audit_id"])
            db.add(rec)
            db.commit()
            db.refresh(rec)

            lst = _lang_state(platform, lang)
            item = {"platform": platform, "language": gen.language, "desc_id": rec.id,
                    "title": gen.title, "characters": len(gen.description),
                    "optimization_score": gen.optimization_score,
                    "language_ok": lst["ok"], "language_note": lst["reason"],
                    "compliant": bool(gen.platform_compliant)}

            # ② Agentic
            if _plan_ok(user, "agentic_feed"):
                try:
                    qa = build_qa(rec, platform=platform, language=lang, n=5)
                    item["agentic"] = {"count": len(qa.get("qa") or []), "state": "done",
                                       "engine": qa.get("engine"), "coverage": qa.get("coverage")}
                    item["_qa"] = qa.get("qa") or []
                except Exception as e:
                    item["agentic"] = {"count": 0, "state": "error", "note": str(e)[:120]}
            else:
                item["agentic"] = {"count": 0, "state": "locked", "note": "Business 专属"}

            # ③ 合规×事故
            hit = _scan_safety(gen.title + "\n" + gen.description + "\n" + gen.search_terms)
            allowed_inc = (getattr(user, "plan", "free") == "business"
                           or addon_credits(db, user, "incident") > 0)
            if hit and allowed_inc:
                try:
                    res = build_incident(db, user, platform=platform,
                                         message="Listing 文案含安全风险表述：" + hit,
                                         sku=req.sku, product_name=req.product_name, language=lang)
                    item["incident"] = {"hit": hit, "is_incident": bool(res.get("is_incident")),
                                        "incident_id": res.get("incident_id"),
                                        "days_left": res.get("days_left"), "state": "done"}
                except Exception as e:
                    item["incident"] = {"hit": hit, "state": "error", "note": str(e)[:120]}
            elif hit:
                item["incident"] = {"hit": hit, "state": "locked", "note": "需 Business 或 incident 加购"}
            else:
                item["incident"] = {"hit": None, "state": "clean"}

            # ④ 客服草稿（不发送）
            qa_list = item.get("_qa") or []
            if _plan_ok(user, "send_message"):
                drafts = []
                for q in qa_list[:3]:
                    drafts.append({"question": q.get("question") or q.get("q", ""),
                                   "reply": (q.get("answer") or q.get("a", ""))[:400]})
                if not drafts:
                    b1 = (gen.bullet_points[0].heading if gen.bullet_points else "商品信息")
                    drafts = [
                        {"question": "Is this in stock / when will it ship?",
                         "reply": "In stock. Ships within 24h; tracking uploaded after dispatch."},
                        {"question": "Is it %s?" % b1.lower(),
                         "reply": (gen.bullet_points[0].content if gen.bullet_points else gen.description)[:300]},
                        {"question": "What if it arrives damaged?",
                         "reply": "Send a photo within 14 days; we replace or refund per platform policy."},
                    ]
                item["cs"] = {"state": "draft_only", "drafts": drafts, "auto_send": False}
            else:
                item["cs"] = {"state": "locked", "drafts": [], "note": "自动回复需 Pro 及以上"}

            # 写回 payload（不真推）
            mapping = None
            try:
                payload = build_listing_payload(platform, rec, sku=req.sku or ("SKU-" + rec.id[:8]),
                                                mapping=mapping)
                item["writeback"] = {
                    "supported": bool(payload.get("supported", payload.get("endpoint"))),
                    "endpoint": payload.get("endpoint"),
                    "reason": payload.get("reason") or payload.get("note"),
                }
            except Exception as e:
                item["writeback"] = {"supported": False, "reason": str(e)[:120]}

            item["credential"] = "live_ready" if platform in connected else "not_connected"
            item.pop("_qa", None)
            items.append(item)

    stages = {
        "content": {"done": len(items), "total": len(plats) * len(langs), "state": "done" if items else "error"},
        "agentic": {"done": sum(1 for i in items if i["agentic"]["state"] == "done"),
                    "locked": sum(1 for i in items if i["agentic"]["state"] == "locked"),
                    "state": "locked" if not _plan_ok(user, "agentic_feed") else "done"},
        "incident": {"scanned": len(items),
                     "hit": sum(1 for i in items if i["incident"].get("hit")),
                     "locked": sum(1 for i in items if i["incident"]["state"] == "locked"),
                     "state": "done"},
        "cs": {"drafts": sum(len(i["cs"].get("drafts") or []) for i in items),
               "state": "locked" if not _plan_ok(user, "send_message") else "draft_only"},
        "writeback": {"ready": sum(1 for i in items if (i["writeback"] or {}).get("supported")),
                      "live_ready": sum(1 for i in items if i["credential"] == "live_ready")},
    }
    return {"plan": user.plan, "connected": sorted(connected), "items": items,
            "errors": errors, "stages": stages,
            "note": "回复与写回均为草稿/预览：真正发送或提交需凭证 + 套餐，且不会替你自动执行。"}


@router.get("/pipeline/lang-check", summary="逐语种逐平台体检：口径、字段上限、生成可用性")
def lang_check(platforms: str = "allegro", languages: str = ",".join(LANGS),
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plats = [p.strip() for p in platforms.split(",") if p.strip()][:13]
    langs = [l.strip() for l in languages.split(",") if l.strip()][:7]
    rows: List[Dict] = []
    max_pairs = 60
    for pl in plats:
        cfg = platform_config(pl)
        need = _market_langs(pl)
        for lg in langs:
            st = _lang_state(pl, lg)
            row = {"platform": pl, "language": lg, "market_languages": need,
                   "language_ok": st["ok"], "language_note": st["reason"],
                   "title_max": cfg["title_max"], "bullets": cfg["bullets"],
                   "search_terms_max": cfg["search_terms_max"], "state": "checked", "notes": []}
            if len([r for r in rows if r.get("generated")]) < max_pairs and st["ok"]:
                try:
                    ctx = build_compliance_context(db, user.id, platform=pl, product_name="Lang check")
                    gen = None
                    for _attempt in range(3):
                        try:
                            gen = expert.generate(ProductDescriptionRequest(
                                product_name="Ceramic Mug 350ml", keywords=["ceramic", "350ml"],
                                platform=pl, language=lg, tone="professional"),
                                compliance_block=ctx["prompt_block"])
                            break
                        except Exception:
                            gen = None
                    row["generated"] = True
                    row["title_len"] = len(gen.title)
                    row["bullets_count"] = len(gen.bullet_points)
                    row["desc_len"] = len(gen.description)
                    row["search_len"] = len(gen.search_terms)
                    row["title_ok"] = len(gen.title) <= cfg["title_max"]
                    row["bullets_ok"] = len(gen.bullet_points) <= cfg["bullets"]
                    row["search_ok"] = len(gen.search_terms) <= cfg["search_terms_max"]
                    row["desc_ok"] = len(gen.description) <= cfg.get("description_max", 99999)
                    row["sample_title"] = gen.title
                    if not (row["title_ok"] and row["search_ok"] and row["desc_ok"]):
                        row["notes"].append("字段超限，需按平台规则裁剪")
                except HTTPException as e:
                    row["generated"] = False
                    row["notes"].append("用量限制：%s" % (e.detail if isinstance(e.detail, str) else "额度已满"))
                except Exception as e:
                    row["generated"] = False
                    row["notes"].append("生成失败：%s" % str(e)[:100])
            elif not st["ok"]:
                row["state"] = "skip"
            rows.append(row)
    passed = sum(1 for r in rows if r.get("generated") and r.get("title_ok") and r.get("search_ok") and r.get("desc_ok"))
    return {"platforms": plats, "languages": langs, "rows": rows, "passed": passed,
            "total": len(rows),
            "note": "语言可写 ≠ 平台接受：本地市场语言为强制项，英语仅作跨境通用稿。"}
