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
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..billing import (plan_config, check_and_record_usage,
                       automation_frequency, AUTOMATION_INTERVALS)
from ..config import settings
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


def auto_reply_conversation(db: Session, user: User, conv_id: str) -> Optional[Dict]:
    """【P0】单会话 AI 客服自动回复（Pro+ 门控 + 生成额度校验；失败返回 None）。

    供 scheduler.drain_events_job（事件触发通道）与 automation_run（一键跑一轮）复用。
    """
    cfg = plan_config(user.plan)
    if "customer_service" not in cfg["features"]:
        return None
    conv = db.get(InboxConversation, conv_id)
    if not conv or conv.user_id != user.id:
        return None
    msgs = (db.query(InboxMessage)
            .filter(InboxMessage.conversation_id == conv.id)
            .order_by(InboxMessage.created_at.asc()).all())
    last_in = next((m for m in reversed(msgs)
                    if m.direction == "incoming"), None)
    has_out = any(m.direction == "outgoing" for m in msgs)
    if not last_in or has_out:
        return None  # 无买家消息或已回复 → 跳过
    try:
        check_and_record_usage(db, user, "customer_service")
    except HTTPException:
        return None  # 额度用尽 → 跳过（不阻断）
    try:
        result = _cs_expert.handle(CustomerServiceRequest(
            customer_message=last_in.body[:4000],
            platform=conv.platform, language="en"))
    except Exception as exc:  # 单条失败不阻断流水线
        log.warning("自动回复失败 conv=%s: %s", conv.id, exc)
        return None
    db.add(InboxMessage(
        conversation_id=conv.id, direction="outgoing",
        body=result.reply, intent=result.intent,
        sentiment=result.sentiment,
        needs_escalation=result.needs_escalation,
        gpsr_incident=result.gpsr_incident,
        ai_act_disclosure=result.ai_act_disclosure or ""))
    db.commit()
    return {"conversation_id": conv.id, "platform": conv.platform,
            "intent": result.intent, "sentiment": result.sentiment,
            "needs_escalation": result.needs_escalation}


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


# ---------------- 自动化流水线三语文案（en/de/fr；zh 用上方原文） ----------------
_AUTO_I18N = {
    "en": {
        "labels": {"watch": "📡 Listing monitoring", "gpsr": "🛡️ GPSR compliance check",
                   "cs": "💬 AI customer service", "inbox": "📥 Unified inbox",
                   "ad": "📣 Ad copy", "review": "🔄 Review rewrite"},
        "watch_active": "Daily auto-audit of {n} listing(s) with risk report",
        "watch_ready": "Add a listing to start daily auto-audit + report",
        "no_credential": "Connect any platform credential and buyer messages enter the auto-processing queue",
        "locked_plan": "Message auto-processing requires Pro plan or above (includes AI customer service)",
        "active": "eBay real-time sync live: buyer messages auto-detected with compliant replies",
        "waiting_connector": "Credential saved; real-time connector for this platform in development — auto-activates at launch",
        "ad_locked": "Ad copy is a Pro plan and above feature",
        "ad_manual": "On-demand generation (no platform credentials needed)",
        "review_manual": "On-demand analysis & rewrite (no credentials needed, counts toward generation quota)",
        "rules": [
            "New buyer message → AI customer service auto-reply (Pro+, connected platforms)",
            "New listing under watch → instant single audit + compliance block",
            "New risk found → compliance block + in-app notification (write-back tiered by plan)",
        ],
        "connector_reason": "eBay OAuth real-time message sync connected",
    },
    "de": {
        "labels": {"watch": "📡 Listing-Überwachung", "gpsr": "🛡️ GPSR-Compliance-Check",
                   "cs": "💬 KI-Kundenservice", "inbox": "📥 Einheitlicher Posteingang",
                   "ad": "📣 Werbetexte", "review": "🔄 Rezensionen umschreiben"},
        "watch_active": "Tägliche automatische Prüfung von {n} Listing(s) mit Risikobericht",
        "watch_ready": "Listing hinzufügen → tägliche Auto-Prüfung + Bericht starten",
        "no_credential": "Nach Verbinden beliebiger Plattform-Zugangsdaten landen Käufernachrichten automatisch in der Verarbeitungswarteschlange",
        "locked_plan": "Automatische Nachrichtenverarbeitung erfordert Pro oder höher (inkl. KI-Kundenservice)",
        "active": "eBay-Echtzeitsynchronisierung aktiv: Käufernachrichten werden automatisch erkannt und konform beantwortet",
        "waiting_connector": "Zugangsdaten gespeichert; Echtzeit-Connector für diese Plattform in Entwicklung — aktiviert sich automatisch zum Start",
        "ad_locked": "Werbetexte sind ab dem Pro-Tarif verfügbar",
        "ad_manual": "Bedarfsgesteuerte Generierung (keine Plattform-Zugangsdaten nötig)",
        "review_manual": "Bedarfsgesteuerte Analyse & Umschreibung (ohne Zugangsdaten, zählt aufs Generierungskontingent)",
        "rules": [
            "Neue Käufernachricht → KI-Kundenservice antwortet automatisch (Pro+, verbundene Plattformen)",
            "Neues Listing in Überwachung → sofortige Einzelprüfung + Compliance-Block",
            "Neues Risiko gefunden → Compliance-Block + In-App-Benachrichtigung (Rückschreibung nach Tarif gestuft)",
        ],
        "connector_reason": "eBay-OAuth-Echtzeitnachrichtensynchronisierung verbunden",
    },
    "fr": {
        "labels": {"watch": "📡 Surveillance des listings", "gpsr": "🛡️ Contrôle de conformité GPSR",
                   "cs": "💬 Service client IA", "inbox": "📥 Boîte de réception unifiée",
                   "ad": "📣 Textes publicitaires", "review": "🔄 Réécriture des avis"},
        "watch_active": "Audit automatique quotidien de {n} listing(s) avec rapport de risques",
        "watch_ready": "Ajoutez un listing pour démarrer l'audit quotidien + rapport",
        "no_credential": "Après connexion d'identifiants d'une plateforme, les messages des acheteurs entrent automatiquement dans la file de traitement",
        "locked_plan": "Le traitement automatique des messages nécessite le plan Pro ou supérieur (service client IA inclus)",
        "active": "Synchronisation eBay en temps réel active : messages acheteurs détectés automatiquement avec réponses conformes",
        "waiting_connector": "Identifiants enregistrés ; connecteur temps réel pour cette plateforme en développement — activation automatique au lancement",
        "ad_locked": "Les textes publicitaires sont réservés au plan Pro et supérieur",
        "ad_manual": "Génération à la demande (aucun identifiant de plateforme requis)",
        "review_manual": "Analyse et réécriture à la demande (sans identifiants, compte dans le quota de génération)",
        "rules": [
            "Nouveau message d'acheteur → réponse automatique du service client IA (Pro+, plateformes connectées)",
            "Nouveau listing surveillé → audit unitaire immédiat + bloc de conformité",
            "Nouveau risque détecté → bloc de conformité + notification in-app (réécriture selon le plan)",
        ],
        "connector_reason": "Synchronisation des messages eBay OAuth en temps réel connectée",
    },
}


def _auto_text(lang: str, key: str) -> str:
    """按语言取流水线文案；zh/未知语言回退调用方原文本（key 原样返回由调用方处理）。"""
    t = _AUTO_I18N.get(lang)
    return (t or {}).get(key, "")


def _next_run_at(freq: str) -> Optional[str]:
    """按频率计算下一次自动运行时间（UTC ISO8601）；manual 返回 None。"""
    if freq == "manual":
        return None
    now = datetime.now(timezone.utc)
    if freq == "realtime":
        return (now + timedelta(seconds=AUTOMATION_INTERVALS["realtime"])).isoformat()
    slots = [settings.watch_daily_hour,
             (settings.watch_daily_hour + 8) % 24,
             (settings.watch_daily_hour + 16) % 24] if freq == "daily_xN" \
        else [settings.watch_daily_hour]
    for h in slots:
        nxt = now.replace(hour=h, minute=0, second=0, microsecond=0)
        if nxt > now:
            return nxt.isoformat()
    base = now.replace(hour=slots[0], minute=0, second=0, microsecond=0)
    return (base + timedelta(days=1)).isoformat()


_TRIGGER_RULES = [
    {"event": "new_buyer_message", "action": "新买家消息 → AI 客服自动回复（Pro+，已接入平台）"},
    {"event": "new_watch_listing", "action": "新 listing 加入监控 → 立即单条体检并生成合规块"},
    {"event": "new_risk", "action": "体检发现新风险 → 生成合规块 + 站内通知（写回按订阅分级）"},
]


def _connector_states() -> List[Dict]:
    """P1 连接器状态矩阵：eBay active，其余待凭据启用（未配置凭证的平台恒为 pending）。"""
    try:
        from ..connectors import connector_states
        return connector_states()
    except Exception:
        return [{"platform": "ebay", "state": "active",
                 "reason": "eBay OAuth 实时消息同步已接入"}]


@router.get("/automation/status",
            summary="自动化矩阵：6 大功能按订阅×凭证的自动化状态")
def automation_status(user: User = Depends(get_current_user),
                      db: Session = Depends(get_db),
                      lang: str = "zh"):
    cfg = plan_config(user.plan)
    quota = cfg["platforms"]                      # None = 无限（business）
    connected = connected_platforms(db, user.id)
    watch_count = (db.query(ListingWatch)
                   .filter(ListingWatch.user_id == user.id).count())
    has_cs = "customer_service" in cfg["features"]
    has_ad = "ad_copy" in cfg["features"]

    t = _AUTO_I18N.get(lang)
    if t:
        watch_detail = (t["watch_active"].format(n=watch_count) if watch_count > 0
                        else t["watch_ready"])
        sync_detail = (t["no_credential"] if not connected else
                       t["locked_plan"] if not has_cs else
                       t["active"] if "ebay" in connected else
                       t["waiting_connector"])
        L = t["labels"]
        features = {
            "watch": {"label": L["watch"], "state": "active" if watch_count > 0 else "ready",
                      "detail": watch_detail},
            "gpsr": {"label": L["gpsr"], "state": "active" if watch_count > 0 else "ready",
                     "detail": watch_detail},  # 日报内含 GPSR 复检+合规块
            "cs": {"label": L["cs"], "state": _sync_state(connected, has_cs)["state"],
                   "detail": sync_detail},
            "inbox": {"label": L["inbox"], "state": _sync_state(connected, has_cs)["state"],
                      "detail": sync_detail},
            "ad": ({"label": L["ad"], "state": "locked_plan", "detail": t["ad_locked"]} if not has_ad else
                   {"label": L["ad"], "state": "manual", "detail": t["ad_manual"]}),
            "review": {"label": L["review"], "state": "manual", "detail": t["review_manual"]},
        }
        trigger_rules = [{"event": r["event"], "action": a}
                         for r, a in zip(_TRIGGER_RULES, t["rules"])]
        connectors = _connector_states()
        for c in connectors:
            if c.get("platform") == "ebay" and c.get("state") == "active":
                c["reason"] = t["connector_reason"]
    else:  # zh / 未知语言：原中文文案
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
            "ad": ({"label": "📣 广告文案", "state": "locked_plan", "detail": "广告文案为 Pro 及以上套餐功能"}
                   if not has_ad else
                   {"label": "📣 广告文案", "state": "manual", "detail": "按需生成（无需平台凭证）"}),
            "review": {"label": "🔄 差评改写", "state": "manual", "detail": "按需分析改写（无需凭证，含在生成额度内）"},
        }
        trigger_rules = _TRIGGER_RULES
        connectors = _connector_states()

    return {
        "plan": user.plan,
        "frequency": automation_frequency(user),
        "next_run_at": _next_run_at(automation_frequency(user)),
        "trigger_rules": trigger_rules,
        "connectors": connectors,
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
            try:
                reply = auto_reply_conversation(db, user, conv.id)
            except HTTPException as exc:
                cs_skipped = f"额度限制：{exc.detail}"
                break
            if reply:
                auto_replies.append(reply)

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
