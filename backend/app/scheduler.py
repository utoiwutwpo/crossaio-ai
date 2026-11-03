"""
7x24 监控调度器（APScheduler）
每日 watch_daily_hour 点（UTC）对所有用户跑体检轮 + 生成风险日报 + 发邮件。
每 50 分钟自动刷新 eBay OAuth 即将过期的 token。
Railway 单实例部署时随 FastAPI lifespan 启动；多实例/外部 cron 时设
WATCH_SCHEDULER_ENABLED=false 关闭。
"""
import logging
import time

from .database import ListingWatch, SessionLocal, User, eBayConnection
from .watch_service import run_user_watch, send_report_email

log = logging.getLogger("crossaio.scheduler")
_scheduler = None


def daily_watch_job() -> dict:
    """每日体检轮：遍历所有有 listing 的用户。返回执行摘要。"""
    db = SessionLocal()
    ran, failed = 0, 0
    try:
        user_ids = [row[0] for row in db.query(User.id).distinct().all()]
        for uid in user_ids:
            user = db.get(User, uid)
            has_listings = db.query(ListingWatch).filter_by(user_id=uid).count() > 0
            if not has_listings:
                continue
            try:
                report = run_user_watch(db, user)
                sent = send_report_email(user, report, db=db)
                log.info("日报完成 user=%s total=%s high=%s email=%s",
                         uid, report["total_listings"],
                         report["high_count"], sent)
                ran += 1
            except Exception:
                log.exception("用户 %s 体检轮失败", uid)
                failed += 1
    finally:
        db.close()
    return {"users_processed": ran, "failed": failed}


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
    _scheduler.add_job(
        daily_watch_job, "cron", hour=settings.watch_daily_hour,
        minute=0, id="daily_watch", replace_existing=True)
    _scheduler.add_job(
        refresh_oauth_tokens_job, "interval", minutes=50,
        id="refresh_oauth_tokens", replace_existing=True)
    _scheduler.start()
    log.info("监控调度器已启动：每日 %02d:00 UTC 体检 + 每 50 分钟刷新 OAuth token",
             settings.watch_daily_hour)


def stop_scheduler() -> None:
    if _scheduler:
        _scheduler.shutdown(wait=False)
