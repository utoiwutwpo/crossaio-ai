"""
7x24 监控调度器（APScheduler）
按订阅频率调度体检轮：
- starter(daily)    : 每日 watch_daily_hour 点 1 次
- pro(daily_xN)     : 每日 3 次（watch_daily_hour / +8h / +16h）
- business(realtime): 每 10 分钟一轮（近实时）
- free(manual)      : 不自动跑（仅手动「立即跑一轮」）
事件触发通道：每 2 分钟 drain 内存事件队列（automation_events），
按事件类型执行对应环节（新 listing→单条体检 / 新买家消息→Pro+ AI 回复 / 新风险→合规块+通知）。
每 50 分钟自动刷新 eBay OAuth 即将过期的 token。
Railway 单实例部署时随 FastAPI lifespan 启动；多实例/外部 cron 时设
WATCH_SCHEDULER_ENABLED=false 关闭。
"""
import logging
import time

from .database import ListingWatch, SessionLocal, User, eBayConnection
from .watch_service import run_user_watch, send_report_email, check_one
from .billing import automation_frequency, plan_config

log = logging.getLogger("crossaio.scheduler")
_scheduler = None


def _cadence_matches(freq: str, cadence: str) -> bool:
    """该用户的自动化频率是否匹配本次调度节奏。"""
    if cadence == "daily":
        return freq in ("daily", "daily_xN")   # starter 每日 1 次；pro 含每日基线
    if cadence == "xN":
        return freq == "daily_xN"               # pro 的 +8h/+16h 附加轮
    if cadence == "realtime":
        return freq == "realtime"               # business 近实时轮
    return False


def daily_watch_job(cadence: str = "daily") -> dict:
    """体检轮：按订阅频率过滤用户后执行。返回执行摘要。"""
    db = SessionLocal()
    ran, failed, skipped = 0, 0, 0
    try:
        user_ids = [row[0] for row in db.query(User.id).distinct().all()]
        for uid in user_ids:
            user = db.get(User, uid)
            freq = automation_frequency(user)
            if not _cadence_matches(freq, cadence):
                skipped += 1
                continue
            has_listings = db.query(ListingWatch).filter_by(user_id=uid).count() > 0
            if not has_listings:
                continue
            try:
                report = run_user_watch(db, user)
                sent = send_report_email(user, report, db=db)
                log.info("日报完成 user=%s cadence=%s total=%s high=%s email=%s",
                         uid, cadence, report["total_listings"],
                         report["high_count"], sent)
                ran += 1
            except Exception:
                log.exception("用户 %s 体检轮失败", uid)
                failed += 1
    finally:
        db.close()
    return {"users_processed": ran, "failed": failed, "skipped": skipped}


def drain_events_job() -> dict:
    """【P0】每 2 分钟 drain 内存事件队列，按事件类型执行对应自动化环节。"""
    from . import automation_events
    from .routers.automation import auto_reply_conversation
    db = SessionLocal()
    stats = {"users": 0, "new_watch_listing": 0, "new_buyer_message": 0, "new_risk": 0}
    try:
        for uid in automation_events.pending_users():
            user = db.get(User, uid)
            if not user:
                automation_events.drain(uid)
                continue
            events = automation_events.drain(uid)
            stats["users"] += 1
            for etype, payload in events:
                if etype == "new_watch_listing":
                    wid = payload.get("watch_id")
                    w = db.get(ListingWatch, wid) if wid else None
                    if w and w.user_id == user.id:
                        try:
                            check_one(db, user, w)
                            stats["new_watch_listing"] += 1
                        except Exception:
                            log.exception("事件 new_watch_listing 处理失败 user=%s", uid)
                elif etype == "new_buyer_message":
                    conv_id = payload.get("conversation_id")
                    cfg = plan_config(user.plan)
                    if cfg.get("auto_reply") and conv_id:
                        try:
                            auto_reply_conversation(db, user, conv_id)
                            stats["new_buyer_message"] += 1
                        except Exception:
                            log.exception("事件 new_buyer_message 处理失败 user=%s", uid)
                    else:
                        stats["new_buyer_message"] += 1  # 非 Pro+ 或缺失会话：诚实跳过
                elif etype == "new_risk":
                    # 合规块已由 check_one 生成；写回分级通知已由 apply_writeback_tier 处理
                    stats["new_risk"] += 1
    finally:
        db.close()
    if stats["users"]:
        log.info("自动化事件 drain：%s", stats)
    return stats


def refresh_oauth_tokens_job() -> dict:
    """每 50 分钟刷新即将过期的 eBay OAuth token（30 分钟内过期的才刷）。
    商家授权一次，token 自动续期，不用重新点授权。"""
    import asyncio
    db = SessionLocal()
    refreshed, failed = 0, 0
    try:
        from .ebay_service import eBayService
        svc = eBayService()
        now = time.time()
        conns = (db.query(eBayConnection)
                 .filter(eBayConnection.expires_at < now + 1800)  # 30 分钟内过期
                 .all())
        for conn in conns:
            try:
                ok = asyncio.get_event_loop().run_until_complete(
                    svc.refresh_access_token(conn))
                if ok:
                    db.commit()
                    refreshed += 1
                else:
                    failed += 1
            except Exception:
                log.exception("eBay token 刷新失败 user=%s", conn.user_id)
                db.rollback()
                failed += 1
    finally:
        db.close()
    if refreshed:
        log.info("eBay token 自动刷新：成功 %d 个，失败 %d 个", refreshed, failed)
    return {"refreshed": refreshed, "failed": failed}


def start_scheduler() -> None:
    global _scheduler
    from .config import settings
    if not settings.watch_scheduler_enabled:
        log.info("监控调度器已通过配置关闭")
        return
    from apscheduler.schedulers.background import BackgroundScheduler
    _scheduler = BackgroundScheduler(timezone="UTC")
    h = settings.watch_daily_hour
    # 每日基线（starter 每日 1 次；pro 含此轮）
    _scheduler.add_job(daily_watch_job, "cron", hour=h, minute=0,
                       kwargs={"cadence": "daily"}, id="watch_daily", replace_existing=True)
    # pro(daily_xN) 附加两轮：+8h / +16h
    _scheduler.add_job(daily_watch_job, "cron", hour=(h + 8) % 24, minute=0,
                       kwargs={"cadence": "xN"}, id="watch_x2", replace_existing=True)
    _scheduler.add_job(daily_watch_job, "cron", hour=(h + 16) % 24, minute=0,
                       kwargs={"cadence": "xN"}, id="watch_x3", replace_existing=True)
    # business(realtime)：每 10 分钟近实时轮
    _scheduler.add_job(daily_watch_job, "interval", minutes=10,
                       kwargs={"cadence": "realtime"}, id="watch_realtime", replace_existing=True)
    # 事件触发通道：每 2 分钟 drain
    _scheduler.add_job(drain_events_job, "interval", minutes=2,
                       id="drain_automation_events", replace_existing=True)
    _scheduler.add_job(
        refresh_oauth_tokens_job, "interval", minutes=50,
        id="refresh_oauth_tokens", replace_existing=True)
    _scheduler.start()
    log.info("监控调度器已启动：daily=%02d:00 UTC / pro +%02d:+%02d / business 10min / 事件 drain 2min",
             h, (h + 8) % 24, (h + 16) % 24)


def stop_scheduler() -> None:
    if _scheduler:
        _scheduler.shutdown(wait=False)
