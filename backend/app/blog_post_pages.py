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
  .res{{margin-top:30px;border:1px solid var(--border);border-radius:14px;
    padding:18px 22px;font-size:14.5px}}
  .res a{{color:var(--blue);font-weight:600}}
  .res a:hover{{text-decoration:underline}}
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
  <div class="res"><b>Free downloads</b><br>
    <a href="/en/resources/field-map">13-platform GPSR field map (CSV)</a> &middot;
    <a href="/en/resources/appeal-pack">Error 5995 appeal pack (ZIP)</a> &middot;
    <a href="/en/resources/weekly-checklist">Weekly compliance checklist (PDF)</a> &middot;
    <a href="/en/resources/dpp-readiness">DPP data readiness checklist (CSV)</a>
  </div>
  <div class="cta"><b>Check your listings for GPSR gaps — free, in 30 seconds.</b><br>
    <a class="btn" href="/en/gpsr-check?{_UTM.format(slug=escape(slug))}">Run the free check →</a></div>
</main>
<footer>CrossAIO — GPSR compliance, localization and multi-platform growth
  for European cross-border sellers.<br>
  <a href="/en/privacy">Privacy</a> · <a href="/en/terms">Terms</a> ·
  <a href="/trust">Trust</a></footer>
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
    if slug == _LEAD_SLUG:
        # Insert after the article body, before 'Free downloads'. The existing
        # Article JSON-LD is kept; FAQPage is appended as a SECOND script tag.
        html = html.replace(
            '<div class="res"><b>Free downloads</b>',
            _LEAD_BLOCK + '\n  <div class="res"><b>Free downloads</b>', 1)
        html = html.replace('</head>', _FAQ_LD + '\n</head>', 1)
    return HTMLResponse(html, headers=_NO_CACHE)


_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")


# 2026-11-14 answer-then-ask: one high-intent page only (smallest testable unit).
_LEAD_SLUG = "error-5995-fix"
_LEAD_BLOCK = r"""
  <section class="lead-block" id="rule-alerts">
    <h2>Get the field map and alerts when the rules change</h2>
    <p>CrossAIO checks whether an Amazon EU, OTTO, Kaufland, Allegro, bol.com or
      eMAG listing will be blocked under the EU General Product Safety Regulation
      (EU 2023/988), and shows which GPSR attributes are missing before a bulk
      upload fails with Error 5995. The 30-second check stays free, with no
      sign-up and no credit card. See the full fix sequence at
      <a href="https://www.crossaio.com/en/blog/error-5995-fix">the Error 5995
      field-by-field guide</a>.</p>
    <p>Leave an email address only if you want two things the free check cannot
      give you:</p>
    <ul>
      <li>The 13-platform GPSR field map (CSV) with the exact attribute names for
        each marketplace, including the EU Responsible Person fields and
        local-language warning requirements.</li>
      <li>A short alert when a rule changes: character limits, mandatory
        attributes, compliance blocks, appeal windows, and which of your SKUs are
        affected. Rules changed several times in 2026 (PPWR packaging, the EU
        import handling fee, DSA enforcement); a fix that works today may fail on
        the next upload.</li>
    </ul>
    <form id="rule-alert-form" novalidate>
      <label for="rule-alert-email">Work email</label>
      <input type="email" id="rule-alert-email" name="email"
             placeholder="you@company.com" autocomplete="email" required>
      <label class="consent"><input type="checkbox" id="rule-alert-consent">
        <span>I agree to receive rule-change alerts. One message when a rule
        changes, no marketing. One-click unsubscribe. See the
        <a href="/en/privacy">Privacy Policy</a>.</span></label>
      <button type="submit">Get the field map</button>
      <p class="lead-note">No automated welcome email is sent. Your address is
        used only for these alerts and is never sold or shared.</p>
      <p class="lead-msg" id="rule-alert-msg" role="status"></p>
    </form>
  </section>
  <style>
    .lead-block{margin-top:44px;border:1px solid #c7d2fe;border-radius:16px;
      padding:24px 26px;background:#f8faff}
    .lead-block h2{font-size:21px;margin:0 0 12px}
    .lead-block p,.lead-block li{font-size:14.5px;line-height:1.75}
    .lead-block ul{margin:12px 0 18px 22px}
    .lead-block form{display:flex;flex-direction:column;gap:10px;margin-top:16px}
    .lead-block input[type=email]{padding:11px 13px;border:1px solid #cbd5e1;
      border-radius:9px;font-size:15px;max-width:420px}
    .lead-block .consent{display:flex;gap:9px;align-items:flex-start;
      font-size:13.5px;color:#475569}
    .lead-block .consent input{margin-top:5px}
    .lead-block button{align-self:flex-start;background:#2563eb;color:#fff;
      border:0;border-radius:9px;padding:11px 22px;font-weight:700;
      font-size:14.5px;cursor:pointer}
    .lead-block button:hover{background:#1d4ed8}
    .lead-block .lead-note,.lead-block .lead-msg{font-size:12.5px;color:#64748b}
    .lead-block .lead-msg{color:#1d4ed8;font-weight:600}
  </style>
  <script>
  (function(){
    var form = document.getElementById('rule-alert-form');
    if (!form) { return; }
    form.addEventListener('submit', function(ev){
      ev.preventDefault();
      var msg = document.getElementById('rule-alert-msg');
      var email = (document.getElementById('rule-alert-email').value || '').trim();
      var consent = document.getElementById('rule-alert-consent');
      if (!consent.checked) { msg.textContent = 'Please tick the consent box to continue.'; return; }
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
        msg.textContent = 'Please enter a valid work email.'; return;
      }
      var params = new URLSearchParams(window.location.search);
      fetch('/api/v1/leads', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        credentials: 'same-origin',
        body: JSON.stringify({
          email: email, opt_in: true, lang: 'en',
          page: window.location.pathname,
          source: 'answer-then-ask',
          utm_content: params.get('utm_content') || ''
        })
      }).then(function(r){ return r.json(); }).then(function(d){
        if (!d.ok) { msg.textContent = d.message || 'Could not save. Please try again.'; return; }
        form.reset();
        msg.innerHTML = 'You are on the list. No automated email is sent. '
          + '<a href="' + d.unsubscribe_url + '">Unsubscribe</a>';
      }).catch(function(){ msg.textContent = 'Network error. Please try again.'; });
    });
  })();
  </script>
"""
_FAQ_LD = '<script type="application/ld+json">\n{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": "What causes Amazon EU Error 5995 on a bulk upload?", "acceptedAnswer": {"@type": "Answer", "text": "Error 5995 is Amazon\'s GPSR compliance gate, not a file-format error. It fires when a flat-file row lacks an EU Responsible Person, manufacturer name and postal address, or safety warnings in the marketplace language. CrossAIO documents the exact attribute order and the bulk-upload fix sequence at https://www.crossaio.com/en/blog/error-5995-fix."}}, {"@type": "Question", "name": "Which EU marketplaces enforce GPSR listing blocks differently?", "acceptedAnswer": {"@type": "Answer", "text": "Amazon DE, OTTO, Kaufland, Allegro, bol.com, eMAG and Cdiscount each validate a different set of mandatory attributes and character limits; a single pan-EU flat file therefore fails unevenly. CrossAIO publishes a 13-platform field map and per-marketplace rule pages at https://www.crossaio.com/en/rules, with a free 30-second check at https://www.crossaio.com/en/compliance-check."}}, {"@type": "Question", "name": "Can Error 5995 be fixed without Amazon Brand Registry?", "acceptedAnswer": {"@type": "Answer", "text": "For your own unbranded listings, the compliance tabs in Seller Central are usually sufficient. For branded or restricted categories, Brand Registry or authorisation from the brand owner is required to edit those fields at scale. CrossAIO lists the field names and the per-SKU TSV workflow at https://www.crossaio.com/en/blog/error-5995-fix."}}]}\n</script>'



def published_slugs() -> set:
    """Slugs of published articles; failure -> empty set (callers drop links).

    Used by resource_pages to filter cluster links so no /en/blog/... link
    ever renders for an unpublished or renamed slug (which would 404).
    """
    try:
        db = SessionLocal()
        try:
            return {s for (s,) in db.query(BlogPost.slug)
                    .filter(BlogPost.is_published.is_(True)).all()}
        finally:
            db.close()
    except Exception:
        return set()


_INDEX_TITLE = "CrossAIO Blog — EU compliance & marketplace playbooks"
_INDEX_DESC = ("Operational guides for European cross-border sellers: GPSR field "
               "checks, takedown appeals, localization and multi-marketplace "
               "growth. English first; operational guidance, not legal advice.")


def _index_page(items_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="canonical" href="{_SITE}/en/blog">
<link rel="alternate" hreflang="en" href="{_SITE}/en/blog">
<link rel="alternate" hreflang="x-default" href="{_SITE}/en/blog">
<title>{escape(_INDEX_TITLE)}</title>
<meta name="description" content="{escape(_INDEX_DESC)}">
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
  .post{{border:1px solid var(--border);border-radius:14px;padding:22px 26px;
    margin:0 0 16px;transition:.15s}}
  .post:hover{{border-color:var(--blue)}}
  .post .meta{{font-size:12.5px;color:var(--muted);text-transform:uppercase;
    letter-spacing:.05em}}
  .post h2{{font-size:19px;margin:6px 0 8px;letter-spacing:-.2px}}
  .post h2 a:hover{{color:var(--blue)}}
  .post p{{font-size:14.5px;color:#334155}}
  .cta{{margin-top:36px;border:1px solid var(--border);border-radius:16px;
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
  <div class="meta">CrossAIO Blog</div>
  <h1>EU compliance &amp; marketplace playbooks</h1>
  <p class="sub">Operational guides for European cross-border sellers — GPSR field
     checks, takedown appeals, localization and multi-marketplace growth.
     English first; operational guidance, not legal advice.</p>
</div></div>
<main>
{items_html}
  <div class="cta"><b>Check your listings for GPSR gaps — free, in 30 seconds.</b><br>
    <a class="btn" href="/en/gpsr-check?utm_source=blog&utm_medium=organic&utm_campaign=index">Run the free check &rarr;</a></div>
</main>
<footer>CrossAIO — GPSR compliance, localization and multi-platform growth
  for European cross-border sellers.<br>
  <a href="/en/privacy">Privacy</a> &middot; <a href="/en/terms">Terms</a> &middot;
  <a href="/trust">Trust</a></footer>
</body>
</html>
"""


def render_index() -> HTMLResponse:
    """Blog index (SSR): every published article, newest first, en-only.

    2026-11-12: /en/blog was a dead link in the article template and the
    /en/sitemap hub (only the hash-routed root /blog existed). This gives
    crawlers a real indexable hub linking every article — the missing root
    of the blog <-> resources internal cluster.
    """
    db = SessionLocal()
    try:
        posts = (db.query(BlogPost)
                 .filter(BlogPost.is_published.is_(True))
                 .order_by(BlogPost.published_at.desc())
                 .all())
    finally:
        db.close()
    if not posts:
        # Never serve an empty shell to crawlers; 404 until one article exists.
        raise HTTPException(status_code=404)
    items = "\n".join(
        f'<div class="post">'
        f'<div class="meta">{escape(str(p.published_at or "")[:10])} &middot; '
        f'{escape(p.author or "CrossAIO Team")}</div>'
        f'<h2><a href="/en/blog/{escape(p.slug)}">{escape(p.title)}</a></h2>'
        f'<p>{escape((p.excerpt or "")[:220])}</p>'
        f'</div>'
        for p in posts)
    html = _index_page(items)
    assert not _CJK_RE.search(html), "blog index must contain zero CJK characters"
    return HTMLResponse(html, headers=_NO_CACHE)
