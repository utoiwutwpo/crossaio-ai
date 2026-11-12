"""12 平台店铺授权：规格、跳转、校验、令牌换取、四语种矩阵。"""
import json
import secrets
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..connectors.auth.providers import (build_authorize_url, exchange_code,
                                         validate_shape, verify_credential,
                                         verify_many)
from ..connectors.auth.spec import (AUTH_SPECS, PLATFORM_ORDER, all_specs,
                                    get_spec)
from ..database import PlatformCredential, User, get_db
from ..ebay_service import decrypt_secret, encrypt_secret
from ..i18n import LANGS, matrix_all_locales, platform_text_all

router = APIRouter()

# confirmed = 端点已在公开文档核实；unconfirmed = 只做形状校验
CONFIRMED = [p for p in PLATFORM_ORDER if AUTH_SPECS[p]["stage"] == "confirmed"]


def _load_payload(db: Session, user: User, platform: str) -> Dict[str, str]:
    """读取并解密该用户在该平台的自助凭证；不存在返回空 dict。"""
    row = (db.query(PlatformCredential)
           .filter_by(user_id=user.id, platform=platform).first())
    if not row:
        return {}
    try:
        obj = json.loads(decrypt_secret(row.payload))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _save_payload(db: Session, user: User, platform: str, payload: Dict[str, str]) -> None:
    row = (db.query(PlatformCredential)
           .filter_by(user_id=user.id, platform=platform).first())
    cipher = encrypt_secret(json.dumps(payload, ensure_ascii=False))
    if row:
        row.payload = cipher
    else:
        db.add(PlatformCredential(user_id=user.id, platform=platform, payload=cipher))
    db.commit()


@router.get("/specs", summary="12 平台授权规格（含四语种文案）")
def list_specs():
    rows = []
    for spec in all_specs():
        platform = spec.pop("platform")
        rows.append({
            "platform": platform,
            "auth_type": spec["auth_type"],
            "stage": spec["stage"],
            "stage_text": ("端点已核实" if spec["stage"] == "confirmed"
                           else "端点待核实·仅形状校验"),
            "fields": spec["fields"],
            "docs": spec["docs"],
            "github_ref": spec["github"],
            "supports_authorize_url": bool(spec.get("authorize_url")),
            "text": platform_text_all(platform),
        })
    return {"total": len(rows), "langs": list(LANGS),
            "confirmed_count": len(CONFIRMED), "items": rows}


@router.get("/matrix", summary="12 平台 × 4 语种 × 授权状态矩阵")
def matrix(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    statuses = {}
    for platform in PLATFORM_ORDER:
        payload = _load_payload(db, user, platform)
        if not payload:
            statuses[platform] = "unconnected"
            continue
        shape = validate_shape(platform, payload)
        statuses[platform] = shape["status"]
    rows = matrix_all_locales(PLATFORM_ORDER, statuses)
    return {
        "total": len(rows),
        "langs": list(LANGS),
        "summary": {
            "unconnected": sum(1 for s in statuses.values() if s == "unconnected"),
            "connected": sum(1 for s in statuses.values()
                             if s in ("connected", "live_ok")),
        },
        "items": rows,
    }


@router.get("/{platform}/authorize-url", summary="获取 OAuth 授权跳转地址")
def authorize_url(
    platform: str,
    redirect_uri: str = Query(..., description="平台控制台登记的回调地址"),
    state: str = Query("", description="留空则自动生成 CSRF state"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if platform not in AUTH_SPECS:
        raise HTTPException(404, f"未知平台：{platform}")
    payload = _load_payload(db, user, platform)
    state = state or secrets.token_urlsafe(16)
    url = build_authorize_url(platform, state, redirect_uri, payload)
    if not url:
        raise HTTPException(
            422, f"{platform} 无已核实的授权端点，或尚未填写 Client ID")
    return {"platform": platform, "state": state, "authorize_url": url}


@router.post("/{platform}/verify", summary="校验已存凭证（可选真实令牌校验）")
async def verify(
    platform: str,
    live: bool = Query(False, description="true 时对 confirmed 平台发起真实令牌校验"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if platform not in AUTH_SPECS:
        raise HTTPException(404, f"未知平台：{platform}")
    payload = _load_payload(db, user, platform)
    if not payload:
        return {"platform": platform, "status": "unconnected", "ok": False,
                "checks": [], "missing_fields": [], "live": None,
                "reason": "尚未填写任何凭证"}
    return await verify_credential(platform, payload, live=live)


@router.post("/verify-all", summary="12 平台并发校验（一次跑完）")
async def verify_all(
    live: bool = Query(False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payloads = {p: _load_payload(db, user, p) for p in PLATFORM_ORDER}
    payloads = {p: v for p, v in payloads.items() if v}
    if not payloads:
        return {"checked": 0, "results": {},
                "note": "尚未填写任何平台凭证"}
    results = await verify_many(payloads, live=live)
    return {"checked": len(results), "uses_langs": list(LANGS),
            "results": results}


@router.post("/{platform}/exchange", summary="授权码换取令牌（写入加密存储）")
async def exchange(
    platform: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if platform not in AUTH_SPECS:
        raise HTTPException(404, f"未知平台：{platform}")
    code = str(body.get("code") or "").strip()
    redirect_uri = str(body.get("redirect_uri") or "").strip()
    if not code or not redirect_uri:
        raise HTTPException(422, "code 与 redirect_uri 均为必填")

    payload = _load_payload(db, user, platform)
    if not payload:
        raise HTTPException(422, "请先保存 Client ID / Secret 再换取令牌")

    result = await exchange_code(platform, code, redirect_uri, payload)
    if not result.get("ok"):
        return {"platform": platform, "ok": False, "reason": result.get("reason"),
                "http_status": result.get("http_status")}

    tokens = result.get("tokens") or {}
    stored = {k: v for k, v in tokens.items() if v}
    if stored:
        payload.update(stored)
        _save_payload(db, user, platform, payload)

    # 响应体绝不回传令牌本身
    return {"platform": platform, "ok": True,
            "has_access_token": bool(tokens.get("access_token")),
            "has_refresh_token": bool(tokens.get("refresh_token")),
            "expires_in": tokens.get("expires_in"),
            "stored_encrypted": bool(stored)}


@router.get("/capabilities", summary="12 平台通道能力矩阵（消息/订单/写权限）")
def capabilities():
    from ..connectors.capabilities import TIER_TEXT, matrix, summary
    from ..connectors.channels.spec import endpoint_status
    rows = matrix()
    eps = [endpoint_status(r["platform"]) for r in rows]
    return {"total": len(rows), "tiers": summary(),
            "tier_text": TIER_TEXT, "items": rows,
            "endpoints": eps,
            "verified_counts": {
                k: sum(1 for e in eps if e["verified"] == k)
                for k in ("official", "inferred", "portal")}}


@router.post("/{platform}/credentials", summary="保存平台凭证（加密入库）")
def save_credentials(
    platform: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if platform not in AUTH_SPECS:
        raise HTTPException(404, f"未知平台：{platform}")

    raw = body.get("payload") if isinstance(body.get("payload"), dict) else body
    allowed = set(AUTH_SPECS[platform]["fields"])
    payload = {}
    for k, v in raw.items():
        if k == "payload" or v is None:
            continue
        val = str(v).strip()
        if val:
            payload[k] = val

    if not payload:
        raise HTTPException(422, "没有任何有效字段")

    unknown = sorted(k for k in payload if k not in allowed)
    # 允许分步填写：未填全不拒绝保存，由校验结果告知缺什么
    _save_payload(db, user, platform, payload)
    shape = validate_shape(platform, payload)
    return {"platform": platform, "saved_fields": sorted(payload),
            "unknown_fields": unknown, "status": shape["status"],
            "missing_fields": shape["missing_fields"],
            "checks": shape["checks"]}


@router.get("/{platform}/credential", summary="查看凭证字段是否已配置（不回传明文）")
def read_credential(
    platform: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if platform not in AUTH_SPECS:
        raise HTTPException(404, f"未知平台：{platform}")
    payload = _load_payload(db, user, platform)
    fields = {}
    for f in AUTH_SPECS[platform]["fields"]:
        val = str(payload.get(f) or "")
        fields[f] = {"set": bool(val), "length": len(val)}
    status = validate_shape(platform, payload)["status"] if payload else "unconnected"
    return {"platform": platform, "status": status, "fields": fields,
            "extra_fields": sorted(k for k in payload
                                   if k not in AUTH_SPECS[platform]["fields"])}


@router.delete("/{platform}/credentials", summary="解绑平台凭证")
def delete_credentials(
    platform: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (db.query(PlatformCredential)
           .filter_by(user_id=user.id, platform=platform).first())
    if not row:
        return {"platform": platform, "ok": False, "reason": "本就没有凭证"}
    db.delete(row)
    db.commit()
    return {"platform": platform, "ok": True, "status": "unconnected"}


@router.post("/{platform}/qualification", summary="登记平台资质（如 TikTok Partner 审核通过）")
def set_qualification(platform: str, body: dict,
                      user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    """把 partner_approved 写进该平台凭证 payload；写入后消息能力才放行。"""
    import json
    from ..database import PlatformCredential
    from ..ebay_service import decrypt_secret, encrypt_secret
    p = platform.strip().lower()
    if p != "tiktok":
        raise HTTPException(422, "目前只有 tiktok 需要资质开关")
    approved = bool(body.get("approved"))
    row = (db.query(PlatformCredential)
           .filter(PlatformCredential.user_id == user.id,
                   PlatformCredential.platform == p).first())
    payload = {}
    if row:
        try:
            raw = decrypt_secret(row.payload)
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = {}
    payload["partner_approved"] = approved
    if row:
        row.payload = encrypt_secret(json.dumps(payload, ensure_ascii=False))
    else:
        row = PlatformCredential(user_id=user.id, platform=p,
                                 payload=encrypt_secret(json.dumps(payload)))
        db.add(row)
    db.commit()
    return {"platform": p, "partner_approved": approved,
            "effect": "send_message/auto_send 放行" if approved else "回退为不可发送"}


@router.post("/{platform}/probe", summary="真实连通探测（发一次真请求看 live）")
def probe_platform_endpoint(platform: str,
                            user: User = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    """不做假判定：拿到 2xx 才 live=True；未保存凭证直接 not_connected。"""
    import asyncio
    import json
    from ..connectors.live_probe import probe_platform
    from ..database import PlatformCredential

    p = platform.strip().lower()
    row = (db.query(PlatformCredential)
           .filter(PlatformCredential.user_id == user.id,
                   PlatformCredential.platform == p).first())
    payload = {}
    if row:
        try:
            from ..ebay_service import decrypt_secret
            raw = decrypt_secret(row.payload)
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = {}
    return asyncio.run(probe_platform(p, payload))
