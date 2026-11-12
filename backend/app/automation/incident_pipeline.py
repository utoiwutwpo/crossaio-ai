"""GPSR 安全事件闭环：识别 → 冻结 SKU → 档案 → 15 天上报倒计时 → listing 改写。

这是四条线里唯一"竞品都没做全"的一条：要求同时有客服消息、平台写权限、
合规知识与 listing 编辑权。本模块先做编排，外部写回一律走待确认产物，
不自动提交。
"""
from datetime import datetime, timedelta
import json

from ..connectors.capabilities import PLATFORM_FIX_HINT, supports
from ..database import (IncidentRecord, PlatformTask, PlatformCredential,
                        UsageEvent, gen_id)
from ..experts.compliance_workflow import (compliance_priority_reply,
                                          is_safety_incident)
from ..experts.safety_gate import safety_keywords_hint

REPORT_WINDOW_DAYS = 15   # EU 2023/988 Art.35：事故后 15 天内评估上报


def _connected_platforms(db, user_id: str) -> list[str]:
    return [r.platform for r in
            db.query(PlatformCredential)
            .filter(PlatformCredential.user_id == user_id).all()]


def build_incident(db, user, *, platform: str, message: str,
                   sku: str = "", product_name: str = "",
                   language: str = "en") -> dict:
    """检测并生成事故闭环产物。非安全事件直接返回 is_incident=False。"""
    if not is_safety_incident(message):
        return {"is_incident": False, "reason": "未命中产品安全事件特征"}

    now = datetime.utcnow()
    deadline = now + timedelta(days=REPORT_WINDOW_DAYS)
    incident_id = gen_id()
    connected = _connected_platforms(db, user.id) or [platform]

    # ① 买家侧：当地语言安全指引 + 不认责 + 转人工
    buyer_reply = compliance_priority_reply(platform, language, message, True)

    # ② 平台侧：能写库存的直接给下架/冻结 payload，不能写的落任务卡
    freeze_actions = []
    for p in connected:
        if supports(p, "write_inventory"):
            freeze_actions.append({
                "platform": p, "action": "freeze_sku", "mode": "api",
                "sku": sku, "quantity": 0,
                "note": "需人工确认后提交（AdaptAPI 层不会自动下架）",
            })
        else:
            freeze_actions.append({
                "platform": p, "action": "freeze_sku", "mode": "task",
                "sku": sku,
                "hint": PLATFORM_FIX_HINT.get(p, "请在平台后台手动下架该 SKU"),
            })
            db.add(PlatformTask(
                user_id=user.id, platform=p, kind="incident",
                external_ref=sku or incident_id,
                customer_message=message[:2000],
                note=f"GPSR 安全事件：立即下架/冻结 SKU {sku}",
                backoffice_url="",
            ))

    # ③ 档案：可追溯、可举证
    dossier = {
        "incident_id": incident_id,
        "detected_at": now.isoformat() + "Z",
        "platform": platform,
        "sku": sku,
        "product_name": product_name,
        "buyer_message": message[:2000],
        "severity": "high",
        "regulation": "EU 2023/988 GPSR Art.35（15 天内评估 Safety Gate 上报）",
        "evidence_index": {
            "buyer_message_hash": __import__("hashlib").sha256(
                message.encode("utf-8")).hexdigest()[:32],
            "safety_keywords": safety_keywords_hint()[:12],
            "buyer_reply": buyer_reply,
        },
        "freeze_actions": freeze_actions,
        "listing_patch": {
            "note": "在全平台 listing 增加安全警示与正确使用说明，并核对欧代与批次信息",
            "fields": ["warning_text", "eu_rep", "batch_code", "instructions_language"],
            "submit_mode": "manual_review",
        },
        "report_checklist": [
            "确认事故是否发生在正常使用条件下",
            "统计受影响批次与已售数量",
            "准备产品照片、批次号、合格评定文件",
            f"在 {deadline.date().isoformat()} 前决定是否通过 Safety Gate 上报",
        ],
    }

    rec = IncidentRecord(
        id=incident_id, user_id=user.id, platform=platform, sku=sku,
        buyer_message=message[:4000], severity="high", status="open",
        dossier_json=json.dumps(dossier, ensure_ascii=False),
        deadline_at=deadline,
    )
    db.add(rec)

    # ④ 计量：事故闭环次数
    db.add(UsageEvent(user_id=user.id, kind="incident_closures", qty=1,
                      ref_id=incident_id))
    db.commit()

    return {
        "is_incident": True,
        "incident_id": incident_id,
        "deadline_at": deadline.isoformat() + "Z",
        "days_left": REPORT_WINDOW_DAYS,
        "buyer_reply": buyer_reply,
        "freeze_actions": freeze_actions,
        "dossier": dossier,
    }
