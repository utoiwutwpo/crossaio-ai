"""
数据库会话与表结构定义（SQLAlchemy ORM）
本地默认 SQLite，生产切换 PostgreSQL 只需改 DATABASE_URL。
"""
from datetime import datetime, date
from uuid import uuid4

from sqlalchemy import (
    create_engine, Column, String, Integer, Boolean, Text, DateTime, Date,
    Float, ForeignKey, JSON, UniqueConstraint, text,
)
from sqlalchemy.orm import sessionmaker, DeclarativeBase, relationship

from .config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def gen_id() -> str:
    return uuid4().hex


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(String(32), primary_key=True, default=gen_id)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), default="")
    company_name = Column(String(255), default="")
    plan = Column(String(20), default="free")  # free / starter / pro / business
    stripe_customer_id = Column(String(255), default="")
    stripe_subscription_id = Column(String(255), default="")
    stripe_status = Column(String(50), default="")
    # 【P0】该用户最近一次自动体检轮（按订阅频率触发）的 UTC 时间戳；
    # None = 尚未自动跑过（视为到期，下一轮扫描即跑）。
    last_auto_watch_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    descriptions = relationship("ProductDescription", back_populates="user",
                                cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="user",
                              cascade="all, delete-orphan")


class ProductDescription(Base):
    __tablename__ = "product_descriptions"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    product_name = Column(String(255))
    platform = Column(String(50))
    language = Column(String(10), default="en")
    tone = Column(String(20), default="professional")
    title = Column(Text)
    bullet_points = Column(JSON)
    description = Column(Text)
    search_terms = Column(String(1000))
    optimization_score = Column(Float, default=0)
    platform_compliant = Column(Boolean, default=True)
    related_audit_id = Column(String(32), nullable=True)  # 【P0-2】关联最近一次未通过体检
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="descriptions")


class CustomerServiceConversation(Base):
    __tablename__ = "cs_conversations"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    customer_message = Column(Text)
    ai_response = Column(Text)
    intent = Column(String(30), default="other")
    sentiment = Column(String(20), default="neutral")
    needs_escalation = Column(Boolean, default=False)
    related_audit_id = Column(String(32), nullable=True)  # 【P0-2】关联最近一次未通过体检
    created_at = Column(DateTime, default=datetime.utcnow)


class AdCopy(Base):
    __tablename__ = "ad_copies"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    platform = Column(String(50))  # facebook / google / tiktok
    product_name = Column(String(255))
    primary_text = Column(Text)
    headline = Column(String(200))
    ad_description = Column(Text)
    cta = Column(String(100))
    hashtags = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    feature = Column(String(50))          # product_desc / customer_service / ad_copy
    with_compliance = Column(Boolean, default=False)  # 【P0-2】本次调用是否带合规上下文
    log_date = Column(Date, default=date.today, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="usage_logs")


class AnalyticsEvent(Base):
    """验证闭环埋点：landing_view → guest_check → signup → generate → upgrade"""
    __tablename__ = "analytics_events"

    id = Column(String(32), primary_key=True, default=gen_id)
    event_type = Column(String(40), index=True, nullable=False)
    platform = Column(String(50), default="")
    utm_source = Column(String(100), default="")    # reddit / wb_zyb / fb_group_pl ...
    utm_medium = Column(String(100), default="")
    utm_campaign = Column(String(100), default="")
    ip_hash = Column(String(16), default="")        # 匿名：仅哈希前16位
    user_id = Column(String(32), index=True, default="")  # 注册后可关联
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ListingWatch(Base):
    """Listing 仓库：7x24 自动监控的 listing 快照（Phase 1 手动导入）"""
    __tablename__ = "listing_watches"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    sku = Column(String(100), default="")             # 卖家自编 SKU/标识
    product_name = Column(String(255), nullable=False)
    platform = Column(String(50), nullable=False)
    keywords = Column(JSON, default=list)
    title = Column(Text, default="")
    bullets = Column(JSON, default=list)
    description = Column(Text, default="")

    # 最近一次体检结果
    risk_level = Column(String(10), default="low")    # low / medium / high
    risk_score = Column(Float, default=100)
    risk_items = Column(JSON, default=list)
    fix_hints = Column(JSON, default=list)
    gpsr_block = Column(Text, default="")
    prev_risk_level = Column(String(10), default="")  # 上一次体检等级（变化检测用）
    writeback_status = Column(String(20), default="none")
    # none / draft（中低风险，合规块已生成）/ pending（高风险，待写回）/ done（已写回）
    last_checked_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RiskReport(Base):
    """每日风险日报（每用户每天一份，由调度器或手动触发生成）"""
    __tablename__ = "risk_reports"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    report_date = Column(Date, default=date.today, index=True)
    total_listings = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    new_risks = Column(JSON, default=list)      # 风险等级恶化/新增 blocker 的条目
    improved = Column(JSON, default=list)       # 风险等级改善的条目
    email_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ComplianceAudit(Base):
    """一键合规体检记录（GPSR 付费闭环）：每次体检保存摘要，支持历史回看。"""
    __tablename__ = "compliance_audits"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    platform = Column(String(50), nullable=False)
    product_name = Column(String(255), nullable=False)
    risk_level = Column(String(10), default="low")          # low / medium / high
    compliance_score = Column(Integer, default=0)            # 0-100 就绪分
    critical_gap_count = Column(Integer, default=0)
    report = Column(JSON, default=dict)                      # 完整报告（按套餐裁剪后）
    created_at = Column(DateTime, default=datetime.utcnow)


class eBayConnection(Base):
    """eBay 平台授权连接（卖家 OAuth 成功后存储 token）"""
    __tablename__ = "ebay_connections"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False, unique=True)
    access_token = Column(Text, nullable=False)      # 加密存储
    refresh_token = Column(Text, default="")         # 加密存储
    expires_at = Column(Float, nullable=False)       # Unix timestamp
    marketplace_id = Column(String(50), default="")  # 如 EBAY_US, EBAY_DE
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlatformCredential(Base):
    """平台凭证 — 商家在工作台自助粘贴的 API 凭证（AES-256 加密封存）。

    与部署环境级环境变量（CROSSBOT_CRED_*）互补：
    - 环境变量     → 平台运营方统一配置（托管/代理模式）
    - 本表（自助） → 每个商家自己的凭证，12 平台通用，多店铺隔离零运维
    eBay 用户级授权走 eBayConnection（OAuth 流程），不经本表。
    """
    __tablename__ = "platform_credentials"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    platform = Column(String(32), index=True, nullable=False)
    payload = Column(Text, nullable=False)   # JSON 整包加密（字段名见 platform_credentials 注册表）
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("user_id", "platform",
                                       name="uq_user_platform_cred"),)


class EuResponsiblePerson(Base):
    """欧盟授权代表（欧代）台账 — GPSR (EU 2023/988 Art.9) 强制要求。

    合规块与 Listing 文案不再使用 [欧代公司名称] 占位符，而是从这里取值。
    每个用户可维护多条（对应不同品牌/实体），其中一条标记为默认。
    """
    __tablename__ = "eu_responsible_persons"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    company_name = Column(String(255), nullable=False)
    address = Column(Text, nullable=False)
    email = Column(String(255), default="")
    phone = Column(String(80), default="")
    website = Column(String(255), default="")
    contact_person = Column(String(255), default="")   # 对接联系人（可选）
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InboxConversation(Base):
    """跨平台统一收件箱 — 会话（一条会话对应某平台某买家的一串消息）。

    区别于 eBay 专用的 IncomingMessage/OutgoingReply：本表为通用聚合，
    覆盖全部 12 平台，是"统一工作台"的数据核心。实时同步连接器（各平台
    API 拉取）为独立模块，未实现；本表支持手动导入 / 演示种子数据。
    """
    __tablename__ = "inbox_conversations"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    platform = Column(String(50), nullable=False, index=True)   # amazon/ebay/allegro...
    external_thread_id = Column(String(100), default="")        # 平台原生 threadId
    buyer_id = Column(String(100), default="")
    subject = Column(String(300), default="")
    status = Column(String(20), default="open")                 # open / pending / resolved
    unread_count = Column(Integer, default=0)
    last_message_at = Column(DateTime)
    context_json = Column(Text, default="")   # 【P0-1】订单/商品上下文（JSON：order_id/asin/sku），SP-API 待审核前为占位
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InboxMessage(Base):
    """统一收件箱 — 单条消息（方向 in/out，出站消息由组合工作流处理后写入）。"""
    __tablename__ = "inbox_messages"

    id = Column(String(32), primary_key=True, default=gen_id)
    conversation_id = Column(String(32),
                             ForeignKey("inbox_conversations.id", ondelete="CASCADE"),
                             index=True, nullable=False)
    direction = Column(String(10), default="incoming")  # incoming / outgoing
    body = Column(Text, default="")
    intent = Column(String(30), default="other")
    sentiment = Column(String(20), default="neutral")
    needs_escalation = Column(Boolean, default=False)
    gpsr_incident = Column(Boolean, default=False)
    ai_act_disclosure = Column(Text, default="")   # 出站消息附带的 Art.50 披露文本
    created_at = Column(DateTime, default=datetime.utcnow)


class IncomingMessage(Base):
    """eBay 推送过来的买家原始消息"""
    __tablename__ = "ebay_incoming_messages"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    platform = Column(String(20), default="ebay")     # 预留多平台扩展
    message_id = Column(String(100), default="")      # eBay messageId
    thread_id = Column(String(100), default="")       # eBay threadId
    buyer_id = Column(String(100), default="")        # eBay userId
    raw_payload = Column(Text)                        # 完整 JSON（便于调试）
    customer_message = Column(Text)                   # 买家原文
    status = Column(String(20), default="received")   # received / processed / failed
    processed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class OutgoingReply(Base):
    """AI 生成的回复草稿 + 发送状态"""
    __tablename__ = "ebay_outgoing_replies"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    message_id = Column(String(32), ForeignKey("ebay_incoming_messages.id", ondelete="CASCADE"),
                        nullable=False)
    ai_reply = Column(Text)                           # AI 生成原文
    intent = Column(String(30), default="other")      # tracking/return/complaint/product_info
    sentiment = Column(String(20), default="neutral")
    needs_escalation = Column(Boolean, default=False)
    policy_flags = Column(JSON, default=list)         # 命中的红线类型
    guardrail = Column(Text, default="")              # 红线模式提示
    status = Column(String(20), default="draft")      # draft / sent / deleted
    sent_at = Column(DateTime)
    ebay_response = Column(Text)                      # eBay API 返回
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemSetting(Base):
    """系统级配置（eBay 应用凭证等），key-value 存储，value 加密。"""
    __tablename__ = "system_settings"
    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=False)              # AES-256 加密存储
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReviewRewriteLog(Base):
    """【P0-4】跨平台差评回复改写留痕。

    只生成/导出/复制，不自动发送（无任何发送端点）。状态机：
    pending（含规则风险命中，待人工确认）→ approved（自查通过，可复制导出）
    → exported（卖家已复制/导出，由前端标记）。
    """
    __tablename__ = "review_rewrite_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=False)
    platform = Column(String(20), nullable=False)      # amazon / ebay
    listing_ref = Column(String(120), default="")      # ASIN / item id / 链接
    review_snippet = Column(Text, nullable=False)      # 差评原文
    public_reply = Column(Text, default="")            # 公开回复
    private_message = Column(Text, default="")         # 私信安抚（若有）
    rule_check_json = Column(Text, default="{}")       # 规则自查结果 JSON
    status = Column(String(20), default="pending", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    """【P2】站内通知闭环：体检新风险 / 日报生成 / AI 回复 / 写回结果 / 连接器状态变化。"""
    __tablename__ = "notifications"
    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    # risk / report / reply / writeback / system
    type = Column(String(20), default="system", index=True)
    title = Column(String(255), default="")
    body = Column(Text, default="")
    read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


def _ensure_column(engine, table: str, column_name: str, ddl: str) -> None:
    """SQLite 幂等加列：create_all 不会为已存在的表补列（清单 §6 迁移要求）。

    仅处理 SQLite；PostgreSQL 生产环境改由正式迁移工具（Alembic）管理。
    表名/列名均为内部常量，不经用户输入。
    """
    if engine.dialect.name != "sqlite":
        return
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
        if column_name not in cols:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
            conn.commit()


def init_db() -> None:
    Base.metadata.create_all(engine)
    # 【P0-1】增量迁移：收件箱会话上下文列（旧库升级路径）
    _ensure_column(engine, "inbox_conversations", "context_json",
                   "context_json TEXT DEFAULT ''")
    # 【P0-2】增量迁移：合规×运营一体化关联列 + 用量标记列（旧库升级路径）
    _ensure_column(engine, "product_descriptions", "related_audit_id",
                   "related_audit_id VARCHAR(32)")
    _ensure_column(engine, "cs_conversations", "related_audit_id",
                   "related_audit_id VARCHAR(32)")
    _ensure_column(engine, "usage_logs", "with_compliance",
                   "with_compliance BOOLEAN DEFAULT 0")
    # 【P0】订阅驱动的自动体检：users 表记录最近一次自动运行时间（旧库升级路径）
    _ensure_column(engine, "users", "last_auto_watch_at",
                   "last_auto_watch_at DATETIME")
    # 【P0-4】默认差评改写规则模板写入（幂等：仅首次初始化）
    from .experts.review_rewrite import DEFAULT_REVIEW_RULES
    from .ebay_service import encrypt_secret
    try:
        from sqlalchemy.orm import Session as _Session
        with _Session(bind=engine) as s:
            row = s.query(SystemSetting).filter_by(key="review_rules").first()
            if row is None:
                s.add(SystemSetting(
                    key="review_rules",
                    value=encrypt_secret(__import__("json").dumps(
                        DEFAULT_REVIEW_RULES, ensure_ascii=False))))
                s.commit()
    except Exception:
        pass  # 规则模板写入失败不阻断启动（运行时回退内置默认）


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class PlatformTask(Base):
    """B/C 档降级产物：卖家去平台后台处理的任务卡。"""
    __tablename__ = "platform_tasks"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    platform = Column(String(50), index=True, nullable=False)
    kind = Column(String(30), default="message")   # message / order / listing / incident
    external_ref = Column(String(120), default="")
    customer_message = Column(Text, default="")
    draft_reply = Column(Text, default="")
    backoffice_url = Column(String(300), default="")
    status = Column(String(20), default="open")    # open / done / dismissed
    note = Column(String(300), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UsageEvent(Base):
    """六维用量计量（AI 调用 / 处理消息 / 解决工单 / 内容条数 / 事故闭环 / 坐席）。"""
    __tablename__ = "usage_events"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    kind = Column(String(40), index=True, nullable=False)
    qty = Column(Integer, default=1)
    ref_id = Column(String(64), default="")
    log_date = Column(Date, default=date.today, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class IncidentRecord(Base):
    """GPSR 安全事件档案：可追溯、可举证、带 15 天上报倒计时。"""
    __tablename__ = "incident_records"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    platform = Column(String(50), default="")
    sku = Column(String(120), default="")
    buyer_message = Column(Text, default="")
    severity = Column(String(20), default="high")
    status = Column(String(20), default="open")     # open / reported / closed
    dossier_json = Column(Text, default="")
    deadline_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AddOnPurchase(Base):
    """加购包：接入位 / 自动回复次数 / 事故闭环次数 / 坐席。"""
    __tablename__ = "addon_purchases"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    kind = Column(String(30), index=True, nullable=False)
    qty = Column(Integer, default=1)
    unit_price_usd = Column(Float, default=0.0)
    amount_usd = Column(Float, default=0.0)
    status = Column(String(20), default="active")   # active / refunded
    note = Column(String(200), default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class ListingMap(Base):
    """SKU → 平台对象映射（offer_id / unit_id / EAN / 类目），写回与库存的硬前置。"""
    __tablename__ = "listing_map"
    __table_args__ = (__import__("sqlalchemy").UniqueConstraint(
        "user_id", "platform", "sku", name="uq_listing_map"),)

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    platform = Column(String(50), index=True, nullable=False)
    sku = Column(String(120), index=True, nullable=False)
    offer_id = Column(String(120), default="")
    unit_id = Column(String(120), default="")
    ean = Column(String(40), default="")
    extra_json = Column(Text, default="{}")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
