# -*- coding: utf-8 -*-
"""博客文章真实 URL 页（SEO 可索引）— /en/blog/{slug}
=====================================================
背景（2026-11-06）：博客此前只有 /blog 列表页 + hash 路由（/#slug）+ JSON API，
文章详情没有可被搜索引擎索引的真实 URL。本模块提供服务端渲染的文章页：

- GET /en/blog/{slug}        文章规范 URL（英文首发，进 sitemap）
- GET /blog/{slug}           301 → /en/blog/{slug}（根路径归一，见 main.py）

设计约束：
- 正文 seed 统一用 mdLite 兼容子集（## 标题 / **粗体** / *斜体* /
  "- " 无序列表 / "1. " 有序列表 / [文本](链接) / 段落），
  前端 /blog hash 视图与服务端渲染两端结果一致。
- 所有文本先 HTML escape 再包标签，防注入；链接只允许 http(s) 与站内相对路径。
- zh 不做 SEO（2026-11-06 决策）：hreflang 仅 en + x-default，中文不入。
"""
from __future__ import annotations

import re
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import HTTPException
from fastapi.responses import HTMLResponse

from .community_models import BlogPost
from .database import SessionLocal

_NO_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate"}
_SITE = "https://www.crossaio.com"
_UTM = "utm_source=google&utm_medium=organic&utm_campaign={slug}"

_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+|/[^)\s]*)\)")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITAL_RE = re.compile(r"\*(.+?)\*")


def _safe_href(url: str) -> str | None:
    """链接白名单：http(s) 任意站、站内绝对路径；防 javascript: 等。"""
    u = url.strip()
    if u.startswith("/"):
        return u
    parts = urlsplit(u)
    if parts.scheme in ("http", "https") and parts.netloc:
        return u
    return None


def _inline(text: str) -> str:
    """行内 markdown → HTML（先整体 escape，再按白名单语义包标签）。"""
    s = escape(text)

    # 链接：先抽出为占位符，避免后续 bold/ital 误伤 URL
    links: list[str] = []

    def _link(m: re.Match) -> str:
        href = _safe_href(m.group(2))
        if not href:
            return m.group(1)  # 非白名单链接退化为纯文本
        links.append(f'<a href="{escape(href, quote=True)}" '
                     f'style="color:#2563eb;text-decoration:underline">{m.group(1)}</a>')
        return f"\x00{len(links) - 1}\x00"

    s = _LINK_RE.sub(_link, s)
    s = _BOLD_RE.sub(r"<b>\1</b>", s)
    s = _ITAL_RE.sub(r"<i>\1</i>", s)
    for i, a in enumerate(links):
        s = s.replace(f"\x00{i}\x00", a)
    return s


def md_to_html(body: str) -> str:
    """mdLite 兼容子集 → HTML 块级结构（h2/ul/ol/p）。"""
    out: list[str] = []
    list_tag: str | None = None  # "ul" | "ol"

    def _close_list() -> None:
        nonlocal list_tag
        if list_tag:
            out.append(f"</{list_tag}>")
            list_tag = None

    for raw in body.split("\n"):
        line = raw.rstrip()
        if line.startswith("## "):
            _close_list()
            out.append(f"<h2>{_inline(line[3:])}</h2>")
        elif re.match(r"^\d+\.\s", line):
            if list_tag != "ol":
                _close_list()
                out.append("<ol>")
                list_tag = "ol"
            out.append(f"<li>{_inline(re.sub(r'^\d+\.\s', '', line))}</li>")
        elif line.startswith("- "):
            if list_tag != "ul":
                _close_list()
                out.append("<ul>")
                list_tag = "ul"
            out.append(f"<li>{_inline(line[2:])}</li>")
        elif line.strip() == "":
            _close_list()
        else:
            _close_list()
            out.append(f"<p>{_inline(line)}</p>")
    _close_list()
    return "\n".join(out)


def _page(slug: str, title: str, excerpt: str, author: str,
          published_at: str, body_html: str) -> str:
    import json as _json
    iso_date = (published_at or "")[:10]
    json_title = _json.dumps(title, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="canonical" href="{_SITE}/en/blog/{escape(slug)}">
<link rel="alternate" hreflang="en" href="{_SITE}/en/blog/{escape(slug)}">
<link rel="alternate" hreflang="x-default" href="{_SITE}/en/blog/{escape(slug)}">
<title>{escape(title)} | CrossAIO</title>
<meta name="description" content="{escape(excerpt[:155])}">
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"Article",
  "headline":{json_title},
  "datePublished":"{iso_date}",
  "author":{{"@type":"Organization","name":"CrossAIO"}},
  "publisher":{{"@type":"Organization","name":"CrossAIO"}},
  "mainEntityOfPage":"{_SITE}/en/blog/{escape(slug)}"}}
</script>
<style>
  :root{{--navy:#0b1030;--ink:#0f172a;--muted:#64748b;--border:#e2e8f0;
    --blue:#2563eb;--blue-dark:#1d4ed8;--purple:#8b5cf6;--soft:#f8fafc}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:Inter,"Segoe UI",system-ui,-apple-system,sans-serif;
    background:#fff;color:var(--ink);line-height:1.8}}
  a{{text-decoration:none;color:inherit}}
  nav{{display:flex;justify-content:space-between;align-items:center;
    padding:14px 32px;max-width:1080px;margin:0 auto}}
  .logo{{font-weight:800;font-size:19px;display:flex;align-items:center;gap:8px}}
  .logo .dot{{width:28px;height:28px;border-radius:8px;
    background:linear-gradient(135deg,var(--blue),var(--purple));
    display:inline-flex;align-items:center;justify-content:center;
    color:#fff;font-size:15px}}
  .navlinks{{display:flex;gap:22px;font-size:14.5px;font-weight:600}}
  .navlinks a:hover{{color:var(--blue)}}
  .hero{{background:linear-gradient(135deg,#0b1030 0%,#16204d 55%,#231457 100%);
    color:#fff;padding:56px 32px 60px}}
  .hero-in{{max-width:780px;margin:0 auto}}
  .hero .meta{{font-size:13px;color:#93a5c8;text-transform:uppercase;
    letter-spacing:.05em}}
  .hero h1{{font-size:34px;line-height:1.25;margin:14px 0 12px;letter-spacing:-.4px}}
  .hero p.sub{{color:#cbd5e1;font-size:16px}}
  main{{max-width:780px;margin:0 auto;padding:44px 28px 64px}}
  article h2{{font-size:22px;margin:30px 0 12px;letter-spacing:-.2px}}
  article p{{margin:13px 0;font-size:15.5px}}
  article ul,article ol{{margin:13px 0 13px 26px}}
  article li{{margin:7px 0;font-size:15.5px}}
  article blockquote{{border-left:3px solid var(--border);
    padding-left:14px;color:var(--muted);margin:14px 0}}
  .back{{display:inline-block;color:#93a5c8;font-weight:600;font-size:14px;
    margin-bottom:16px}}
  .back:hover{{color:#fff}}
  .cta{{margin-top:44px;border:1px solid var(--border);border-radius:16px;
    padding:26px;text-align:center;background:var(--soft)}}
  .cta b{{font-size:17px}}
  .btn{{display:inline-block;margin-top:14px;
    background:linear-gradient(135deg,var(--blue),var(--blue-dark));
    color:#fff;font-weight:700;font-size:15px;padding:12px 26px;
    border-radius:11px;transition:.2s;
    box-shadow:0 8px 22px rgba(37,99,235,.35)}}
  .btn:hover{{transform:translateY(-2px)}}
  footer{{border-top:1px solid var(--border);padding:26px 32px;text-align:center;
    color:var(--muted);font-size:13px}}
</style>
</head>
<body>
<nav>
  <div class="logo"><span class="dot">◈</span>CrossAIO</div>
  <div class="navlinks">
    <a href="/en/rules">Rules</a><a href="/en/pricing">Pricing</a>
    <a href="/en/blog">Blog</a><a href="/signup">Sign up</a>
  </div>
</nav>
<div class="hero"><div class="hero-in">
  <a class="back" href="/en/blog">← All posts</a>
  <div class="meta">{iso_date} · {escape(author)}</div>
  <h1>{escape(title)}</h1>
  <p class="sub">{escape(excerpt)}</p>
</div></div>
<main>
  <article>
{body_html}
  </article>
  <div class="cta"><b>Check your listings for GPSR gaps — free, in 30 seconds.</b><br>
    <a class="btn" href="/en/gpsr-check?{_UTM.format(slug=escape(slug))}">Run the free check →</a></div>
</main>
<footer>CrossAIO — GPSR compliance, localization and multi-platform growth
  for European cross-border sellers.<br>
  <a href="/en/privacy">Privacy</a> · <a href="/en/terms">Terms</a> ·
  <a href="/en/trust">Trust</a></footer>
</body>
</html>
"""


def render_post(slug: str) -> HTMLResponse:
    """按 slug 渲染已发布文章；未发布/不存在 → 404。"""
    db = SessionLocal()
    try:
        post = (db.query(BlogPost)
                .filter(BlogPost.slug == slug, BlogPost.is_published.is_(True))
                .first())
    finally:
        db.close()
    if post is None:
        raise HTTPException(status_code=404)
    body_html = md_to_html(post.body or "")
    html = _page(slug, post.title, post.excerpt or "", post.author or "CrossAIO Team",
                 str(post.published_at or ""), body_html)
    return HTMLResponse(html, headers=_NO_CACHE)
