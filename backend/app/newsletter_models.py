"""政策周报订阅表（导入后随 init_db / create_all 自动建表）。"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String

from .database import Base, gen_id


class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    id = Column(String(32), primary_key=True, default=gen_id)
    email = Column(String(255), unique=True, index=True, nullable=False)
    source = Column(String(50), default="home")   # 来源版块：home / radar / case ...
    lang = Column(String(10), default="zh")       # 页面语言
    page = Column(String(200), default="")        # 提交页面路径
    ip_hash = Column(String(64), default="")      # 只存 IP 的 sha256 前缀，不存明文
    confirmed = Column(Boolean, default=False)
    unsubscribed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
