"""
Listing 监控服务层：体检轮、日报生成、邮件通知、合规块自动写回
被 routers/listings.py（手动触发）与 scheduler.py（每日定时）共同调用。
"""
import logging
from datetime import date, datetime
from typing import Dict, List

from sqlalchemy.orm import Session

from .database import ListingWatch, RiskReport, User, gen_id
from .experts.watchdog import evaluate_listing
from .platform_auth import get_connected_platforms, features_for_platforms

log = logging.getLogger("crossaio.watch")

# 各套餐可监控 listing 数上限（Phase 1 简单配额）
WATCH_LIMITS = {"free": 5, "starter": 20, "pro": 100, "business": 1000}


def check_one(db: Session, watch: ListingWatch) -> Dict:
    """对单条 listing 执行体检并写回结果；返回 {before, after, changed}"""
    result = evaluate_listing(
        product_name=watch.product_name, keywords=watch.keywords or [],
        platform=watch.platform, title=watch.title or "",
        bullets=watch.bullets or [], description=watch.description or "")
    before = watch.risk_level or ""
    watch.prev_risk_level = before
    watch.risk_level = result["risk_level"]
    watch.risk_score = result["risk_score"]
    watch.risk_items = result["risk_items"]
    watch.fix_hints = result["fix_hints"]
    watch.gpsr_block = result["gpsr_block"]
    # 自动写回标记：高风险且已生成合规块 → 标记待写回
    if result["risk_level"] == "high" and result.get("gpsr_block"):
        watch.writeback_status = "pending"  # 待商家确认写回
    elif result["risk_level"] in ("medium", "low") and result.get("gpsr_block"):
        watch.writeback_status = "draft"    # 草稿可用，非紧急
    else:
        watch.writeback_status = "none"
    watch.last_checked_at = datetime.utcnow()
    db.commit()
    return {"before": before, "after": result["risk_level"],
            "score": result["risk_score"], "items": result["risk_items"],
            "gpsr_block": result.get("gpsr_block", ""),
            "writeback_status": watch.writeback_status}


def auto_writeback_ready(db: Session, user: User) -> List[Dict]:
    """返回该用户待自动写回的高风险 listing 列表。
    已接入对应平台 → 自动写回；未接入 → 返回待手动粘贴。"""
    connected = get_connected_platforms(db, user.id)
    feats = features_for_platforms(connected)
    pending = (db.query(ListingWatch)
               .filter(ListingWatch.user_id == user.id,
                       ListingWatch.writeback_status == "pending")
               .all())
    results = []
    for w in pending:
        can_auto = w.platform in connected and feats.get("auto_writeback", False)
        results.append({
            "id": w.id, "sku": w.sku, "product_name": w.product_name,
            "platform": w.platform, "risk_level": w.risk_level,
            "gpsr_block": w.gpsr_block,
            "can_auto_writeback": can_auto,
            "writeback_method": "api_auto" if can_auto else "manual_copy",
        })
    return results


def run_user_watch(db: Session, user: User) -> Dict:
    """对一个用户的全部 listing 跑一轮体检 + 生成当天日报（同日重复跑则覆盖更新）"""
    listings: List[ListingWatch] = (
        db.query(ListingWatch).filter(ListingWatch.user_id == user.id).all())
    new_risks, improved = [], []
    counts = {"high": 0, "medium": 0, "low": 0}

    for w in listings:
        prev = w.prev_risk_level or ""   # 上一次变更前的已知等级
        diff = check_one(db, w)
        after = diff["after"]
        counts[after] = counts.get(after, 0) + 1
        rank = {"low": 0, "medium": 1, "high": 2, "": 0}
        if rank[after] > rank[prev]:
            # prev 为空 = 新入库且首次体检即有风险；非空 = 等级恶化
            new_risks.append({
                "id": w.id, "sku": w.sku, "product_name": w.product_name,
                "platform": w.platform,
                "from": prev or "new", "to": after,
                "top_items": [i["message"] for i in diff["items"][:3]]})
        elif prev and rank[after] < rank[prev]:
            improved.append({"id": w.id, "sku": w.sku,
                             "product_name": w.product_name,
                             "platform": w.platform,
                             "from": prev, "to": after})

    today = date.today()
    report = (db.query(RiskReport)
              .filter(RiskReport.user_id == user.id, RiskReport.report_date == today)
              .first())
    if not report:
        report = RiskReport(id=gen_id(), user_id=user.id, report_date=today)
        db.add(report)
    report.total_listings = len(listings)
    report.high_count = counts["high"]
    report.medium_count = counts["medium"]
    report.low_count = counts["low"]
    report.new_risks = new_risks
    report.improved = improved
    db.commit()
    return report_to_dict(report)


def report_to_dict(r: RiskReport) -> Dict:
    return {
        "report_date": str(r.report_date), "total_listings": r.total_listings,
        "high_count": r.high_count, "medium_count": r.medium_count,
        "low_count": r.low_count, "new_risks": r.new_risks or [],
        "improved": r.improved or [], "email_sent": r.email_sent,
    }


def render_report_email(user: User, report: Dict) -> str:
    """把日报渲染成简洁 HTML 邮件"""
    rows = "".join(
        f"<tr><td>{x.get('sku') or '-'}</td><td>{x['product_name']}</td>"
        f"<td>{x['platform']}</td><td><b style='color:#c0392b'>{x['to']}</b></td>"
        f"<td>{'; '.join(x.get('top_items') or [])}</td></tr>"
        for x in report["new_risks"]) or \
        "<tr><td colspan='5'>无新增风险 🎉</td></tr>"
    return f"""
    <h2>CrossAIO 风险日报 — {report['report_date']}</h2>
    <p>共监控 <b>{report['total_listings']}</b> 条 listing：
       🔴 高风险 {report['high_count']} · 🟡 中风险 {report['medium_count']} ·
       🟢 低风险 {report['low_count']}</p>
    <h3>需处理（等级恶化 / 新增）</h3>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse">
      <tr><th>SKU</th><th>产品</th><th>平台</th><th>风险</th><th>主要问题</th></tr>
      {rows}
    </table>
    <p>修复建议与 GPSR 合规块请登录工作台查看：<br>{'_APP_URL_'}/app</p>
    """


def send_report_email(user: User, report: Dict, db=None) -> bool:
    """SMTP 未配置时跳过（日报仍入库可在工作台查看）。
    按套餐裁剪：free=不发邮件；starter=每周一发；pro=每日；business=每日+实时预警。"""
    from .config import settings
    from .billing import plan_config

    if not settings.smtp_host or not user.email:
        return False

    plan = user.plan

    # free 套餐不发邮件
    if plan == "free":
        return False

    # starter 只在每周一发
    if plan == "starter":
        from datetime import date as _d
        if _d.today().weekday() != 0:  # 0=Monday
            return False

    try:
        from .mailer import send_email
        html = render_report_email(user, report).replace(
            "_APP_URL_", settings.app_url)

        # business 套餐额外加实时预警段
        if plan == "business":
            if db:
                pending = auto_writeback_ready(db, user)
            else:
                from .database import SessionLocal
                _db = SessionLocal()
                try:
                    pending = auto_writeback_ready(_db, user)
                finally:
                    _db.close()
            if pending:
                pending_rows = "".join(
                    f"<tr><td>{p['product_name']}</td><td>{p['platform']}</td>"
                    f"<td><b style='color:#c0392b'>{p['risk_level']}</b></td>"
                    f"<td>{p['writeback_method']}</td></tr>"
                    for p in pending)
                html += f"""
                <h3>⚡ 实时预警（Business 专属）</h3>
                <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse">
                  <tr><th>产品</th><th>平台</th><th>风险</th><th>写回方式</th></tr>
                  {pending_rows}
                </table>"""

        send_email(
            to=user.email,
            subject=f"[CrossAIO] 风险日报 {report['report_date']}："
                    f"{report['high_count']} 高风险 / {report['medium_count']} 中风险",
            html=html)
        return True
    except Exception as exc:  # 邮件失败不阻断日报
        log.warning("日报邮件发送失败 user=%s: %s", user.id, exc)
        return False
