"""播客模块 — 对标 Helium 10 Serious Sellers Podcast（helium10.com/podcast）。

路由前缀：/api/v1/podcast
- GET  /episodes      公开：已发布单集列表
- GET  /feed         公开：RSS 2.0（供 Spotify / Apple Podcasts 抓取）
- POST /episodes      需登录（内容管理）：新增/补全单集
- GET  /{eid}        公开：单集详情
"""
from datetime import datetime, timezone
from email.utils import format_datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from xml.sax.saxutils import escape

from ..database import get_db, User
from ..auth import get_current_user
from ..config import settings
from ..community_models import PodcastEpisode

router = APIRouter()

PODCAST_AUTHOR = "CrossAIO"
# 单集音频托管根（上线时改为 CDN/对象存储地址）
AUDIO_BASE = "https://cdn.crossaio.com/podcast/"

# 多语播客元数据：英文首发，保留 de / fr（欧洲多语；对标 Helium 10 仅英文的缺口）
PODCAST_META = {
    "en": {
        "title": "CrossAIO Compliance & Cross-Border",
        "subtitle": "GPSR compliance, localization and multi-platform growth for European cross-border sellers",
    },
    "de": {
        "title": "CrossAIO Compliance & Cross-Border",
        "subtitle": "GPSR-Konformität, Lokalisierung und Multi-Plattform-Wachstum für europäische Cross-Border-Verkäufer",
    },
    "fr": {
        "title": "CrossAIO Conformité & Cross-Border",
        "subtitle": "Conformité GPSR, localisation et croissance multiplateforme pour les vendeurs cross-border européens",
    },
}
_RSS_LANG = {"en": "en-us", "de": "de-de", "fr": "fr-fr"}


# ---------------- 模型 ----------------
class EpisodeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    audio_url: str = Field(min_length=1, max_length=2000)  # 完整直链；或仅填文件名
    video_url: str = ""    # 视频直链；或仅填 video/xx.mp4（落地页视频闭环）
    shownotes: str = ""
    duration_sec: int = 0
    language: str = "en"   # en / de / fr（英文首发）
    episode_no: int = 0
    published_at: str = None  # ISO 字符串；留空 = 草稿（不进 RSS）


class EpisodeOut(BaseModel):
    id: str
    episode_no: int
    title: str
    description: str
    audio_url: str
    video_url: str = ""
    shownotes: str
    duration_sec: int
    language: str
    published_at: datetime | None

    class Config:
        from_attributes = True


def _resolve_audio(raw: str) -> str:
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    # 相对文件名 -> 本站 /podcast-audio/ 静态目录（static/podcast/）
    return f"{settings.public_url}/podcast-audio/{raw.lstrip('/')}"


def _resolve_video(raw: str | None) -> str:
    """视频相对名（video/xx.mp4）-> /podcast-audio/video/；空/绝对原样。"""
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    return f"{settings.public_url}/podcast-audio/{raw.lstrip('/')}"


def _audio_mime(url: str) -> str:
    lower = url.lower()
    if lower.endswith(".mp3"):
        return "audio/mpeg"
    if lower.endswith(".m4a") or lower.endswith(".mp4"):
        return "audio/mp4"
    if lower.endswith(".ogg") or lower.endswith(".opus"):
        return "audio/ogg"
    return "audio/wav"  # 默认（SAPI 预生成 .wav）


# ---------------- 读取 ----------------
@router.get("/episodes", response_model=list[EpisodeOut], summary="已发布单集列表（?lang= 筛选）")
def list_episodes(lang: str = None, limit: int = 50, db: Session = Depends(get_db)):
    q = db.query(PodcastEpisode).filter(PodcastEpisode.published_at.isnot(None))
    if lang:
        q = q.filter(PodcastEpisode.language == lang)
    eps = q.order_by(PodcastEpisode.published_at.desc()).limit(limit).all()
    for e in eps:
        e.audio_url = _resolve_audio(e.audio_url)
        e.video_url = _resolve_video(e.video_url)
    return eps


@router.get("/feed", summary="RSS 2.0 订阅源（默认 en；?lang=de|fr 切换，供 Spotify / Apple Podcasts）", include_in_schema=True)
def rss_feed(lang: str = "en", db: Session = Depends(get_db)):
    lang = lang if lang in PODCAST_META else "en"
    meta = PODCAST_META[lang]
    rss_lang = _RSS_LANG.get(lang, "en-us")
    eps = (
        db.query(PodcastEpisode)
        .filter(PodcastEpisode.published_at.isnot(None),
                PodcastEpisode.language == lang)
        .order_by(PodcastEpisode.published_at.desc())
        .limit(50)
        .all()
    )
    base = settings.public_url
    items = []
    for e in eps:
        url = _resolve_audio(e.audio_url)
        pub = e.published_at
        try:
            dt = format_datetime(datetime.fromisoformat(pub)) if isinstance(pub, str) else pub
        except Exception:
            dt = format_datetime(datetime.now(timezone.utc))
        items.append(f"""
    <item>
      <title>{escape(e.title)}</title>
      <description>{escape(e.description or '')}</description>
      <link>{escape(base)}/podcast#ep-{e.id}</link>
      <guid isPermaLink="false">{escape(base)}/podcast#ep-{e.id}</guid>
      <pubDate>{dt}</pubDate>
      <enclosure url="{escape(url)}" type="{_audio_mime(url)}" length="{e.duration_sec * 16000}"/>
      <itunes:duration>{e.duration_sec}</itunes:duration>
    </item>""")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>{escape(meta['title'])}</title>
    <link>{escape(base)}</link>
    <language>{escape(rss_lang)}</language>
    <itunes:author>{escape(PODCAST_AUTHOR)}</itunes:author>
    <description>{escape(meta['subtitle'])}</description>
    <itunes:category text="Business"/>
{''.join(items)}
  </channel>
</rss>"""
    return Response(content=xml, media_type="application/rss+xml")


@router.get("/{eid}", response_model=EpisodeOut, summary="单集详情")
def get_episode(eid: str, db: Session = Depends(get_db)):
    e = db.get(PodcastEpisode, eid)
    if e is None or e.published_at is None:
        raise HTTPException(status_code=404, detail="单集不存在")
    e.audio_url = _resolve_audio(e.audio_url)
    e.video_url = _resolve_video(e.video_url)
    return e


# ---------------- 写入（内容管理，需登录） ----------------
@router.post("/episodes", response_model=EpisodeOut, summary="新增/补全单集（草稿或已发布）")
def create_episode(req: EpisodeCreate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    pub = None
    if req.published_at:
        try:
            pub = datetime.fromisoformat(req.published_at)
        except Exception:
            raise HTTPException(status_code=422, detail="published_at 须为 ISO 时间字符串")
    e = PodcastEpisode(
        episode_no=req.episode_no,
        title=req.title,
        description=req.description,
        audio_url=req.audio_url,
        video_url=req.video_url,
        shownotes=req.shownotes,
        duration_sec=req.duration_sec,
        language=req.language,
        published_at=pub,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    e.audio_url = _resolve_audio(e.audio_url)
    e.video_url = _resolve_video(e.video_url)
    return e
