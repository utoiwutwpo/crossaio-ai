"""
验证闭环埋点 — 转化漏斗数据（对应竞品扫描报告「验证闭环」前置条件）

漏斗：landing_view → guest_check → signup → generate → upgrade
用途：用真实数据验证「GPSR 恐惧钩子」假设，决定社群投放是否加倍。
匿名性：IP 只存 SHA-256 哈希前 16 位，不存原文，不关联个人。
"""
import base64
import hashlib
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from urllib.parse import parse_qsl

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
    # 2026-11-12 P1: downloadable assets / lead capture (wired after 11-14)
    "asset_view", "asset_download", "lead_capture",
}


def ip_hash(request: Request) -> str:
    ip = request.client.host if request.client else "unknown"
    return hashlib.sha256(f"{ip}:{settings.jwt_secret}".encode()).hexdigest()[:16]


# 2026-11-07 P0-2：服务端转化事件（guest_check / generate / 体检 / signup /
# upgrade）大多不显式传 utm_*。若不兜底，渠道表里的「体检 / 注册」会全部落到
# direct，一周后就无法判断哪个渠道真的带来动作。优先级：显式参数 > URL 参数 >
# caio_attr 归因 cookie > Referer 推断。
_FB_UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign")
_FB_REF_CHANNELS = (
    ("reddit", "reddit"), ("sellerforum", "sellerforum"),
    ("facebook", "facebook"), ("instagram", "instagram"),
    ("google.", "google"), ("bing.", "bing"),
    ("linkedin.", "linkedin"), ("youtube.", "youtube"),
    ("allegro", "allegro"), ("bol.com", "bol"), ("emag", "emag"),
)


def _fallback_utm(request: Request | None) -> dict:
    """从 query / caio_attr cookie / Referer 补齐渠道，供所有 track_event 复用。"""
    if request is None:
        return {}
    try:
        q = request.query_params
        utm = {k: (q.get(k) or "").strip()[:60] for k in _FB_UTM_KEYS}
        utm = {k: v for k, v in utm.items() if v}
        if utm.get("utm_source"):
            return utm
        raw = request.cookies.get("caio_attr") or ""
        if raw:
            s = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode()
            d = {k: v[:60] for k, v in parse_qsl(s, keep_blank_values=False)
                 if k in _FB_UTM_KEYS}
            if d.get("utm_source"):
                return d
        ref = (request.headers.get("referer") or "").lower()
        for needle, name in _FB_REF_CHANNELS:
            if needle in ref:
                return {"utm_source": name, "utm_medium": "referral"}
    except Exception:
        pass
    return {}


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
    fb = _fallback_utm(request)
    try:
        db.add(AnalyticsEvent(
            event_type=event_type,
            platform=platform,
            utm_source=(utm_source or fb.get("utm_source") or "")[:100],
            utm_medium=(utm_medium or fb.get("utm_medium") or "")[:100],
            utm_campaign=(utm_campaign or fb.get("utm_campaign") or "")[:100],
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


# 与 PV 分开的漏斗/转化事件，用于按渠道判断「推广有没有带来真实动作」
_TRAFFIC_CONV_EVENTS = (
    "landing_view", "guest_check", "compliance_audit", "guest_audit",
    "signup", "generate", "gpsr_unlock_click", "pricing_view",
    "plan_view", "subscribe_click", "upgrade_cta_shown", "upgrade",
    "asset_view", "asset_download", "lead_capture",
)


@router.get("/traffic", summary="全站访问量看板数据（需管理员令牌）")
def traffic(
    days: int = 30,
    x_admin_token: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """服务端 PV 聚合：真人 / 爬虫 / 内部探针 / 独立访客 / 渠道归因 / 转化。

    2026-11-07 P0：UA 三态分类（human/bot/probe）+ UTM 归因落库，
    目的是让「哪个渠道带来多少真人与体检」可被复算，而不是只看一个总 PV。
    """
    if not settings.admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=403, detail="需要 X-Admin-Token（backend/.env 的 ADMIN_TOKEN）")
    days = max(1, min(days, 90))
    since = datetime.utcnow() - timedelta(days=days)
    rows = (db.query(AnalyticsEvent)
            .filter(AnalyticsEvent.event_type == "page_view",
                    AnalyticsEvent.created_at >= since)
            .order_by(AnalyticsEvent.created_at.desc())
            .all())
    events = (db.query(AnalyticsEvent)
              .filter(AnalyticsEvent.event_type.in_(_TRAFFIC_CONV_EVENTS),
                      AnalyticsEvent.created_at >= since)
              .all())

    by_day: dict = defaultdict(lambda: {"human": 0, "bot": 0, "probe": 0})
    by_path: dict = defaultdict(lambda: {"human": 0, "bot": 0, "probe": 0})
    by_ref: dict = defaultdict(int)
    by_channel: dict = defaultdict(lambda: {"pv": 0, "vid": set()})
    ev_by_channel: dict = defaultdict(Counter)
    ev_total: Counter = Counter()
    human_ips = set()
    human_pv = bot_pv = probe_pv = 0
    recent = []
    for r in rows:
        meta = r.meta or {}
        kind = meta.get("ua_kind")
        if kind not in ("human", "bot", "probe"):
            # 兼容部署前的旧事件：只有 is_bot 字段
            kind = "bot" if meta.get("is_bot") else "human"
        day = r.created_at.strftime("%Y-%m-%d") if r.created_at else "?"
        path = meta.get("path") or "?"
        by_day[day][kind] += 1
        by_path[path][kind] += 1
        if kind == "human":
            human_pv += 1
            # 匿名访客 cookie 优先于 IP：同一出口 IP 下的多个真实用户能分开计数
            vid = meta.get("vid") or r.ip_hash or ""
            if vid:
                human_ips.add(vid)
            channel = ((r.utm_source or "").strip()
                       or (meta.get("utm") or {}).get("utm_source", "")
                       or "direct")
            by_channel[channel]["pv"] += 1
            by_channel[channel]["vid"].add(vid)
            ref = (meta.get("ref") or "").strip()
            if ref:
                by_ref[ref] += 1
            if len(recent) < 30:
                recent.append({
                    "at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
                    "path": path,
                    "channel": channel,
                    "ip": vid[:8],
                    "ua": (meta.get("ua") or "")[:120],
                })
        elif kind == "bot":
            bot_pv += 1
        else:
            probe_pv += 1

    for e in events:
        channel = (e.utm_source or "").strip() or "direct"
        ev_by_channel[channel][e.event_type] += 1
        ev_total[e.event_type] += 1

    channels = []
    for channel in sorted(set(by_channel) | set(ev_by_channel)):
        c = by_channel.get(channel, {"pv": 0, "vid": set()})
        ev = ev_by_channel.get(channel, Counter())
        channels.append({
            "channel": channel,
            "human_pv": c["pv"],
            "unique": len(c["vid"]),
            "landing": ev.get("landing_view", 0),
            "checks": (ev.get("guest_check", 0) + ev.get("compliance_audit", 0)
                       + ev.get("guest_audit", 0)),
            "signups": ev.get("signup", 0),
            "generates": ev.get("generate", 0),
            "upgrades": ev.get("upgrade", 0) + ev.get("subscribe_click", 0),
        })
    channels.sort(key=lambda x: (-x["human_pv"], -x["unique"]))

    return {
        "days": days,
        "total_pv": len(rows),
        "human_pv": human_pv,
        "bot_pv": bot_pv,
        "probe_pv": probe_pv,
        "unique_human_visitors": len(human_ips),
        "by_day": [{"date": d, **v} for d, v in sorted(by_day.items())],
        "top_pages": [{"path": p, **v} for p, v in
                      sorted(by_path.items(),
                             key=lambda kv: -(kv[1]["human"] + kv[1]["bot"] + kv[1]["probe"]))[:20]],
        "top_referers": [{"ref": k, "count": v} for k, v in
                         sorted(by_ref.items(), key=lambda kv: -kv[1])[:15]],
        "channels": channels,
        "conversion_events": dict(ev_total),
        "recent_human": recent,
        "ga4_enabled": bool((settings.ga4_measurement_id or "").strip()),
        "note": "2026-11-07 口径：UA 三态分类（human/bot/probe），probe=健康检查、自建验证、"
                "无浏览器指纹请求，不计入真人；utm_* 由 URL 参数或 caio_attr cookie 归因，"
                "无 UTM 时按 Referer 推断渠道；独立访客用匿名 caio_vid cookie；"
                "看板页 /traffic 自身不计入。转化事件按 utm_source 归到渠道。",
    }
