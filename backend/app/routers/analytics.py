"""
验证闭环埋点 — 转化漏斗数据（对应竞品扫描报告「验证闭环」前置条件）

漏斗：landing_view → guest_check → signup → generate → upgrade
用途：用真实数据验证「GPSR 恐惧钩子」假设，决定社群投放是否加倍。
匿名性：IP 只存 SHA-256 哈希前 16 位，不存原文，不关联个人。
"""
import hashlib
from datetime import datetime, timedelta
from collections import Counter, defaultdict

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db, AnalyticsEvent, User
from ..schemas import AnalyticsTrackRequest

router = APIRouter()

VALID_EVENTS = {
    "landing_view", "guest_check", "signup", "generate",
    "upgrade", "gpsr_unlock_click", "pricing_view",
    "compliance_audit", "guest_audit", "connector_import",
    # 【P0-3】订阅漏斗：浏览定价页 → 点击订阅/选择 → 升级引导 CTA 展示
    "plan_view", "subscribe_click", "upgrade_cta_shown",
    # 服务端全站 PV（main.py 中间件写入，覆盖所有 200 HTML 页面）
    "page_view",
}


def ip_hash(request: Request) -> str:
    ip = request.client.host if request.client else "unknown"
    return hashlib.sha256(f"{ip}:{settings.jwt_secret}".encode()).hexdigest()[:16]


def track_event(
    db: Session,
    event_type: str,
    request: Request | None = None,
    user_id: str | None = None,
    platform: str | None = None,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    meta: dict | None = None,
) -> None:
    """内部埋点入口（业务路由里直接调用，失败不影响主流程）。"""
    if event_type not in VALID_EVENTS:
        return
    try:
        db.add(AnalyticsEvent(
            event_type=event_type,
            platform=platform,
            utm_source=(utm_source or "")[:100],
            utm_medium=(utm_medium or "")[:100],
            utm_campaign=(utm_campaign or "")[:100],
            ip_hash=ip_hash(request) if request else "",
            user_id=user_id,
            meta=meta or {},
        ))
        db.commit()
    except Exception:  # 埋点绝不阻断业务
        db.rollback()


@router.post("/track", summary="前端埋点上报（公开）")
def track(body: AnalyticsTrackRequest, request: Request, db: Session = Depends(get_db)):
    if body.event_type not in VALID_EVENTS:
        raise HTTPException(status_code=422, detail=f"未知事件，可用：{sorted(VALID_EVENTS)}")
    track_event(db, body.event_type, request, platform=body.platform,
                utm_source=body.utm_source, utm_medium=body.utm_medium,
                utm_campaign=body.utm_campaign, meta=body.meta)
    return {"ok": True}


@router.get("/summary", summary="转化漏斗统计（需管理员令牌）")
def summary(
    days: int = 30,
    x_admin_token: str = Header(default=""),
    db: Session = Depends(get_db),
):
    if not settings.admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=403, detail="需要 X-Admin-Token（backend/.env 的 ADMIN_TOKEN）")

    since = datetime.utcnow() - timedelta(days=days)
    rows = db.query(AnalyticsEvent).filter(AnalyticsEvent.created_at >= since).all()

    by_event = Counter(r.event_type for r in rows)
    by_source: dict = defaultdict(Counter)
    for r in rows:
        src = r.utm_source or "direct"
        by_source[src][r.event_type] += 1

    # 漏斗：view → guest_check → signup → generate → upgrade
    funnel_steps = ["landing_view", "guest_check", "signup", "generate", "upgrade"]
    funnel = {step: by_event.get(step, 0) for step in funnel_steps}

    # 关键转化率（防除零）
    def rate(num, den):
        return round(num / den * 100, 1) if den else None

    return {
        "days": days,
        "funnel": funnel,
        "conversion": {
            "view_to_check": rate(funnel["guest_check"], funnel["landing_view"]),
            "check_to_signup": rate(funnel["signup"], funnel["guest_check"]),
            "signup_to_generate": rate(funnel["generate"], funnel["signup"]),
            "generate_to_upgrade": rate(funnel["upgrade"], funnel["generate"]),
        },
        "by_source": {src: dict(cnt) for src, cnt in by_source.items()},
        "total_events": len(rows),
        "note": "判读基准（COMMUNITY_PLAYBOOK）：check_to_signup >25% 加倍投放；"
                "高风险报告占比 >40% 说明社群选对；generate_to_upgrade >8% 说明付费钩子成立。",
    }


@router.get("/traffic", summary="全站访问量看板数据（需管理员令牌）")
def traffic(
    days: int = 30,
    x_admin_token: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """服务端 PV 聚合：真人 / 爬虫 / 独立访客 / 按天 / 热门页面 / 来源。"""
    if not settings.admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=403, detail="需要 X-Admin-Token（backend/.env 的 ADMIN_TOKEN）")
    days = max(1, min(days, 90))
    since = datetime.utcnow() - timedelta(days=days)
    rows = (db.query(AnalyticsEvent)
            .filter(AnalyticsEvent.event_type == "page_view",
                    AnalyticsEvent.created_at >= since)
            .order_by(AnalyticsEvent.created_at.desc())
            .all())

    by_day: dict = defaultdict(lambda: {"human": 0, "bot": 0})
    by_path: dict = defaultdict(lambda: {"human": 0, "bot": 0})
    by_ref: dict = defaultdict(int)
    human_ips = set()
    human_pv = bot_pv = 0
    recent = []
    for r in rows:
        meta = r.meta or {}
        kind = "bot" if meta.get("is_bot") else "human"
        day = r.created_at.strftime("%Y-%m-%d") if r.created_at else "?"
        path = meta.get("path") or "?"
        by_day[day][kind] += 1
        by_path[path][kind] += 1
        if kind == "human":
            human_pv += 1
            if r.ip_hash:
                human_ips.add(r.ip_hash)
            ref = (r.utm_source or "").strip()
            if ref:
                by_ref[ref] += 1
            if len(recent) < 30:
                recent.append({
                    "at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
                    "path": path,
                    "ip": (r.ip_hash or "")[:8],
                    "ua": (meta.get("ua") or "")[:120],
                })
        else:
            bot_pv += 1

    return {
        "days": days,
        "total_pv": len(rows),
        "human_pv": human_pv,
        "bot_pv": bot_pv,
        "unique_human_visitors": len(human_ips),
        "by_day": [{"date": d, **v} for d, v in sorted(by_day.items())],
        "top_pages": [{"path": p, **v} for p, v in
                      sorted(by_path.items(), key=lambda kv: -(kv[1]["human"] + kv[1]["bot"]))[:20]],
        "top_referers": [{"ref": k, "count": v} for k, v in
                         sorted(by_ref.items(), key=lambda kv: -kv[1])[:15]],
        "recent_human": recent,
        "ga4_enabled": bool((settings.ga4_measurement_id or "").strip()),
        "note": "page_view 由服务端中间件记录，覆盖全部 200 HTML 页面；is_bot 按 User-Agent 判定，"
                "看板页面 /traffic 自身不计入。",
    }
