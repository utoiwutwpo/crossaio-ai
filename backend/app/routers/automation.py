"""自动化流水线：平台凭证 × 订阅档位 → 店铺问题自动识别、自动处理。

设计（诚实边界）：
- 自动识别：Listing 监控体检轮（watch_service.run_user_watch，调度器每日已自动跑）
  发现店铺 listing 的 GPSR/规则风险；统一收件箱汇聚买家消息。
- 自动处理：高风险 listing 自动生成 GPSR 合规块（watch 已内置）；未回复买家会话
  由 AI 客服 expert 自动生成合规回复（Art.50 披露 + 情绪/意图识别），写入收件箱。
- 按订阅档位自动识别：customer_service / ad_copy 环节按 PLANS.features 门控，
  平台接入数量按 PLANS.platforms 配额（保存凭证时强制，见 compliance.save_platform_creds）。
- 差评改写 / 广告文案：问题驱动联动建议（不自动消耗生成额度）。
"""
import logging
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..billing import plan_config, check_and_record_usage
from ..database import (get_db, User, ListingWatch, eBayConnection,
                        PlatformCredential, InboxConversation, InboxMessage)
from ..experts.customer_service import CustomerServiceExpert
from ..platform_auth import get_connected_platforms, features_for_platforms
from ..schemas import CustomerServiceRequest
from ..watch_service import run_user_watch, send_report_email

log = logging.getLogger("crossaio.automation")
router = APIRouter()
_cs_expert = CustomerServiceExpert()

# 6 大功能的自动化语义（与工作台自动化卡片一一对应）
_FEATURES = [
    ("watch", "📡 Listing 监控"),
    ("gpsr", "🛡️ GPSR 合规体检"),
    ("cs", "💬 AI 客服"),
    ("inbox", "📥 统一收件箱"),
    ("ad", "📣 广告文案"),
    ("review", "🔄 差评改写"),
]

# 差评/负面信号词（问题分诊：命中则联动差评改写）
_REVIEW_SIGNALS = ("broken", "refund", "return", "waste", "terrible",
                   "worst", "scam", "danger", "hurt", "broke", "坏", "差评",
                   "退款", "退货", "危险", "断裂")


def connected_platforms(db: Session, user_id: str) -> set:
    """当前用户已接入的平台集合（自助凭证表 + eBay OAuth 连接）。
    统一从 platform_auth 模块导入，保持单一口径。"""
    return get_connected_platforms(db, user_id)


def _sync_state(connected: set, has_cs: bool) -> Dict:
    """AI 客服 / 统一收件箱共用的「消息自动处理」状态机（按订阅×凭证）。"""
    if not connected:
        return {"state": "no_credential",
                "detail": "接入任一平台凭证后，买家消息自动进入处理队列"}
    if not has_cs:
        return {"state": "locked_plan",
                "detail": "消息自动处理需 Pro 及以上套餐（含 AI 客服）"}
    if "ebay" in connected:
        return {"state": "active",
                "detail": "eBay 实时同步已上线：买家消息自动识别并生成合规回复"}
    return {"state": "waiting_connector",
            "detail": "凭证已保存；该平台实时同步连接器开发中，上线即自动接管"}


@router.get("/automation/status",
            summary="自动化矩阵：6 大功能按订阅×凭证的自动化状态")
def automation_status(user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    cfg = plan_config(user.plan)
    quota = cfg["platforms"]                      # None = 无限（business）
    connected = connected_platforms(db, user.id)
    watch_count = (db.query(ListingWatch)
                   .filter(ListingWatch.user_id == user.id).count())
    has_cs = "customer_service" in cfg["features"]
    has_ad = "ad_copy" in cfg["features"]

    watch_state = (
        "active" if watch_count > 0 else "ready",
        (f"每日自动体检 {watch_count} 个 listing 并生成风险日报"
         if watch_count > 0 else "添加 listing 后即进入每日自动体检+日报"))
    watch_pair = {"state": watch_state[0], "detail": watch_state[1]}
    sync = _sync_state(connected, has_cs)

    features = {
        "watch": {"label": "📡 Listing 监控", **watch_pair},
        "gpsr": {"label": "🛡️ GPSR 合规体检", **watch_pair},  # 日报内含 GPSR 复检+合规块
        "cs": {"label": "💬 AI 客服", **sync},
        "inbox": {"label": "📥 统一收件箱", **sync},
        "ad": ({"state": "locked_plan", "detail": "广告文案为 Pro 及以上套餐功能"}
               if not has_ad else
               {"state": "manual", "detail": "按需生成（无需平台凭证）"}),
        "review": {"state": "manual", "detail": "按需分析改写（无需凭证，含在生成额度内）"},
    }
    return {
        "plan": user.plan,
        "platform_quota": {"limit": quota, "used": len(connected)},
        "connected_platforms": sorted(connected),
        "features": features,
    }


@router.post("/automation/run",
             summary="一键串联流水线：识别店铺问题 → 按订阅自动处理 6 大功能")
def automation_run(user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """流水线四步：①监控体检识别问题 → ②高风险自动生成 GPSR 合规块 →
    ③收件箱未回复会话自动生成合规回复（按订阅门控）→ ④差评/广告联动建议。"""
    cfg = plan_config(user.plan)
    has_cs = "customer_service" in cfg["features"]
    has_ad = "ad_copy" in cfg["features"]

    # ① 自动识别：监控体检轮（含 GPSR 复检）
    report = run_user_watch(db, user)

    # ② 自动处理：高风险/中风险 listing 的 GPSR 合规块已由体检自动生成
    risky = (db.query(ListingWatch)
             .filter(ListingWatch.user_id == user.id,
                     ListingWatch.risk_level.in_(["high", "medium"]))
             .all())
    gpsr_done = [{"id": w.id, "product_name": w.product_name,
                  "platform": w.platform, "risk": w.risk_level,
                  "gpsr_block_ready": bool(w.gpsr_block)}
                 for w in risky]

    # ③ 自动处理：收件箱未回复会话 → AI 客服合规回复（按订阅门控+额度）
    auto_replies, cs_skipped = [], None
    if not has_cs:
        cs_skipped = "消息自动处理需 Pro 及以上套餐（当前 {}）".format(user.plan)
    else:
        convs = (db.query(InboxConversation)
                 .filter(InboxConversation.user_id == user.id).all())
        for conv in convs:
            msgs = (db.query(InboxMessage)
                    .filter(InboxMessage.conversation_id == conv.id)
                    .order_by(InboxMessage.created_at.asc()).all())
            last_in = next((m for m in reversed(msgs)
                            if m.direction == "incoming"), None)
            has_out = any(m.direction == "outgoing" for m in msgs)
            if not last_in or has_out:
                continue  # 无买家消息或已回复 → 跳过
            try:
                check_and_record_usage(db, user, "customer_service")
            except HTTPException as exc:
                cs_skipped = f"额度限制：{exc.detail}"
                break
            try:
                result = _cs_expert.handle(CustomerServiceRequest(
                    customer_message=last_in.body[:4000],
                    platform=conv.platform, language="en"))
            except Exception as exc:  # 单条失败不阻断流水线
                log.warning("自动回复失败 conv=%s: %s", conv.id, exc)
                continue
            db.add(InboxMessage(
                conversation_id=conv.id, direction="outgoing",
                body=result.reply, intent=result.intent,
                sentiment=result.sentiment,
                needs_escalation=result.needs_escalation,
                gpsr_incident=result.gpsr_incident,
                ai_act_disclosure=result.ai_act_disclosure or ""))
            db.commit()
            auto_replies.append({
                "conversation_id": conv.id, "platform": conv.platform,
                "intent": result.intent, "sentiment": result.sentiment,
                "needs_escalation": result.needs_escalation})

    # ④ 联动建议（问题驱动，不自动消耗额度）
    suggestions: List[Dict] = []
    neg_convs = (db.query(InboxMessage)
                 .join(InboxConversation,
                       InboxMessage.conversation_id == InboxConversation.id)
                 .filter(InboxConversation.user_id == user.id,
                         InboxMessage.direction == "incoming",
                         InboxMessage.sentiment == "negative").count())
    if neg_convs:
        suggestions.append({
            "feature": "review", "action": "差评改写",
            "reason": f"收件箱有 {neg_convs} 条负面情绪买家消息，"
                      "建议用「差评改写」定位 listing 缺口并生成五点修复"})
    if has_ad:
        healthy = (db.query(ListingWatch)
                   .filter(ListingWatch.user_id == user.id,
                           ListingWatch.risk_level == "low").count())
        if healthy:
            suggestions.append({
                "feature": "ad", "action": "广告文案",
                "reason": f"{healthy} 个 listing 状态健康，"
                          "可用「广告文案」为表现好的产品扩量"})

    email_sent = send_report_email(user, report)
    found = len(gpsr_done) + len(auto_replies)
    return {
        "ok": True,
        "summary": {
            "problems_found": found,
            "gpsr_blocks_ready": len(gpsr_done),
            "auto_replies_sent": len(auto_replies),
            "skipped": ([{"step": "cs_autoreply", "reason": cs_skipped}]
                        if cs_skipped else []),
            "suggestions": suggestions,
            "email_sent": email_sent,
        },
        "report": report,
        "gpsr_done": gpsr_done,
        "auto_replies": auto_replies,
    }


@router.get("/automation/writeback",
            summary="查看待自动写回的合规块（高风险 listing）")
def list_writeback(user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """列出所有待写回的高风险 listing：已接入平台的自动写回，未接入的提供手动复制。"""
    from ..watch_service import auto_writeback_ready
    items = auto_writeback_ready(db, user)
    return {"items": items, "total": len(items)}


@router.post("/automation/writeback/{watch_id}",
             summary="确认写回合规块到 listing")
def confirm_writeback(watch_id: str,
                      user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    """商家确认后标记写回完成。已接入平台的走 API 自动写回，未接入的复制粘贴。"""
    from ..database import ListingWatch
    w = (db.query(ListingWatch)
         .filter(ListingWatch.id == watch_id,
                 ListingWatch.user_id == user.id).first())
    if not w:
        raise HTTPException(404, "Listing 不存在")
    w.writeback_status = "done"
    db.commit()
    return {"ok": True, "id": w.id, "product_name": w.product_name,
            "message": "合规块已标记为已写回"}
