"""
CrossAIO — 增长模块 ORM 模型（社区 / 播客 / 峰会 / 博客 / 信任）
==========================================================
继承 database.Base，随 init_db() 的 Base.metadata.create_all 自动建表。
设计原则（与现有代码一致）：
- user_id 外键关联 users.id，级联删除
- id 用 uuid4 hex（与 User / ProductDescription 一致）
- 时间列默认 datetime.utcnow
- 语言体系：en / de / fr（英文首发，欧洲多语）
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey,
)
from sqlalchemy.orm import relationship

from .database import Base


def _gen_id() -> str:
    return uuid4().hex


# ===================== 社区论坛 =====================
class CommunityThread(Base):
    __tablename__ = "community_threads"

    id = Column(String(32), primary_key=True, default=_gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    author_name = Column(String(255), default="")      # 冗余存昵称，避免每次 JOIN
    category = Column(String(50), default="general", index=True)
    language = Column(String(10), default="en", index=True)  # en / de / fr
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    tags = Column(String(500), default="")             # 逗号分隔
    reply_count = Column(Integer, default=0)
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    replies = relationship("CommunityReply", back_populates="thread",
                           cascade="all, delete-orphan")


class CommunityReply(Base):
    __tablename__ = "community_replies"

    id = Column(String(32), primary_key=True, default=_gen_id)
    thread_id = Column(String(32), ForeignKey("community_threads.id", ondelete="CASCADE"),
                      index=True, nullable=False)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                    index=True, nullable=False)
    author_name = Column(String(255), default="")
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    thread = relationship("CommunityThread", back_populates="replies")


# ===================== 播客 =====================
class PodcastEpisode(Base):
    __tablename__ = "podcast_episodes"

    id = Column(String(32), primary_key=True, default=_gen_id)
    episode_no = Column(Integer, default=0)
    title = Column(String(300), nullable=False)
    description = Column(Text, default="")
    audio_url = Column(Text, nullable=False)           # 托管音频直链（供 RSS enclosure）
    video_url = Column(Text, default="")               # 视频直链（落地页视频播放器闭环）
    shownotes = Column(Text, default="")
    duration_sec = Column(Integer, default=0)
    language = Column(String(10), default="en")        # en / de / fr
    published_at = Column(DateTime, nullable=True)     # 空 = 草稿，不进 RSS
    created_at = Column(DateTime, default=datetime.utcnow)


# ===================== 虚拟峰会 =====================
class SummitRegistration(Base):
    __tablename__ = "summit_registrations"

    id = Column(String(32), primary_key=True, default=_gen_id)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    company = Column(String(255), default="")
    # 渠道归因：复用现有 UTM 范式（与 AnalyticsEvent / users.register 一致）
    utm_source = Column(String(100), default="")
    utm_medium = Column(String(100), default="")
    utm_campaign = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class SummitSession(Base):
    __tablename__ = "summit_sessions"

    id = Column(String(32), primary_key=True, default=_gen_id)
    title = Column(String(300), nullable=False)
    speaker = Column(String(255), default="")
    room = Column(String(50), default="main")
    starts_at = Column(DateTime, nullable=True)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


# ===================== 博客内容矩阵 =====================
class BlogPost(Base):
    __tablename__ = "blog_posts"

    id = Column(String(32), primary_key=True, default=_gen_id)
    slug = Column(String(120), unique=True, index=True, nullable=False)
    language = Column(String(10), default="en", index=True)  # en / de / fr
    title = Column(String(300), nullable=False)
    excerpt = Column(Text, default="")
    body = Column(Text, default="")                    # markdown / 纯文本段落
    author = Column(String(255), default="CrossAIO Team")
    tags = Column(String(300), default="")             # 逗号分隔
    views = Column(Integer, default=0)
    is_published = Column(Boolean, default=False)      # False = 草稿
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ===================== 信任模块：一键取消 =====================
class CancellationRequest(Base):
    __tablename__ = "cancellation_requests"

    id = Column(String(32), primary_key=True, default=_gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    email = Column(String(255), default="")
    plan_at_cancel = Column(String(50), default="")    # 取消时的套餐快照
    reason = Column(Text, default="")
    status = Column(String(20), default="effective")   # effective / feedback
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# ===================== Academy（教育护城河 → 术语同化 → 自然获客） =====================
class AcademyCourse(Base):
    __tablename__ = "academy_courses"

    id = Column(String(32), primary_key=True, default=_gen_id)
    slug = Column(String(120), unique=True, index=True, nullable=False)
    language = Column(String(10), default="en", index=True)  # en / de / fr
    title = Column(String(300), nullable=False)
    summary = Column(Text, default="")
    emoji = Column(String(10), default="🎓")
    level = Column(String(20), default="free")         # free / pro（pro=仅预览课开放）
    is_published = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    lessons = relationship("AcademyLesson", back_populates="course",
                           cascade="all, delete-orphan",
                           order_by="AcademyLesson.sort_order")


class AcademyLesson(Base):
    __tablename__ = "academy_lessons"

    id = Column(String(32), primary_key=True, default=_gen_id)
    course_id = Column(String(32), ForeignKey("academy_courses.id", ondelete="CASCADE"),
                       index=True, nullable=False)
    slug = Column(String(140), unique=True, index=True, nullable=False)
    title = Column(String(300), nullable=False)
    body = Column(Text, default="")                    # 课程正文（绑定 CrossAIO 术语）
    duration_min = Column(Integer, default=10)
    is_free_preview = Column(Boolean, default=False)   # pro 课的免费预览课
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    course = relationship("AcademyCourse", back_populates="lessons")


class AcademyProgress(Base):
    __tablename__ = "academy_progress"

    id = Column(String(32), primary_key=True, default=_gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    lesson_id = Column(String(32), ForeignKey("academy_lessons.id", ondelete="CASCADE"),
                       index=True, nullable=False)
    completed_at = Column(DateTime, default=datetime.utcnow)


class AcademyCertificate(Base):
    __tablename__ = "academy_certificates"

    id = Column(String(32), primary_key=True, default=_gen_id)
    cert_code = Column(String(20), unique=True, index=True, nullable=False)  # XA-XXXXXXXXXX
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    course_id = Column(String(32), ForeignKey("academy_courses.id", ondelete="CASCADE"),
                       index=True, nullable=False)
    learner_name = Column(String(255), default="")
    course_title = Column(String(300), default="")     # 快照，课程改名不影响已发证书
    issued_at = Column(DateTime, default=datetime.utcnow)
