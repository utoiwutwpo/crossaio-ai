"""一键合规体检路由（GPSR 付费闭环）。

- POST /api/v1/compliance/audit        登录体检：免费层=摘要（只报问题不给答案），
                                        Starter+=完整报告（欧代标注/技术文件清单/警示语包）
- POST /api/v1/compliance/audit-guest  游客体检：每 IP 每天 3 次，固定摘要版
- GET  /api/v1/compliance/audits       体检历史（登录用户）
- GET  /api/v1/compliance/credentials  平台凭证接入状态（部署环境级，工作台横幅）
"""
import time
from collections import defaultdict
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import (get_db, ComplianceAudit, User, eBayConnection,
                        PlatformCredential)
from ..auth import get_current_user
from ..experts import compliance_audit
from ..experts import eu_rep as eu_rep_svc
from ..experts.platform_registry import PLATFORMS
from ..routers.analytics import track_event

router = APIRouter()

# ---- 游客限频（与 products.gpsr/check-guest 同款内存实现） ----
_GUEST_LIMIT = 3
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


class AuditRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    keywords: List[str] = Field(min_length=1, max_length=20)
    platform: str = "amazon"


def _do_audit(db: Session, platform: str, product_name: str, keywords: List[str],
              user: Optional[User]) -> dict:
    """共用的体检执行：登录用户自动嵌入默认欧代；游客不带欧代。"""
    if platform not in PLATFORMS:
        raise HTTPException(status_code=404, detail=f"未知平台: {platform}")
    rep = eu_rep_svc.get_default_rep(db, user.id) if user else None
    rep_line = eu_rep_svc.render_rep_line(rep) if rep else ""
    is_free = (user is None) or (user.plan == "free")
    report = compliance_audit.run_audit(
        platform, product_name, keywords, eu_rep=rep, rep_line=rep_line,
        full=not is_free,
    )
    report["unlocked"] = not is_free
    if is_free:
        report["upsell_note"] = (
            "⚠️ 免费版只报问题不给答案。升级 Starter 解锁：欧代标注行（含三处标注"
            "位置指引）+ 技术文件清单（8 项，10 年存档）+ 当地语言警示语包 + "
            "平台原生合规块——平台前置校验拦截前把合规做完。")
    if user:
        db.add(ComplianceAudit(
            user_id=user.id, platform=platform, product_name=product_name[:255],
            risk_level=report["risk_level"],
            compliance_score=report["compliance_score"],
            critical_gap_count=report["critical_gap_count"],
            report=report,
        ))
        db.commit()
    return report


@router.post("/audit", summary="一键合规体检（登录）：免费=摘要 / Starter+=完整交付物")
def audit(req: AuditRequest, user: User = Depends(get_current_user),
          db: Session = Depends(get_db)):
    report = _do_audit(db, req.platform, req.product_name, req.keywords, user)
    track_event(db, "compliance_audit", user_id=user.id, platform=req.platform,
                meta={"risk": report["risk_level"], "score": report["compliance_score"]})
    return report


@router.post("/audit-guest", summary="一键合规体检（游客版，免注册）：每 IP 每天 3 次")
def audit_guest(req: AuditRequest, request: Request,
                db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    if not _guest_rate_ok(ip):
        raise HTTPException(
            status_code=429,
            detail="今日免费体检次数已用完（3 次/天）。注册免费账号可继续体检并保存历史。")
    report = _do_audit(db, req.platform, req.product_name, req.keywords, None)
    track_event(db, "guest_audit", request, platform=req.platform,
                meta={"risk": report["risk_level"]})
    return report


@router.get("/audits", summary="体检历史（最近 30 次）")
def audit_history(user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    rows = (db.query(ComplianceAudit)
            .filter(ComplianceAudit.user_id == user.id)
            .order_by(ComplianceAudit.created_at.desc())
            .limit(30).all())
    return {"items": [
        {"id": r.id, "platform": r.platform, "product_name": r.product_name,
         "risk_level": r.risk_level, "compliance_score": r.compliance_score,
         "critical_gap_count": r.critical_gap_count,
         "created_at": r.created_at}
        for r in rows
    ]}


# ---- 平台凭证接入状态（部署环境级，工作台横幅数据源） ----

_AMAZON_ENV_KEYS = [
    ("CLIENT_ID", "LWA 开发者应用 Client ID"),
    ("CLIENT_SECRET", "LWA 开发者应用 Client Secret"),
    ("REFRESH_TOKEN", "卖家授权后换取的 Refresh Token"),
]


@router.get("/credentials", summary="平台凭证接入状态（部署环境级，工作台提示接入）")
def credentials_status(user: User = Depends(get_current_user),
                       db: Session = Depends(get_db),
                       lang: str = "zh"):
    """诚实汇报部署环境的平台凭证配置状态（不回显任何密钥值）。

    - Amazon SP-API：环境变量 CROSSBOT_CRED_AMAZON_*（命名约定见 listing_backfill）
      就绪后可解锁：合规块真实写回 Amazon Listing（回填适配层 dry_run=False）
    - eBay OAuth：两层 —— 应用级（settings.ebay_client_id/secret）+
      用户级（当前卖家是否已完成 OAuth 授权，eBayConnection 表）
      就绪后可解锁：eBay 消息实时同步 + AI 回复直发买家

    lang 支持 zh（默认）/ en / de / fr：平台 label、接入指南、unlocks
    按语言返回（数据源 PLATFORM_CRED_I18N）。
    """
    import os

    from ..experts.platform_credentials import _tr

    tr = (lambda p: _tr(p, lang)) if lang in ("en", "de", "fr") else (lambda p: None)
    _AMAZON_ENV_KEYS_TR = {
        "en": [("CLIENT_ID", "LWA developer app Client ID"),
               ("CLIENT_SECRET", "LWA developer app Client Secret"),
               ("REFRESH_TOKEN", "Refresh Token exchanged after seller authorisation")],
        "de": [("CLIENT_ID", "Client ID der LWA-Entwickler-App"),
               ("CLIENT_SECRET", "Client Secret der LWA-Entwickler-App"),
               ("REFRESH_TOKEN", "Refresh Token nach der Verkäufer-Autorisierung eingetauscht")],
        "fr": [("CLIENT_ID", "Client ID de l'application développeur LWA"),
               ("CLIENT_SECRET", "Client Secret de l'application développeur LWA"),
               ("REFRESH_TOKEN", "Refresh Token obtenu après autorisation du vendeur")],
    }
    amz_keys = _AMAZON_ENV_KEYS_TR.get(lang, _AMAZON_ENV_KEYS) if lang in ("en", "de", "fr") else _AMAZON_ENV_KEYS
    _STATUS_I18N = {
        "amazon_sp_api": {
            "en": {"unlocks": "Write GPSR compliance blocks back to real Amazon Listings (backfill dry_run=False)",
                   "docs": "SP-API developer account + compliance read/write permission (LWA + AWS SigV4)"},
            "de": {"unlocks": "Compliance-Blöcke in echte Amazon-Listings zurückschreiben (Backfill dry_run=False)",
                   "docs": "SP-API-Entwicklerkonto + Compliance-Lese-/Schreibrecht (LWA + AWS SigV4)"},
            "fr": {"unlocks": "Écriture réelle des blocs de conformité sur les listings Amazon (backfill dry_run=False)",
                   "docs": "Compte développeur SP-API + droit de lecture/écriture conformité (LWA + AWS SigV4)"},
        },
        "ebay_oauth": {
            "en": {"unlocks": "Real-time eBay buyer message sync + direct AI reply sending",
                   "docs": "eBay Developer Program → OAuth (user token, stored encrypted)"},
            "de": {"unlocks": "Echtzeit-Sync der eBay-Käufernachrichten + direkter Versand von KI-Antworten",
                   "docs": "eBay Developer Program → OAuth (User-Token, verschlüsselt gespeichert)"},
            "fr": {"unlocks": "Synchronisation en temps réel des messages acheteurs eBay + envoi direct des réponses IA",
                   "docs": "eBay Developer Program → OAuth (user token, stocké chiffré)"},
        },
    }
    si = _STATUS_I18N.get(lang, {})

    amz_missing = [k for k, _ in amz_keys
                   if not os.environ.get("CROSSBOT_CRED_AMAZON_" + k)]

    from ..config import settings
    ebay_app_ok = bool(settings.ebay_client_id and settings.ebay_client_secret)
    ebay_conn = (db.query(eBayConnection)
                 .filter(eBayConnection.user_id == user.id).first())
    ebay_user_ok = ebay_conn is not None

    # 13 平台自助凭证（PlatformCredential 表，AES-256 加密封存）
    from ..experts.platform_credentials import PLATFORM_CRED_REGISTRY, cred_guide
    saved_platforms = {r.platform: r for r in
                       db.query(PlatformCredential)
                       .filter(PlatformCredential.user_id == user.id).all()}

    amz_ready = not amz_missing
    platforms = {}
    for p, cfg in PLATFORM_CRED_REGISTRY.items():
        t = tr(p)
        label = t["label"] if t else cfg["label"]
        unlocks = t["unlocks"] if t else cfg["unlocks"]
        if cfg.get("oauth"):
            platforms[p] = {
                "label": label, "oauth": True,
                "connected": ebay_user_ok,
                "ready": ebay_app_ok and ebay_user_ok,
                "app_configured": ebay_app_ok,
                "connect_url": "/api/v1/ebay/auth-url",
                "guide": cred_guide(p, lang),
                "unlocks": unlocks,
            }
            continue
        row = saved_platforms.get(p)
        env_ready = (p in ("amazon", "amazon_us")) and amz_ready
        platforms[p] = {
            "label": label, "oauth": False,
            "connected": row is not None,
            "ready": bool(row) or env_ready,
            "source": ("self" if row else ("env" if env_ready else None)),
            "connected_at": row.updated_at.isoformat() if row else None,
            "guide": cred_guide(p, lang),
            "unlocks": unlocks,
        }

    return {
        "amazon_sp_api": {
            "ready": amz_ready or platforms["amazon"]["connected"],
            "missing": amz_missing,
            "required": [{"key": k, "desc": d, "env": f"CROSSBOT_CRED_AMAZON_{k}"}
                         for k, d in amz_keys],
            "env_prefix": "CROSSBOT_CRED_AMAZON_",
            "unlocks": si["amazon_sp_api"]["unlocks"] if si else "合规块真实写回 Amazon Listing（回填适配层 dry_run=False）",
            "docs": si["amazon_sp_api"]["docs"] if si else "SP-API 开发者账号 + 合规读写权限（LWA + AWS SigV4）",
        },
        "ebay_oauth": {
            "ready": ebay_app_ok and ebay_user_ok,
            "app_configured": ebay_app_ok,
            "user_connected": ebay_user_ok,
            "connect_url": "/api/v1/ebay/auth-url",
            "unlocks": si["ebay_oauth"]["unlocks"] if si else "eBay 买家消息实时同步 + AI 回复直发",
            "docs": si["ebay_oauth"]["docs"] if si else "eBay Developer Program → OAuth（user token，加密封存）",
        },
        "platforms": platforms,
        "all_ready": all(p["ready"] for p in platforms.values()),
    }


# ---- 商家自助凭证（粘贴 → AES-256 加密封存，13 平台通用） ----

class PlatformCredIn(BaseModel):
    """自助接入表单：字段名随平台注册表动态校验。"""
    credentials: dict = Field(..., description="如 {client_id: ..., client_secret: ...}")


@router.post("/credentials/{platform}",
             summary="商家自助接入：粘贴平台凭证（AES 加密封存）")
def save_platform_creds(platform: str, body: PlatformCredIn,
                        user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    from ..experts.platform_credentials import PLATFORM_CRED_REGISTRY, cred_guide
    from ..ebay_service import encrypt_secret
    import json as _json

    cfg = PLATFORM_CRED_REGISTRY.get(platform)
    if not cfg:
        raise HTTPException(404, f"未知平台：{platform}（支持 13 平台，见 GET /credentials）")
    if cfg.get("oauth"):
        raise HTTPException(400, "eBay 走 OAuth 授权流程，请用 GET /api/v1/ebay/auth-url")

    # 动态校验：注册表要求的所有字段必须提供且非空
    missing = [k for k, _, _, _ in cfg["fields"]
               if not str(body.credentials.get(k, "")).strip()]
    if missing:
        raise HTTPException(422, f"缺少必填字段：{', '.join(missing)}")

    # 订阅配额：平台接入数量按套餐自动识别（free/starter=1，pro=3，business=无限）
    from ..billing import plan_config
    from .automation import connected_platforms
    quota = plan_config(user.plan)["platforms"]
    connected = connected_platforms(db, user.id)
    if platform not in connected and quota is not None and len(connected) >= quota:
        raise HTTPException(
            402, f"当前套餐（{user.plan}）最多接入 {quota} 个平台"
                 f"（已接入 {len(connected)} 个）。升级套餐解锁更多平台接入。")

    # 只保留注册表字段（多余键丢弃），整包 JSON 加密
    payload = {k: str(body.credentials.get(k, "")).strip()
               for k, _, _, _ in cfg["fields"]}
    row = (db.query(PlatformCredential)
           .filter(PlatformCredential.user_id == user.id,
                   PlatformCredential.platform == platform).first())
    enc = encrypt_secret(_json.dumps(payload, ensure_ascii=False))
    if row:
        row.payload = enc
    else:
        row = PlatformCredential(user_id=user.id, platform=platform, payload=enc)
        db.add(row)
    db.commit()
    return {"ok": True, "platform": platform, "label": cfg["label"],
            "message": f"{cfg['label']} 凭证已加密保存（AES-256）。"
                       f"平台 API 联调生效时间以该平台审核为准。",
            "unlocks": cfg["unlocks"]}


@router.delete("/credentials/{platform}",
               summary="断开平台自助凭证（删除加密记录）")
def delete_platform_creds(platform: str,
                          user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    row = (db.query(PlatformCredential)
           .filter(PlatformCredential.user_id == user.id,
                   PlatformCredential.platform == platform).first())
    if not row:
        raise HTTPException(404, f"平台 {platform} 没有自助凭证记录")
    db.delete(row)
    db.commit()
    return {"ok": True, "platform": platform, "message": "已断开并删除加密凭证"}


# ===== eBay 应用级配置（Client ID / Secret）=====

class EbayAppConfigIn(BaseModel):
    client_id: str = Field(..., description="eBay Developer Client ID")
    client_secret: str = Field(..., description="eBay Developer Client Secret")


@router.get("/ebay/app-config", summary="查看 eBay 应用配置状态（不回显明文）")
def get_ebay_app_config(user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    from ..database import SystemSetting
    from ..ebay_service import decrypt_secret
    row = db.query(SystemSetting).filter_by(key="ebay_client_id").first()
    has_id = bool(row and row.value)
    row2 = db.query(SystemSetting).filter_by(key="ebay_client_secret").first()
    has_secret = bool(row2 and row2.value)
    # 回显前 4 位 + 后 4 位（脱敏）
    masked_id = ""
    if has_id:
        try:
            raw = decrypt_secret(row.value)
            masked_id = raw[:4] + "****" + raw[-4:] if len(raw) > 8 else "****"
        except Exception:
            masked_id = "****"
    return {
        "has_client_id": has_id,
        "has_client_secret": has_secret,
        "masked_client_id": masked_id,
    }


@router.post("/ebay/app-config", summary="保存 eBay 应用配置（Client ID / Secret）")
def save_ebay_app_config(body: EbayAppConfigIn,
                         user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    """保存 eBay Developer 应用凭证，加密存库，之后卖家可直接点授权。"""
    from ..database import SystemSetting
    from ..ebay_service import encrypt_secret

    for key, val in [("ebay_client_id", body.client_id.strip()),
                     ("ebay_client_secret", body.client_secret.strip())]:
        if not val:
            raise HTTPException(400, f"{key} 不能为空")
        row = db.query(SystemSetting).filter_by(key=key).first()
        enc = encrypt_secret(val)
        if row:
            row.value = enc
        else:
            db.add(SystemSetting(key=key, value=enc))
    db.commit()
    return {"ok": True, "message": "eBay 应用凭证已加密保存，现在可以点「去授权 eBay」了"}
