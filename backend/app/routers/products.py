"""产品描述生成与历史（含欧洲多平台市场矩阵）"""
import json
import time
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db, User, ProductDescription
from ..schemas import (
    ProductDescriptionRequest, ProductDescriptionResponse, BulletPoint,
    MarketMatrixRequest, MarketMatrixResponse,
    GpsrCheckRequest, GpsrCheckResponse,
    AttributeValidateRequest, AttributeValidateResponse,
    ReviewInsightRequest, ReviewInsightResponse,
)
from ..auth import get_current_user
from ..experts.product_description import ProductDescriptionExpert
from ..experts.platform_registry import PLATFORMS, platform_config
from ..experts.platform_registry_i18n import localize_platform
from ..experts.gpsr import required_languages
from ..experts.gpsr import check as gpsr_check
from ..experts.listing_backfill import build_backfill_payload, submit_backfill_payload
from ..experts.attributes import required_attributes, validate_attributes, detect_category
from ..experts.review_loop import ReviewLoopExpert
from ..experts import eu_rep as eu_rep_svc
from ..routers.analytics import track_event
from ..billing import check_and_record_usage
from ..services.compliance_context import build_compliance_context

router = APIRouter()
expert = ProductDescriptionExpert()
review_expert = ReviewLoopExpert()

# ---- 游客体检限频（内存版，MVP 够用；多实例部署时换 Redis） ----
_GUEST_LIMIT = 3               # 每 IP 每天 3 次
_GUEST_HITS: dict = defaultdict(list)
_DAY = 86400


def _guest_rate_ok(ip: str) -> bool:
    now = time.time()
    hits = [t for t in _GUEST_HITS[ip] if now - t < _DAY]
    if len(hits) >= _GUEST_LIMIT:
        _GUEST_HITS[ip] = hits
        return False
    hits.append(now)
    _GUEST_HITS[ip] = hits
    return True


@router.get("/platforms", summary="支持的平台注册表（规则+默认语言）")
def list_platforms(lang: str = "zh"):
    """lang=zh（默认，无参）→ 中文注册表原值，行为逐字节不变。
    lang=en|de|fr → display/notes 用 platform_registry_i18n 覆盖；
    其他非法值 → 回退 zh，不报错。"""
    localized = lang in ("en", "de", "fr")
    return {
        key: {
            "display": (localize_platform(key, lang)["display"]
                        if localized else cfg["display"]),
            "countries": cfg["countries"],
            "language": cfg["language"],
            "title_max": cfg["title_max"],
            "bullets": cfg["bullets"],
            "search_terms_max": cfg["search_terms_max"],
            "description_max": cfg["description_max"],
            "notes": (localize_platform(key, lang)["notes"]
                      if localized else cfg["notes"]),
            "gpsr_languages": required_languages(key),
        }
        for key, cfg in PLATFORMS.items()
    }


@router.post("/gpsr/check", response_model=GpsrCheckResponse,
             summary="GPSR 合规体检（免费）：风险等级 + 法定检查清单")
def gpsr_compliance_check(
    req: GpsrCheckRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """免费只报问题不给答案（合规块付费解锁）——获客钩子。不消耗生成额度。"""
    # 自动取用户默认欧代，使合规块内嵌真实欧代（已配置时）
    rep = eu_rep_svc.get_default_rep(db, user.id)
    eu_rep_line = eu_rep_svc.render_rep_line(rep) if rep else ""
    report = gpsr_check(req.product_name, req.keywords, req.platform,
                        eu_rep_line=eu_rep_line)
    is_free = user.plan == "free"
    return GpsrCheckResponse(
        risk_level=report["risk_level"],
        platform=report["platform"],
        ce_required=report["ce_required"],
        matched_categories=report["matched_categories"],
        ce_directives=report["ce_directives"],
        required_languages=report["required_languages"],
        category_notes=report["category_notes"],
        checklist=report["checklist"],
        gpsr_block=None if is_free else report["gpsr_block"],
        asin=req.asin,
        data_source="title_keywords",
        upsell_note=("⚠️ 检测到该产品需 GPSR 合规块（含当地语言警示语）。"
                     "升级 Starter 及以上套餐解锁可粘贴的完整合规块，"
                     "缺合规块可能导致平台下架（EU 2023/988 已强制执行）。"
                     ) if (is_free and report["ce_required"]) else None,
    )


@router.post("/gpsr/check-guest", response_model=GpsrCheckResponse,
             summary="GPSR 合规体检（游客版，免注册）：每 IP 每天 3 次")
def gpsr_check_guest(req: GpsrCheckRequest, request: Request,
                     db: Session = Depends(get_db)):
    """落地页零门槛体验：不注册、不登录、不消耗额度，只报问题不给合规块。"""
    ip = request.client.host if request.client else "unknown"
    if not _guest_rate_ok(ip):
        raise HTTPException(
            status_code=429,
            detail="今日免费体检次数已用完（3 次/天）。注册免费账号可继续体检并保存历史。",
        )
    report = gpsr_check(req.product_name, req.keywords, req.platform)
    # 平台原生规则卡信息（免费钩子：证明"我们知道该平台每条合规规则"）
    from ..experts import platform_rules
    card = platform_rules.platform_rules_card(req.platform)
    # 验证闭环埋点（失败不影响业务；报告算完再记，带上风险等级）
    track_event(db, "guest_check", request, platform=req.platform,
                meta={"risk": report["risk_level"]})
    return GpsrCheckResponse(
        risk_level=report["risk_level"],
        platform=report["platform"],
        ce_required=report["ce_required"],
        matched_categories=report["matched_categories"],
        ce_directives=report["ce_directives"],
        required_languages=report["required_languages"],
        category_notes=report["category_notes"],
        checklist=report["checklist"],
        gpsr_block=None,   # 游客版固定脱敏，合规块是注册/付费后的价值
        asin=req.asin,
        data_source="title_keywords",
        upsell_note=(f"⚠️ {card['policy_name']}（当地监管：{card['authority']}）"
                     f"共 {card['rule_count']} 条平台特有规则，违规后果：{card['enforcement']}。"
                     "注册免费账号保存体检历史，升级 Starter 解锁平台当地语言的完整合规块。"
                     ) if report["ce_required"] else None,
    )


@router.post("/gpsr/native-block",
             summary="平台原生 GPSR 合规块（免费=规则卡 / 付费=完整块文本）")
def gpsr_native_block(
    req: GpsrCheckRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """「平台原生」GPSR——直接按 Allegro/eMAG/Cdiscount 等平台规则生成合规块。

    - 所有套餐：返回该平台原生规则卡（政策名/官方链接/监管机构/违规后果/平台特有规则）
      —— 展示"我们知道该平台所有合规规则"。
    - Starter 及以上：额外返回完整原生合规块文本（平台当地语言头部 + 欧代行 +
      当地语言警示语），可直接粘贴进 listing 或经 /gpsr/backfill/submit 写回。
    """
    from ..experts import platform_rules, eu_rep as eu_rep_module
    card = platform_rules.platform_rules_card(req.platform)
    is_free = user.plan == "free"
    resp: Dict = {"rules_card": card, "unlocked": not is_free}
    if not is_free:
        rep = eu_rep_svc.get_default_rep(db, user.id)
        eu_rep_line = eu_rep_svc.render_rep_line(rep) if rep else ""
        rep_dict = None
        if eu_rep_line and "," in eu_rep_line:
            parts = [p.strip() for p in eu_rep_line.split(",", 2)]
            if len(parts) == 3:
                rep_dict = {"company_name": parts[0], "address": parts[1],
                            "email": parts[2]}
        nb = platform_rules.native_compliance_block(
            req.platform, req.product_name, req.keywords, eu_rep=rep_dict)
        resp["native_block"] = nb
    else:
        resp["upsell_note"] = (
            f"检测到 {req.platform} 平台原生 GPSR 规则（{card['policy_name']}）。"
            "免费层可见全部规则卡；升级 Starter 解锁平台当地语言的完整合规块，"
            f"缺合规块风险：{card['enforcement']}")
    return resp


@router.post("/gpsr/backfill", summary="GPSR 合规块一键回填：生成待提交的平台适配 payload")
def gpsr_backfill(
    req: GpsrCheckRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """把 gpsr_block_text 生成的合规块转成各平台 API 可回填的结构化 payload。

    真实写入需对应平台凭证（SP-API/OAuth），本端点只返回适配信息，不发起外部调用。
    """
    try:
        rep = eu_rep_svc.get_default_rep(db, user.id)
        eu_rep_line = eu_rep_svc.render_rep_line(rep) if rep else ""
        return build_backfill_payload(
            req.platform, req.product_name, req.keywords, eu_rep_line=eu_rep_line)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"未知平台: {req.platform}")


@router.post("/gpsr/backfill/submit",
             summary="GPSR 合规块回填写入平台（需凭证；默认 dry-run 不联网）")
def gpsr_backfill_submit(
    req: GpsrCheckRequest,
    dry_run: bool = True,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """生成合规块并尝试写回平台 listing。

    - 未配置平台凭证（CROSSBOT_CRED_<PLATFORM>_*）→ 返回 credentials_required。
    - 已配置凭证 + dry_run=True（默认）→ 返回 ready_to_send（含待发请求）。
    - 已配置凭证 + dry_run=False → 真实写回（仅凭证就绪时由调用方显式开启）。
    """
    try:
        rep = eu_rep_svc.get_default_rep(db, user.id)
        eu_rep_line = eu_rep_svc.render_rep_line(rep) if rep else ""
        payload = build_backfill_payload(
            req.platform, req.product_name, req.keywords, eu_rep_line=eu_rep_line)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"未知平台: {req.platform}")
    return submit_backfill_payload(req.platform, payload, dry_run=dry_run)


@router.post("/descriptions/generate", response_model=ProductDescriptionResponse,
             summary="生成产品描述（多平台/多语言）")
def generate_description(
    req: ProductDescriptionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 【P0-2】合规×运营一体化：注入最近一次未通过体检结论（无审计自动降级）
    ctx = build_compliance_context(db, user.id, platform=req.platform,
                                   product_name=req.product_name)
    check_and_record_usage(db, user, "product_desc",
                           with_compliance=ctx["found"])
    track_event(db, "generate", user_id=user.id, platform=req.platform)
    try:
        result = expert.generate(req, compliance_block=ctx["prompt_block"])
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    result.platform = req.platform
    record = ProductDescription(
        user_id=user.id,
        product_name=req.product_name,
        platform=req.platform,
        language=req.language,
        tone=req.tone,
        title=result.title,
        bullet_points=[b.model_dump() for b in result.bullet_points],
        description=result.description,
        search_terms=result.search_terms,
        optimization_score=result.optimization_score,
        platform_compliant=result.platform_compliant,
        related_audit_id=ctx["audit_id"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    result.id = record.id
    from ..experts.content_provenance import build_provenance
    result.provenance = build_provenance(
        f"{result.title}\n{result.description}", platform=req.platform,
        kind="listing_description", source_id=record.id)
    if ctx["found"]:
        result.compliance_note = ctx["display_block"]["text"]
        result.related_audit_id = ctx["audit_id"]
    return result


@router.post("/descriptions/market-matrix", response_model=MarketMatrixResponse,
             summary="欧洲多平台矩阵：一次产品 → 多平台多语言批量生成")
def generate_market_matrix(
    req: MarketMatrixRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """每个平台各计 1 次用量；单平台失败不影响其余平台。"""
    # 去重保序
    platforms = list(dict.fromkeys(req.platforms))
    results: list = []
    errors: list = []

    for i, platform in enumerate(platforms):
        # 【P0-2】每平台独立取审计结论（产品名共享，平台不同结论可能不同）
        ctx = build_compliance_context(db, user.id, platform=platform,
                                       product_name=req.product_name)
        # 用量先检查再生成，避免浪费 AI 调用
        try:
            check_and_record_usage(db, user, "product_desc",
                                   with_compliance=ctx["found"])
        except HTTPException as e:
            errors.append({
                "platform": platform,
                "error": f"额度不足，剩余 {len(platforms) - i} 个平台未生成：{e.detail}",
            })
            break

        single = ProductDescriptionRequest(
            product_name=req.product_name,
            keywords=req.keywords,
            platform=platform,
            language=req.language,      # None → 平台默认语言
            tone=req.tone,
            target_audience=req.target_audience,
            unique_selling_points=req.unique_selling_points,
        )
        try:
            item = expert.generate(single, compliance_block=ctx["prompt_block"])
            item.platform = platform
            record = ProductDescription(
                user_id=user.id,
                product_name=req.product_name,
                platform=platform,
                language=item.language,
                tone=req.tone,
                title=item.title,
                bullet_points=[b.model_dump() for b in item.bullet_points],
                description=item.description,
                search_terms=item.search_terms,
                optimization_score=item.optimization_score,
                platform_compliant=item.platform_compliant,
                related_audit_id=ctx["audit_id"],
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            item.id = record.id
            from ..experts.content_provenance import build_provenance
            item.provenance = build_provenance(
                f"{item.title}\n{item.description}", platform=platform,
                kind="listing_description", source_id=record.id)
            if ctx["found"]:
                item.compliance_note = ctx["display_block"]["text"]
                item.related_audit_id = ctx["audit_id"]
            results.append(item)
        except (ValueError, KeyError) as e:
            db.rollback()
            errors.append({"platform": platform, "error": str(e)[:300]})

    return MarketMatrixResponse(
        product_name=req.product_name,
        requested=len(platforms),
        succeeded=len(results),
        results=results,
        errors=errors,
    )


@router.get("/descriptions", summary="生成历史（分页）")
def list_descriptions(
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = (
        db.query(ProductDescription)
        .filter(ProductDescription.user_id == user.id)
        .order_by(ProductDescription.created_at.desc())
    )
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "items": [
            {
                "id": r.id,
                "product_name": r.product_name,
                "platform": r.platform,
                "language": r.language,
                "title": r.title,
                "bullet_points": r.bullet_points,
                "description": r.description,
                "search_terms": r.search_terms,
                "optimization_score": r.optimization_score,
                "platform_compliant": r.platform_compliant,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }


# ---------- 文化本地化市场画像（免费营销信息 + 生成侧注入的依据） ----------

@router.get("/descriptions/cultural-profiles",
            summary="文化本地化市场画像列表（免费）：各市场买家决策要素与写法")
def list_cultural_profiles():
    from ..experts.cultural_localization import MARKET_PROFILES
    return {"profiles": [
        {"lang": k, **{f: v[f] for f in
                       ("market", "buyer_priorities", "bullet_formula", "tone",
                        "trust_signals", "avoid", "donot", "local_hint")}}
        for k, v in MARKET_PROFILES.items()
    ]}


@router.get("/descriptions/cultural-profile/{platform}",
            summary="单平台文化画像：该平台默认市场（可传 language 覆盖）")
def get_cultural_profile(platform: str, language: Optional[str] = None):
    try:
        platform_config(platform)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"未知平台: {platform}")
    from ..experts.cultural_localization import profile_for
    profile = profile_for(platform, language)
    if not profile:
        raise HTTPException(status_code=404, detail=f"{platform} 暂无该语言的市场画像")
    return {"platform": platform, **profile}


@router.get("/descriptions/{desc_id}", summary="单条详情")
def get_description(
    desc_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    r = db.get(ProductDescription, desc_id)
    if not r or r.user_id != user.id:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {
        "id": r.id,
        "title": r.title,
        "bullet_points": r.bullet_points,
        "description": r.description,
        "search_terms": r.search_terms,
        "optimization_score": r.optimization_score,
        "platform_compliant": r.platform_compliant,
    }


# ---------- 平台属性树（对齐 Marqetir「首过率」卖点） ----------

@router.get("/attributes/{platform}", summary="平台属性树：必填/推荐结构化参数")
def get_attribute_tree(platform: str, category: str = "generic"):
    try:
        platform_config(platform)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"未知平台: {platform}")
    return {
        "platform": platform,
        "category": category,
        "attributes": required_attributes(platform, category),
        "disclaimer": "属性要求为工程默认值，以卖家中心最新类目模板为准",
    }


@router.post("/attributes/validate", response_model=AttributeValidateResponse,
             summary="校验已填属性：缺失/格式错误/硬阻断 + 完整度")
def validate_platform_attributes(req: AttributeValidateRequest):
    category = (req.category or "generic").strip() or "generic"
    return validate_attributes(req.platform, req.attributes, category)


# ---------- 差评 → Listing 闭环 ----------

@router.post("/review-insights", response_model=ReviewInsightResponse,
             summary="差评反向改写：粘贴差评 → 主题定位 → 五点描述修复建议")
def review_insights(
    req: ReviewInsightRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 复用生成额度（feature=product_desc），免费版 5 条/天同池
    check_and_record_usage(db, user, "product_desc")
    return review_expert.analyze(req)


# ================= AI 商品内容 → 平台写回（第三档） =================

class _PushReq(BaseModel):
    platform: str
    sku: str = ""
    price: Optional[float] = None
    currency: str = "EUR"
    quantity: int = 10
    dry_run: bool = True


@router.post("/descriptions/{desc_id}/push", summary="生成稿写回平台（默认 dry-run，真推需凭证+映射）")
async def push_description(desc_id: str, req: _PushReq,
                           user: User = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    from ..entitlements import can_act
    from ..experts.listing_push import build_listing_payload
    from ..database import PlatformCredential
    from ..ebay_service import decrypt_secret
    from ..connectors.channels.registry import adapter_for

    rec = db.get(ProductDescription, desc_id)
    if not rec or rec.user_id != user.id:
        raise HTTPException(404, "生成稿不存在")
    platform = (req.platform or rec.platform or "").strip().lower()

    cred = (db.query(PlatformCredential)
            .filter(PlatformCredential.user_id == user.id,
                    PlatformCredential.platform == platform).first())
    payload_cred = {}
    if cred:
        try:
            raw = decrypt_secret(cred.payload)
            payload_cred = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except Exception:
            payload_cred = {}

    lm = (payload_cred.get("listing_map") or {}).get(req.sku) or {}
    if req.sku:
        from ..database import ListingMap
        row = (db.query(ListingMap)
               .filter(ListingMap.user_id == user.id,
                       ListingMap.platform == platform,
                       ListingMap.sku == req.sku).first())
        if row:
            lm = {**(lm or {}),
                  "offer_id": row.offer_id or (lm or {}).get("offer_id", ""),
                  "unit_id": row.unit_id or (lm or {}).get("unit_id", ""),
                  "ean": row.ean or (lm or {}).get("ean", ""),
                  **json.loads(row.extra_json or "{}")}
    built = build_listing_payload(platform, rec, sku=req.sku, mapping=lm,
                                  price=req.price, currency=req.currency,
                                  quantity=req.quantity)
    if not built["supported"]:
        raise HTTPException(409, detail={
            "reason_code": "platform_unsupported", "hint": built["reason"],
            "platform": platform, "action": "write_listing"})

    decision = can_act(db, user, platform, "write_listing")
    if not decision["allowed"]:
        raise HTTPException(409, detail={
            "reason_code": decision["reason_code"], "hint": decision["hint"],
            "platform": platform, "action": "write_listing"})

    if req.dry_run or not payload_cred:
        return {"ok": True, "dry_run": True, "platform": platform,
                "endpoint": built["endpoint"], "payload": built["payload"],
                "warnings": built["warnings"],
                "next": ("已生成待提交 payload；将 dry_run=false 并保存该平台凭证即可真实提交"
                         if not payload_cred else "核对 payload 后再 dry_run=false 提交")}

    adapter = adapter_for(platform, payload_cred)
    try:
        result = await adapter.push_listing(built["payload"])
    except Exception as exc:
        detail = exc.as_dict() if hasattr(exc, "as_dict") else {"reason_code": "platform_error",
                                                               "hint": str(exc)[:300]}
        raise HTTPException(409, detail=detail)
    return {"ok": True, "dry_run": False, "platform": platform, "result": result}


class _AgenticReq(BaseModel):
    platform: str = "amazon"
    description_id: str = ""
    product_name: str = ""
    keywords: List[str] = []
    language: str = "en"
    n: int = 8


@router.post("/agentic/qa", summary="2026 Agentic：成稿转买家高频问答（Business）")
def agentic_qa(req: _AgenticReq, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    from ..entitlements import can_act, ACTION_PLANS
    from ..experts.agentic_feed import build_qa

    platform = (req.platform or "amazon").strip().lower()
    decision = can_act(db, user, platform, "agentic_feed")
    if not decision["allowed"]:
        raise HTTPException(402, detail={
            "reason_code": decision["reason_code"],
            "hint": decision["hint"],
            "plan_required": sorted(ACTION_PLANS["agentic_feed"]),
            "action": "agentic_feed"})

    rec = None
    if req.description_id:
        rec = db.get(ProductDescription, req.description_id)
        if rec and rec.user_id != user.id:
            rec = None
    if rec is None:
        check_and_record_usage(db, user, "product_desc")
        result = expert.generate(ProductDescriptionRequest(
            product_name=req.product_name or "product",
            keywords=req.keywords or ["product"],
            platform=platform, language=req.language, tone="professional"))
        rec = ProductDescription(user_id=user.id, product_name=req.product_name,
                                 platform=platform, language=req.language,
                                 title=result.title,
                                 bullet_points=[b.model_dump() for b in result.bullet_points],
                                 description=result.description,
                                 search_terms=result.search_terms)
    return build_qa(rec, platform=platform, language=req.language, n=req.n)


# ---------- SKU → 平台对象映射（写回/库存的硬前置） ----------

class _MapReq(BaseModel):
    platform: str
    sku: str
    offer_id: str = ""
    unit_id: str = ""
    ean: str = ""
    extra: Dict[str, str] = {}


@router.post("/listing-map", summary="保存 SKU → 平台对象映射（offer_id/unit_id/EAN）")
def save_listing_map(req: _MapReq, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    from ..database import ListingMap
    platform = (req.platform or "").strip().lower()
    sku = (req.sku or "").strip()
    if not platform or not sku:
        raise HTTPException(422, "platform 与 sku 必填")
    row = (db.query(ListingMap)
           .filter(ListingMap.user_id == user.id, ListingMap.platform == platform,
                   ListingMap.sku == sku).first())
    if not row:
        row = ListingMap(user_id=user.id, platform=platform, sku=sku)
        db.add(row)
    row.offer_id = (req.offer_id or "").strip()
    row.unit_id = (req.unit_id or "").strip()
    row.ean = (req.ean or "").strip()
    row.extra_json = json.dumps(req.extra or {}, ensure_ascii=False)
    db.commit()
    return {"ok": True, "platform": platform, "sku": sku,
            "mapping": {"offer_id": row.offer_id, "unit_id": row.unit_id, "ean": row.ean}}


@router.get("/listing-map", summary="列出已保存的 SKU 映射")
def list_listing_map(platform: str = "", user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    from ..database import ListingMap
    q = db.query(ListingMap).filter(ListingMap.user_id == user.id)
    if platform:
        q = q.filter(ListingMap.platform == platform.strip().lower())
    rows = q.order_by(ListingMap.updated_at.desc()).limit(200).all()
    return {"items": [{"platform": r.platform, "sku": r.sku, "offer_id": r.offer_id,
                       "unit_id": r.unit_id, "ean": r.ean} for r in rows]}
