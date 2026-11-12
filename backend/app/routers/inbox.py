"""跨平台统一收件箱 — 把 12 个平台的买家会话聚合到一处。

设计边界（诚实声明）：
- 本路由提供"统一视图 + 合规客服回复"的真实能力：所有平台的会话在一处
  展示，出站回复统一经过组合工作流（GPSR + AI Act Art.50 + 平台语言）。
- 各平台的"实时消息同步连接器"（调用平台 API 拉取新消息）为独立模块，
  未实现；会话可通过手动导入或 /seed-demo 演示数据创建。
- 【P0-1】Amazon 连接器：凭证存储/状态为真实能力；SP-API 真实同步待
  Amazon Developer Central 审核（【待确认】），审核前不发起任何 SP-API 请求。
"""
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db, User, InboxConversation, InboxMessage, PlatformCredential
from ..schemas import CustomerServiceRequest
from ..auth import get_current_user
from ..experts.customer_service import CustomerServiceExpert
from ..experts.platform_registry import PLATFORMS, platform_config

router = APIRouter()
expert = CustomerServiceExpert()


def _parse_context(c: InboxConversation) -> dict:
    """解析会话上下文 JSON；空值/损坏返回 {}（不抛错）。"""
    raw = getattr(c, "context_json", "") or ""
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except (ValueError, TypeError):
        return {}


def _conv_to_dict(c: InboxConversation) -> dict:
    return {
        "id": c.id, "platform": c.platform, "buyer_id": c.buyer_id,
        "subject": c.subject, "status": c.status,
        "unread_count": c.unread_count,
        "last_message_at": c.last_message_at,
        "context": _parse_context(c),
        "created_at": c.created_at,
    }


def _msg_to_dict(m: InboxMessage) -> dict:
    return {
        "id": m.id, "direction": m.direction, "body": m.body,
        "intent": m.intent, "sentiment": m.sentiment,
        "needs_escalation": m.needs_escalation,
        "gpsr_incident": m.gpsr_incident,
        "ai_act_disclosure": m.ai_act_disclosure,
        "created_at": m.created_at,
    }


@router.get("/conversations", summary="统一收件箱：列出全部平台会话（可按平台过滤）")
def list_conversations(
    platform: Optional[str] = Query(None, description="按平台过滤；不传则跨全部平台"),
    status: Optional[str] = Query(None),
    page: int = 1, page_size: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(InboxConversation).filter(InboxConversation.user_id == user.id)
    if platform:
        if platform not in PLATFORMS:
            raise HTTPException(status_code=404, detail=f"未知平台: {platform}")
        q = q.filter(InboxConversation.platform == platform)
    if status:
        q = q.filter(InboxConversation.status == status)
    total = q.count()
    rows = (q.order_by(InboxConversation.last_message_at.desc().nullslast(),
                       InboxConversation.created_at.desc())
               .offset((page - 1) * page_size).limit(page_size).all())
    # 平台分布统计（前端筛选 chips 用）
    dist = (db.query(InboxConversation.platform,
                     func.count(InboxConversation.id))
            .filter(InboxConversation.user_id == user.id)
            .group_by(InboxConversation.platform).all())
    return {
        "total": total, "page": page,
        "platform_distribution": {p: n for p, n in dist},
        "items": [_conv_to_dict(r) for r in rows],
    }


@router.get("/conversations/{conv_id}", summary="会话详情（含消息流）")
def get_conversation(conv_id: str, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    c = db.get(InboxConversation, conv_id)
    if not c or c.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    msgs = (db.query(InboxMessage)
            .filter(InboxMessage.conversation_id == conv_id)
            .order_by(InboxMessage.created_at.asc()).all())
    # 进入即标记已读
    if c.unread_count:
        c.unread_count = 0
        db.commit()
    return {"conversation": _conv_to_dict(c), "messages": [_msg_to_dict(m) for m in msgs]}


@router.post("/conversations", summary="手动导入/新建一条会话（含首条买家消息）")
def create_conversation(
    body: dict, user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    platform = body.get("platform", "amazon")
    if platform not in PLATFORMS:
        raise HTTPException(status_code=404, detail=f"未知平台: {platform}")
    first = (body.get("first_message") or "").strip()
    ctx = body.get("context") or {}
    if not isinstance(ctx, dict):
        raise HTTPException(status_code=422, detail="context 必须是对象（如 order_id/asin/sku）")
    c = InboxConversation(
        user_id=user.id, platform=platform,
        external_thread_id=body.get("external_thread_id", ""),
        buyer_id=body.get("buyer_id", ""),
        subject=body.get("subject", "") or (first[:60] if first else "(无主题)"),
        context_json=json.dumps(ctx, ensure_ascii=False) if ctx else "",
        last_message_at=datetime.utcnow(),
    )
    db.add(c); db.commit(); db.refresh(c)
    if first:
        db.add(InboxMessage(conversation_id=c.id, direction="incoming",
                            body=first, created_at=datetime.utcnow()))
        db.commit()
        # 【P0】新买家消息 → 事件触发（drain 时按订阅门控执行 AI 自动回复）
        from ..automation_events import enqueue
        enqueue(user.id, "new_buyer_message", {"conversation_id": c.id})
    return _conv_to_dict(c)


@router.post("/conversations/{conv_id}/reply",
             summary="在会话中回复买家（出站消息经组合工作流处理）")
def reply_conversation(
    conv_id: str, body: dict, user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """出站回复：用组合工作流（GPSR + AI Act Art.50 + 平台语言）处理后写回。

    返回 customer_service 的完整响应（含 ai_act_disclosure / gpsr_incident）。
    """
    c = db.get(InboxConversation, conv_id)
    if not c or c.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    message = (body.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=422, detail="message 不能为空")

    req = CustomerServiceRequest(
        customer_message=message,
        platform=c.platform,
        language=body.get("language"),
    )
    result = expert.handle(req)

    # 买家原消息也入流（若此前未入），再写入出站回复
    db.add(InboxMessage(conversation_id=c.id, direction="incoming",
                        body=message, intent=result.intent,
                        sentiment=result.sentiment,
                        needs_escalation=result.needs_escalation,
                        gpsr_incident=result.gpsr_incident,
                        created_at=datetime.utcnow()))
    db.add(InboxMessage(
        conversation_id=c.id, direction="outgoing", body=result.reply,
        intent=result.intent, sentiment=result.sentiment,
        needs_escalation=result.needs_escalation,
        gpsr_incident=result.gpsr_incident,
        ai_act_disclosure=result.ai_act_disclosure or "",
        created_at=datetime.utcnow()))
    c.last_message_at = datetime.utcnow()
    c.status = "pending" if result.needs_escalation else c.status
    db.commit()
    return result.model_dump()


@router.get("/connectors", summary="平台连接器状态（eBay 已接入；Allegro/OTTO/Kaufland 导入骨架）")
def connectors(user: User = Depends(get_current_user)):
    """连接器诚实状态：eBay=api（OAuth 全流程已接）；欧洲本地三平台=manual
    （手动导入骨架，凭证就绪后升级 API 同步）。"""
    from ..experts.inbox_connectors import list_connectors
    return {
        "ebay": {"sync_mode": "api", "credentials_ready": True,
                 "note": "OAuth 全流程已接入（自动拉取消息）"},
        "connectors": list_connectors(),
    }


@router.get("/connectors/amazon/status",
            summary="Amazon 连接器三态状态（纯本地推导，不发起外部调用）")
def amazon_connector_status(user: User = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    """三态：unconnected / pending / connected。

    - unconnected：无任何 Amazon 凭证（self 或 env 均无）
    - pending：有记录但必填字段不全（如只填了 client_id）
    - connected：self 凭证字段完整，或部署环境变量就绪

    纯本地推导（platform_credentials 表 + 环境变量），不请求 SP-API。
    SP-API 真实同步需 Amazon Developer Central 审核（【待确认】）。
    """
    import os

    from ..experts.platform_credentials import PLATFORM_CRED_REGISTRY
    from ..ebay_service import decrypt_secret

    required = [f[0] for f in PLATFORM_CRED_REGISTRY["amazon"]["fields"]]
    rows = (db.query(PlatformCredential)
            .filter(PlatformCredential.user_id == user.id,
                    PlatformCredential.platform.in_(["amazon"]))
            .all())

    best = {"status": "unconnected", "source": None, "connected_at": None,
            "missing_fields": [], "note": "未接入 Amazon 凭证"}
    for row in rows:
        try:
            payload = json.loads(decrypt_secret(row.payload))
        except Exception:
            payload = {}
        missing = [k for k in required if not str(payload.get(k, "")).strip()]
        if not missing:
            return {"platform": "amazon", "status": "connected",
                    "source": "self",
                    "connected_at": row.updated_at.isoformat(),
                    "missing_fields": [],
                    "note": "凭证已就绪；SP-API 真实同步需 Amazon Developer Central "
                            "审核通过（待确认）"}
        if any(str(payload.get(k, "")).strip() for k in required):
            if best["status"] == "unconnected":
                best = {"status": "pending", "source": "self",
                        "connected_at": row.updated_at.isoformat(),
                        "missing_fields": missing,
                        "note": f"缺少必填字段：{', '.join(missing)}"}
            elif len(missing) < len(best.get("missing_fields", [])):
                best["missing_fields"] = missing

    env_ready = all(os.environ.get("CROSSBOT_CRED_AMAZON_" + k.upper())
                    for k in required)
    if env_ready:
        return {"platform": "amazon", "status": "connected", "source": "env",
                "connected_at": None, "missing_fields": [],
                "note": "部署环境已配置 SP-API 凭证"}
    return {"platform": "amazon", **best}


@router.post("/connectors/{platform}/import",
             summary="批量导入某平台的买家会话（手动导入骨架：Allegro/OTTO/Kaufland 等）")
def connector_import(
    platform: str, body: dict, user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """把卖家中心后台的买家消息按模板批量导入统一收件箱。

    body: {"items": [{"buyer_id": "...", "subject": "...", "messages": ["...", ...]}]}
    - 每条 messages 生成一条 incoming 消息（顺序保留）；
    - 导入后即可在收件箱统一回复（出站自动过组合工作流）。
    """
    from ..experts.inbox_connectors import parse_import
    from ..routers.analytics import track_event
    if platform not in PLATFORMS:
        raise HTTPException(status_code=404, detail=f"未知平台: {platform}")
    try:
        rows = parse_import(platform, body.get("items") or [])
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    created = []
    for row in rows:
        c = InboxConversation(
            user_id=user.id, platform=platform,
            external_thread_id=f"manual_{platform}",
            buyer_id=row["buyer_id"], subject=row["subject"],
            last_message_at=datetime.utcnow(),
        )
        db.add(c); db.commit(); db.refresh(c)
        for msg in row["messages"]:
            db.add(InboxMessage(conversation_id=c.id, direction="incoming",
                                body=msg, created_at=datetime.utcnow()))
        c.unread_count = len(row["messages"])
        db.commit()
        # 【P0】批量导入的新买家消息 → 事件触发
        from ..automation_events import enqueue
        enqueue(user.id, "new_buyer_message", {"conversation_id": c.id})
        created.append(_conv_to_dict(c))

    track_event(db, "connector_import", user_id=user.id, platform=platform,
                meta={"count": len(created)})
    return {"imported": len(created), "platform": platform, "items": created}


@router.post("/conversations/seed-demo",
             summary="生成跨 12 平台演示会话（演示统一收件箱用，明确标注 demo）")
def seed_demo(user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    """创建一组跨平台示例会话，便于体验统一收件箱。数据为演示，非真实买家。"""
    samples = [
        ("amazon", "buyer_amz_8821", "Where is my order #123-4567890-1234567?", "物流咨询"),
        ("ebay", "eBay_buyer_x", "The charger caught fire, my son was hurt!", "安全事件"),
        ("allegro", "allegro_klient", "Czy można zwrócić towar?", "退货咨询"),
        ("emag", "emag_client", "Produsul a sosit avariat.", "破损投诉"),
        ("otto", "otto_kunde", "Wann wird mein Paket geliefert?", "物流咨询"),
        ("kaufland", "kaufland_kunde", "Ist der Artikel auch in Größe M verfügbar?", "商品咨询"),
    ]
    created = []
    for plat, buyer, msg, subj in samples:
        if plat not in PLATFORMS:
            continue
        c = InboxConversation(
            user_id=user.id, platform=plat, buyer_id=buyer, subject=subj,
            last_message_at=datetime.utcnow())
        db.add(c); db.commit(); db.refresh(c)
        db.add(InboxMessage(conversation_id=c.id, direction="incoming",
                            body=msg, created_at=datetime.utcnow()))
        db.commit()
        created.append(_conv_to_dict(c))
    return {"seeded": len(created), "demo": True, "items": created}
