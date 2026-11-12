"""消息同步 worker：按套餐频率从各平台适配器拉取消息并落入统一收件箱。

原则：
- 先过双闸（can_act → read_messages），不过就返回原因，不静默跳过；
- 适配器抛 CapabilityNotSupported 时，把 hint 原样带回给前端；
- 解析失败的邮件落"待归档"（这里用 inbox 会话 + 空消息标记），不冒充已同步。
"""
import asyncio
import json
import logging
from datetime import datetime

from ..connectors.channels.base import CapabilityNotSupported
from ..connectors.channels.registry import adapter_for
from ..database import (InboxConversation, InboxMessage, PlatformCredential,
                        SessionLocal, User)
from ..entitlements import can_act

log = logging.getLogger("crossaio.message_sync")


def _load_payload(db, user_id: str, platform: str) -> dict:
    row = (db.query(PlatformCredential)
           .filter(PlatformCredential.user_id == user_id,
                   PlatformCredential.platform == platform)
           .first())
    if not row:
        return {}
    try:
        from ..ebay_service import decrypt_secret
        raw = decrypt_secret(row.payload)
        data = json.loads(raw) if isinstance(raw, str) else (raw or {})
        return data if isinstance(data, dict) else {}
    except Exception as exc:      # 解密失败不冒充成功
        log.warning("credential decrypt failed for %s: %s", platform, exc)
        return {}


def _upsert(db, user_id: str, msg: dict) -> bool:
    """返回是否新增了一条入站消息。"""
    platform = msg["platform"]
    thread_id = msg.get("external_thread_id") or ""
    conv = (db.query(InboxConversation)
            .filter(InboxConversation.user_id == user_id,
                    InboxConversation.platform == platform,
                    InboxConversation.external_thread_id == thread_id)
            .first())
    if conv is None:
        conv = InboxConversation(
            user_id=user_id, platform=platform,
            external_thread_id=thread_id,
            buyer_id=msg.get("buyer_id", ""),
            subject=(msg.get("subject") or "")[:300],
            status="open", unread_count=0,
        )
        db.add(conv)
        db.flush()

    body = (msg.get("body") or "")[:4000]
    if not body:
        return False
    exists = (db.query(InboxMessage)
              .filter(InboxMessage.conversation_id == conv.id,
                      InboxMessage.direction == msg.get("direction", "incoming"),
                      InboxMessage.body == body)
              .first())
    if exists:
        return False

    db.add(InboxMessage(conversation_id=conv.id,
                        direction=msg.get("direction", "incoming"),
                        body=body))
    conv.unread_count = (conv.unread_count or 0) + 1
    conv.last_message_at = datetime.utcnow()
    return True


async def sync_platform(db, user: User, platform: str) -> dict:
    """同步单平台，返回 {ok, platform, new_messages, reason_code, hint}。"""
    decision = can_act(db, user, platform, "read_messages")
    if not decision["allowed"]:
        return {"ok": False, "platform": platform,
                "reason_code": decision["reason_code"],
                "hint": decision["hint"], "new_messages": 0}

    payload = _load_payload(db, user.id, platform)
    if not payload:
        return {"ok": False, "platform": platform, "reason_code": "not_connected",
                "hint": f"{platform} 尚未保存凭证", "new_messages": 0}

    adapter = adapter_for(platform, payload)
    try:
        messages = await adapter.fetch_messages()
    except CapabilityNotSupported as exc:
        return {"ok": False, "platform": platform,
                "reason_code": exc.reason, "hint": exc.fix_hint,
                "new_messages": 0}

    new_count = 0
    for m in messages:
        try:
            if _upsert(db, user.id, m):
                new_count += 1
        except Exception as exc:
            log.warning("upsert failed %s: %s", platform, exc)
    db.commit()
    return {"ok": True, "platform": platform, "new_messages": new_count,
            "fetched": len(messages), "reason_code": "ok", "hint": ""}


async def sync_all(db, user: User) -> dict:
    platforms = [r.platform for r in
                 db.query(PlatformCredential)
                 .filter(PlatformCredential.user_id == user.id).all()]
    results = await asyncio.gather(*[sync_platform(db, user, p) for p in platforms])
    return {"platforms": len(platforms),
            "ok": sum(1 for r in results if r["ok"]),
            "new_messages": sum(r["new_messages"] for r in results),
            "results": list(results)}


def sync_user_job() -> dict:
    """供调度器调用：对所有已接入平台且套餐允许的用户跑一轮。"""
    db = SessionLocal()
    totals = {"users": 0, "new_messages": 0, "errors": 0}
    try:
        for user in db.query(User).all():
            try:
                res = asyncio.run(sync_all(db, user))
                totals["users"] += 1
                totals["new_messages"] += res["new_messages"]
            except Exception as exc:
                totals["errors"] += 1
                log.warning("sync user %s failed: %s", user.id, exc)
    finally:
        db.close()
    return totals
