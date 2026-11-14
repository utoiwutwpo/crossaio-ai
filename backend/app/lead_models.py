"""EU rule-change alert leads (import registers the table via create_all).

Deliberately separate from newsletter_subscribers: that router sends an
automated Chinese confirmation email when SMTP is configured, which violates
the project red line. This table is only a list, with explicit opt-in.
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String

from .database import Base, gen_id


class RuleAlertLead(Base):
    __tablename__ = "rule_alert_leads"

    id = Column(String(32), primary_key=True, default=gen_id)
    email = Column(String(255), unique=True, index=True, nullable=False)
    email_sha256 = Column(String(64), default="", index=True)
    source = Column(String(50), default="answer-then-ask")
    lang = Column(String(10), default="en")
    page = Column(String(200), default="")
    utm_source = Column(String(100), default="")
    utm_medium = Column(String(100), default="")
    utm_campaign = Column(String(100), default="")
    utm_content = Column(String(100), default="")
    caio_vid = Column(String(64), default="")
    ip_hash = Column(String(64), default="")
    opt_in = Column(Boolean, default=False)
    unsubscribed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
