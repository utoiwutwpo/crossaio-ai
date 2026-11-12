# -*- coding: utf-8 -*-
"""English-only downloadable resource pages (stage-3 restore patch, 2026-11-12).

Deploy target: backend/app/resource_pages.py
Routes are wired by patch_resources.py -> main.deploy.py.

Design constraints:
  * Four indexable /en/resources/{slug} pages, one per real asset in
    static/downloads/. English-only: no de/fr/zh URL exists, so the patched
    main.py suppresses those alternates for these paths (and for articles).
  * Every page ships Article-style FAQPage + BreadcrumbList JSON-LD, a
    visible "last verified" date and a not-legal-advice disclaimer.
  * Download is frictionless: no email gate, no redirect, no external host.
  * The optional opt-in is UNCHECKED by default. It deliberately does NOT
    call /api/v1/newsletter/subscribe: that endpoint sends an automated
    Chinese confirmation email when SMTP_HOST is configured, which conflicts
    with the project red lines. Only an anonymous `lead_capture` analytics
    event is emitted (email domain only, never the address itself).
  * No project-internal imports, so this module can be rendered in isolation
    by the verification harness without booting the whole application.

The module never writes to the database and never sends email.
"""
from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse, HTMLResponse

_SITE = "https://www.crossaio.com"
_VERIFIED = "2026-11-12"
_NO_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate"}

# Visible CTA strings are localized client-side by navigator.language.
# HTML always ships the English version first (crawler-visible, zero CJK).
_CTA = {
    "en": {
        "download": "Download the {fmt} — no email required",
        "answer": "Check these three things first",
        "optin": "Notify me when marketplace fields change",
        "disclaimer": "Operational guidance, not legal advice. Verify against current marketplace documentation.",
        "optin_note": "Unchecked by default. No email address is stored and no automated email is sent.",
        "sent": "Interest recorded. No email is stored and no automated email is sent.",
        "tick": "Tick the box to register interest.",
        "badmail": "Enter a valid work email.",
    },
    "de": {
        "download": "{fmt} herunterladen – ohne E-Mail-Adresse",
        "answer": "Prüfen Sie zuerst diese drei Punkte",
        "optin": "Benachrichtigen, wenn sich Marktplatz-Felder ändern",
        "disclaimer": "Arbeitshilfe, keine Rechtsberatung. Gegen aktuelle Marktplatz-Dokumentation prüfen.",
        "optin_note": "Standardmäßig nicht aktiviert. Es wird keine E-Mail-Adresse gespeichert und keine automatische E-Mail versendet.",
        "sent": "Interesse erfasst. Es wird keine E-Mail gespeichert und keine automatische E-Mail versendet.",
        "tick": "Bitte das Kästchen aktivieren.",
        "badmail": "Bitte eine gültige geschäftliche E-Mail-Adresse eingeben.",
    },
    "fr": {
        "download": "Télécharger le {fmt} – sans e-mail",
        "answer": "Vérifiez d'abord ces trois points",
        "optin": "Me prévenir lorsque les champs changent",
        "disclaimer": "Aide opérationnelle, pas un conseil juridique. Vérifier dans la documentation actuelle.",
        "optin_note": "Non coché par défaut. Aucune adresse e-mail n'est conservée et aucun e-mail automatique n'est envoyé.",
        "sent": "Intérêt enregistré. Aucune adresse e-mail n'est conservée et aucun e-mail automatique n'est envoyé.",
        "tick": "Cochez la case pour enregistrer votre intérêt.",
        "badmail": "Saisissez une adresse e-mail professionnelle valide.",
    },
}

# All values below are transcribed from the real generated assets. The
# verification harness cross-checks the preview strings against those files.
RESOURCES = {
    "field-map": {
        "asset_id": "marketplace-gpsr-field-map",
        "file": "marketplace-gpsr-field-map.csv",
        "format": "csv",
        "campaign": "launch",
        "branch": "01 BEFORE LAUNCH",
        "title": "GPSR Field Map for 13 EU Marketplaces - Free CSV",
        "h1": "GPSR fields not accepted by your flat file?",
        "deck": ("Exact column names, EU Responsible Person fields and "
                 "warning-language rules for 13 European marketplaces, in one "
                 "spreadsheet. Last verified " + _VERIFIED + "."),
        "answer_steps": [
            ("01 FIELD NAME",
             "Use the marketplace-specific column, not the Seller Central UI label."),
            ("02 BRAND OWNER",
             "Error 5995 is usually a permission wall, not a broken attribute."),
            ("03 EVIDENCE",
             "Keep a dated copy of the flat file, the exact error text and the ASIN list."),
        ],
        "preview_title": "What is in the CSV",
        "preview_rows": [
            ("13 rows / 20 columns", "platform_id, marketplace, markets, gpsr_scope, rp_label_native, where_to_enter, official_policy_url, last_verified ..."),
            ("Amazon EU", "One language per site; 8 languages in the TSV default; title_max_chars = 200"),
            ("Kaufland", "POLICY 4 languages / tool default DE - verify before upload"),
            ("Amazon US + Walmart", "US - GPSR NOT directly applicable"),
        ],
        "faq": [
            ("Which marketplaces are covered?",
             "13 marketplaces including Amazon EU, Allegro, bol.com, eMAG, OTTO, Kaufland and Cdiscount. US-only platforms are included but explicitly marked as not directly in GPSR scope."),
            ("Is this an official marketplace document?",
             "No. It is an operational cross-reference compiled from public marketplace help pages. Every row carries its official policy URL; verify against the current page before a bulk upload."),
            ("Does the download require an email address?",
             "No. The CSV is served directly from this site. We record an anonymous download event only, so we can tell which resources sellers actually use."),
        ],
        "cluster": [
            ("13-platform rule library", "/en/rules"),
            ("Listing generator for launch", "/en/features/listing-generator"),
            ("Before-launch capability map", "/en/v2/launch"),
            ("Why listings get blocked (GPSR)", "/en/blog/why-listings-get-blocked-gpsr"),
            ("GPSR technical file checklist", "/en/blog/gpsr-technical-file-checklist"),
        ],
        "feature": ("/en/features/listing-generator", "Check your listing fields before upload"),
    },
    "appeal-pack": {
        "asset_id": "error-5995-appeal-pack",
        "file": "error-5995-appeal-pack.zip",
        "format": "zip",
        "campaign": "rescue",
        "branch": "02 ACCIDENT",
        "title": "Error 5995 Appeal Pack - Free Templates",
        "h1": "Listing suppressed with Error 5995?",
        "deck": ("An editable appeal letter, a 15-line evidence checklist and an "
                 "eight-step diagnosis for bulk-upload permission walls. Last "
                 "verified " + _VERIFIED + "."),
        "answer_steps": [
            ("01 PERMISSION",
             "Check whether the account holds the Brand Registry role for the ASIN before rewriting any attribute."),
            ("02 EVIDENCE",
             "Save the takedown notice, the exact listing version and the field-level error text in hour one."),
            ("03 ONE ASIN",
             "For small catalogues submit through Account Health / Manage Your Compliance one ASIN at a time."),
        ],
        "preview_title": "What is in the ZIP (7 files)",
        "preview_rows": [
            ("01_appeal_letter_EN.txt / .docx", "Editable appeal letter with subject, evidence block and disclosure"),
            ("02_evidence_checklist.csv", "15 evidence rows: DoC, EU RP authorisation, test reports, dated flat file"),
            ("03_error_5995_diagnosis.txt", "Eight-step diagnosis, permission wall first, data quality second"),
            ("04 / 05", "Upload workflow + 13 official marketplace policy URLs"),
        ],
        "faq": [
            ("Is Error 5995 a data error?",
             "Usually not. On Amazon EU bulk uploads it is most often a Brand Registry / bulk-permission wall. Re-uploading an unchanged flat file rarely clears it."),
            ("Can I edit the appeal letter?",
             "Yes. The pack contains both plain text and an editable DOCX. Replace the bracketed ASIN, date and contact placeholders before sending."),
            ("Is this legal advice?",
             "No. It is an operational template with a disclosure line. Attach your own Declaration of Conformity and EU Responsible Person authorisation; verify current marketplace policy."),
        ],
        "cluster": [
            ("Safety red-line checks", "/en/features/safety-redline"),
            ("Accident capability map", "/en/v2/rescue"),
            ("13-platform rule library", "/en/rules"),
            ("Why listings get blocked (GPSR)", "/en/blog/why-listings-get-blocked-gpsr"),
            ("EU Responsible Person guide", "/en/blog/eu-responsible-person-complete-guide"),
        ],
        "feature": ("/en/features/safety-redline", "Run the safety red-line check"),
    },
    "weekly-checklist": {
        "asset_id": "eu-compliance-weekly-checklist",
        "file": "eu-compliance-weekly-checklist.pdf",
        "format": "pdf",
        "campaign": "ops",
        "branch": "03 DAILY OPERATIONS",
        "title": "EU Compliance Weekly Checklist - Free PDF",
        "h1": "Need a repeatable weekly compliance check?",
        "deck": ("A three-page printable checklist for GPSR (EU) 2023/988: before "
                 "every bulk upload, weekly, quarterly, evidence retention and "
                 "takedown response. Last verified " + _VERIFIED + "."),
        "answer_steps": [
            ("01 BEFORE UPLOAD",
             "Manufacturer, EU RP, product identifier and local-language warnings in ONE source table."),
            ("02 WEEKLY",
             "Pull the Manage Your Compliance queue and spot-check 10 live offers per marketplace."),
            ("03 EVIDENCE",
             "Keep the DoC and technical documentation for 10 years (GPSR Art. 9); never overwrite a submitted file."),
        ],
        "preview_title": "Sections in the PDF",
        "preview_rows": [
            ("A. BEFORE EVERY BULK UPLOAD", "UTF-8 BOM, TAB separated, keyed on manufacturer reference, not ASIN"),
            ("B. WEEKLY", "Field-level error text, reconciliation, 10-offer spot check, DoC version"),
            ("C. BEFORE PEAK SEASON / QUARTERLY", "Re-verify 13 policy pages, EU RP appointment, new-country warnings"),
            ("D / E / F", "Evidence retention, 13-marketplace quick check, when a listing is suppressed"),
        ],
        "faq": [
            ("Is the checklist specific to one marketplace?",
             "No. Section E is a quick check for all 13 marketplaces in the CrossAIO native rules library, including the tool-versus-policy language differences."),
            ("How long should evidence be kept?",
             "The PDF states 10 years for the Declaration of Conformity and technical documentation under GPSR Art. 9, and recommends dated, versioned copies of every submitted flat file."),
            ("Can I print it for a warehouse team?",
             "Yes. It is a three-page A4-style PDF with checkbox bullets, designed to be printed one copy per SKU family."),
        ],
        "cluster": [
            ("Listing watch", "/en/features/listing-watch"),
            ("Daily operations capability map", "/en/v2/ops"),
            ("13-platform rule library", "/en/rules"),
            ("EU VAT / OSS guide", "/en/blog/eu-vat-oss-guide-marketplace-sellers"),
            ("GPSR technical file checklist", "/en/blog/gpsr-technical-file-checklist"),
        ],
        "feature": ("/en/features/listing-watch", "Set up continuous listing watch"),
    },
    "dpp-readiness": {
        "asset_id": "dpp-data-readiness",
        "file": "dpp-data-readiness.csv",
        "format": "csv",
        "campaign": "govern",
        "branch": "04 GOVERNANCE",
        "title": "DPP Data Readiness Checklist - Free CSV",
        "h1": "Which product data should you collect for the DPP window?",
        "deck": ("25 fields prioritized P0 / P1 / P2, showing what is already "
                 "required under GPSR today and what is only preparatory. Last "
                 "verified " + _VERIFIED + "."),
        "answer_steps": [
            ("01 START WITH P0",
             "GTIN / EAN, manufacturer name, product identifier and EU RP are already GPSR evidence - collect them now."),
            ("02 MIND THE DATE",
             "Category-level DPP is NOT mandatory as of " + _VERIFIED + "; the ESPR working plan is indicative and delegated acts carry at least 18 months transition."),
            ("03 SEPARATE BATTERY",
             "The battery passport has its own hard date of 2027-02-18; do not mix it with category-level DPP claims."),
        ],
        "preview_title": "What is in the CSV",
        "preview_rows": [
            ("25 rows / 11 columns", "priority, data_field, what_to_collect, example_format, where_it_lives_today, already_required_under_gpsr, espr_dpp_relevance, regulatory_note ..."),
            ("P0 example", "GTIN / EAN - EAN-13 4000000000000 - already required as product identifier"),
            ("P0 example", "Manufacturer name - legal entity name - supplier contract / ERP"),
            ("Every row", "Carries the explicit status NOT mandatory as of " + _VERIFIED),
        ],
        "faq": [
            ("Is the Digital Product Passport mandatory today?",
             "No. As of " + _VERIFIED + " category-level DPP requirements are not mandatory. The ESPR working plan is indicative, and delegated acts carry at least 18 months of transition. The battery passport has a separate hard date of 2027-02-18."),
            ("Why collect data before a legal deadline?",
             "Most P0 fields are already needed for GPSR evidence, takedown appeals and marketplace bulk uploads. Preparing them now avoids re-keying supplier data later."),
            ("Does the file claim a final product-group timetable?",
             "No. It labels the sequence as indicative and points back to official sources. It is operational guidance, not legal advice."),
        ],
        "cluster": [
            ("13-platform matrix", "/en/features/matrix"),
            ("Governance capability map", "/en/v2/govern"),
            ("13-platform rule library", "/en/rules"),
            ("EU Responsible Person guide", "/en/blog/eu-responsible-person-complete-guide"),
            ("GPSR technical file checklist", "/en/blog/gpsr-technical-file-checklist"),
        ],
        "feature": ("/en/features/matrix", "Open the 13-platform matrix"),
    },
}

RESOURCE_SLUGS = tuple(RESOURCES)
RESOURCE_PATHS = tuple("/resources/" + s for s in RESOURCE_SLUGS)
_FILE_TO_ASSET = {r["file"]: r["asset_id"] for r in RESOURCES.values()}

_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")

_CSS = """
:root{--navy:#0b1030;--ink:#0f172a;--muted:#64748b;--border:#e2e8f0;
 --blue:#2563eb;--blue-dark:#1d4ed8;--purple:#8b5cf6;--soft:#f8fafc}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Inter,"Segoe UI",system-ui,-apple-system,sans-serif;
 background:#fff;color:var(--ink);line-height:1.75}
a{text-decoration:none;color:inherit}
nav{display:flex;justify-content:space-between;align-items:center;
 padding:14px 32px;max-width:1120px;margin:0 auto}
.logo{font-weight:800;font-size:19px;display:flex;align-items:center;gap:8px}
.logo .dot{width:28px;height:28px;border-radius:8px;
 background:linear-gradient(135deg,var(--blue),var(--purple));
 display:inline-flex;align-items:center;justify-content:center;color:#fff}
.navlinks{display:flex;gap:20px;font-size:14px;font-weight:600}
.navlinks a:hover{color:var(--blue)}
.hero{background:linear-gradient(135deg,#0b1030 0%,#16204d 55%,#231457 100%);
 color:#fff;padding:52px 32px 58px}
.hero-in{max-width:860px;margin:0 auto}
.kicker{font-size:12px;letter-spacing:.08em;color:#9fb2d9;text-transform:uppercase}
.hero h1{font-size:35px;line-height:1.22;margin:14px 0 12px;letter-spacing:-.5px}
.hero p.sub{color:#cbd5e1;font-size:16px;max-width:760px}
.btn{display:inline-block;margin-top:22px;
 background:linear-gradient(135deg,var(--blue),var(--blue-dark));
 color:#fff;font-weight:700;font-size:15px;padding:13px 26px;border-radius:11px;
 box-shadow:0 8px 22px rgba(37,99,235,.35)}
.btn:hover{transform:translateY(-2px)}
.hero small{display:block;color:#9fb2d9;font-size:12.5px;margin-top:12px}
main{max-width:860px;margin:0 auto;padding:40px 28px 70px}
section{margin-top:38px}
h2{font-size:22px;letter-spacing:-.2px;margin-bottom:14px}
.answer{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.step{border:1px solid var(--border);border-radius:14px;padding:18px;background:var(--soft)}
.step b{display:block;color:var(--blue);font-size:11.5px;letter-spacing:.06em;margin-bottom:8px}
.step span{font-size:14px}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{border-bottom:1px solid var(--border);padding:11px 10px;text-align:left;vertical-align:top}
th{background:var(--soft);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
td:first-child{font-weight:700;width:34%}
.opting{border:1px solid var(--border);border-radius:14px;padding:22px;background:var(--soft)}
.opting label{display:flex;gap:10px;align-items:flex-start;font-size:14px;margin-bottom:12px}
.opting input[type=email]{width:100%;max-width:340px;padding:10px 12px;border:1px solid var(--border);
 border-radius:9px;font-size:14px;margin-right:8px}
.opting button{padding:10px 18px;border:0;border-radius:9px;background:var(--navy);
 color:#fff;font-weight:700;font-size:14px;cursor:pointer}
.opting .note,.opting .msg{display:block;color:var(--muted);font-size:12.5px;margin-top:10px}
.cluster{display:flex;flex-wrap:wrap;gap:10px}
.cluster a{border:1px solid var(--border);border-radius:999px;padding:8px 15px;
 font-size:13.5px;color:var(--blue)}
.cluster a:hover{background:var(--soft)}
.faq details{border-bottom:1px solid var(--border);padding:12px 0}
.faq summary{font-weight:700;cursor:pointer;font-size:15px}
.faq p{font-size:14px;color:#334155;margin-top:8px}
.related{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.related a{display:block;border:1px solid var(--border);border-radius:14px;padding:18px}
.related b{display:block;font-size:15px;margin-bottom:6px}
.related span{font-size:13px;color:var(--muted)}
.cta{margin-top:44px;border:1px solid var(--border);border-radius:16px;
 padding:26px;text-align:center;background:var(--soft)}
.cta b{font-size:17px}
.cta .btn{margin-top:14px;font-size:14px}
footer{border-top:1px solid var(--border);padding:24px 32px;text-align:center;
 color:var(--muted);font-size:13px}
footer a{color:var(--blue)}
@media(max-width:720px){.answer,.related{grid-template-columns:1fr}
 .hero h1{font-size:28px}.navlinks{display:none}}
"""

_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>@@TITLE@@ | CrossAIO</title>
<meta name="description" content="@@DESC@@">
<link rel="canonical" href="@@CANONICAL@@">
<link rel="alternate" hreflang="en" href="@@CANONICAL@@">
<link rel="alternate" hreflang="x-default" href="@@CANONICAL@@">
<meta property="og:type" content="article">
<meta property="og:site_name" content="CrossAIO">
<meta property="og:title" content="@@TITLE@@">
<meta property="og:description" content="@@DESC@@">
<meta property="og:url" content="@@CANONICAL@@">
@@JSONLD@@
<style>@@CSS@@</style>
</head>
<body>
<nav>
  <div class="logo"><span class="dot">&#9672;</span>CrossAIO</div>
  <div class="navlinks">
    <a href="/en/rules">Rules</a><a href="/en/features">Features</a>
    <a href="/en/sitemap">All pages</a><a href="/signup">Sign up</a>
  </div>
</nav>
<div class="hero"><div class="hero-in">
  <div class="kicker">FREE DOWNLOAD &middot; @@BRANCH@@ &middot; LAST VERIFIED @@VERIFIED@@</div>
  <h1>@@H1@@</h1>
  <p class="sub">@@DECK@@</p>
  <a class="btn" data-asset-download data-format="@@FORMAT@@" data-cta="download"
     href="@@FILE_URL@@" download>@@DOWNLOAD_EN@@</a>
  <small>@@OPTIN_NOTE_EN@@</small>
</div></div>
<main>
<section>
  <h2 data-cta="answer">@@ANSWER_EN@@</h2>
  <div class="answer">@@STEPS@@</div>
</section>
<section>
  <h2>@@PREVIEW_TITLE@@</h2>
  <table><thead><tr><th>Item</th><th>What you get</th></tr></thead>
  <tbody>@@PREVIEW_ROWS@@</tbody></table>
  <p style="font-size:13px;color:#64748b;margin-top:10px">
    File: @@FILE@@ &middot; Last verified @@VERIFIED@@ &middot; Source:
    CrossAIO 13-platform native rules library and public marketplace policy pages.</p>
</section>
<section class="opting">
  <h2>Optional: field-change updates</h2>
  <form id="optin">
    <label><input type="checkbox" id="optin-check"><span data-cta="optin">@@OPTIN_EN@@</span></label>
    <input type="email" id="optin-email" placeholder="work email (optional)" autocomplete="off">
    <button type="submit">Register interest</button>
    <span class="note" data-cta="optin_note">@@OPTIN_NOTE_EN@@</span>
    <span class="msg" id="optin-msg"></span>
  </form>
</section>
<section>
  <h2>Go deeper</h2>
  <div class="cluster">@@CLUSTER@@</div>
</section>
<section class="faq">
  <h2>FAQ</h2>
  @@FAQ@@
</section>
<section>
  <h2>Other free downloads</h2>
  <div class="related">@@RELATED@@</div>
</section>
<div class="cta"><b>Need the full workflow instead of a file?</b><br>
  <a class="btn" href="@@FEATURE_URL@@">@@FEATURE_LABEL@@ &rarr;</a></div>
<p style="font-size:13px;color:#64748b;margin-top:28px" data-cta="disclaimer">@@DISCLAIMER_EN@@</p>
</main>
<footer>CrossAIO &mdash; Listing quality and compliance tooling for European cross-border sellers.<br>
  <a href="/en/privacy">Privacy</a> &middot; <a href="/en/terms">Terms</a> &middot;
  <a href="/en/sitemap">Sitemap</a><br>
  <span data-cta="disclaimer">@@DISCLAIMER_EN@@</span></footer>
<script>
@@JS@@
</script>
</body>
</html>
"""

_JS_TEMPLATE = """(function(){
  var CTA = @@CTA_JSON@@;
  var ASSET = "@@ASSET_ID@@";
  var FMT = "@@FORMAT_UPPER@@";
  function track(type, extra){
    var meta = {asset_id: ASSET, lang: "en"};
    if (extra) { for (var k in extra) { meta[k] = extra[k]; } }
    try {
      fetch('/api/v1/analytics/track', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({event_type: type, platform: 'web', meta: meta}),
        credentials: 'same-origin',
        keepalive: true
      }).catch(function(){});
    } catch (e) {}
  }
  window.setTimeout(function(){
    if (!document.hidden) { track('asset_view'); }
  }, 3000);
  var links = document.querySelectorAll('a[data-asset-download]');
  for (var i = 0; i < links.length; i++) {
    links[i].addEventListener('click', function(){
      track('asset_download', {format: this.getAttribute('data-format')});
    });
  }
  var form = document.getElementById('optin');
  if (form) {
    form.addEventListener('submit', function(ev){
      ev.preventDefault();
      var lang = CTA[window.__ctaLang] || CTA.en;
      var msg = document.getElementById('optin-msg');
      var box = document.getElementById('optin-check');
      var email = (document.getElementById('optin-email').value || '').trim();
      if (!box.checked) { msg.textContent = lang.tick; return; }
      if (!/^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$/.test(email)) { msg.textContent = lang.badmail; return; }
      var domain = email.split('@')[1].toLowerCase();
      track('lead_capture', {opt_in: true, email_domain: domain});
      msg.textContent = lang.sent;
      form.reset();
    });
  }
  var l = (navigator.language || 'en').slice(0, 2).toLowerCase();
  window.__ctaLang = CTA[l] ? l : 'en';
  var dict = CTA[window.__ctaLang];
  var nodes = document.querySelectorAll('[data-cta]');
  for (var j = 0; j < nodes.length; j++) {
    var el = nodes[j];
    var t = dict[el.getAttribute('data-cta')];
    if (!t) { continue; }
    el.textContent = t.replace('{fmt}', FMT);
  }
})();"""


def _fill(template: str, values: dict) -> str:
    for key, value in values.items():
        template = template.replace("@@" + key + "@@", str(value))
    return template


def _jsonld(slug: str, r: dict) -> str:
    url = f"{_SITE}/en/resources/{slug}"
    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "dateModified": _VERIFIED,
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in r["faq"]
        ],
    }
    crumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "CrossAIO",
             "item": _SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Free seller downloads",
             "item": _SITE + "/en/sitemap"},
            {"@type": "ListItem", "position": 3, "name": r["title"],
             "item": url},
        ],
    }
    out = []
    for block in (faq, crumb):
        out.append('<script type="application/ld+json">\n'
                   + json.dumps(block, ensure_ascii=False, indent=1)
                   + "\n</script>")
    return "\n".join(out)


def _published_slugs() -> set:
    """Blog slugs currently published; empty set on any failure.

    Kept behind a local import so this module still renders in isolation
    (no project-internal import at module load, per the design constraints).
    An empty set drops all /en/blog/ cluster links rather than rendering 404s.
    """
    try:
        from .blog_post_pages import published_slugs
        return published_slugs()
    except Exception:
        return set()


def _page(slug: str, r: dict) -> str:
    fmt = r["format"]
    fmt_upper = fmt.upper()
    en = _CTA["en"]
    steps = "".join(
        f'<div class="step"><b>{escape(tag)}</b><span>{escape(text)}</span></div>'
        for tag, text in r["answer_steps"])
    rows = "".join(
        f"<tr><td>{escape(k)}</td><td>{escape(v)}</td></tr>"
        for k, v in r["preview_rows"])
    # 2026-11-12 internal-cluster fix: /en/blog/{s} links render only for
    # published articles, so the pages can never link a 404 article.
    pub = _published_slugs()
    cluster = "".join(
        f'<a href="{escape(href)}">{escape(label)}</a>'
        for label, href in r["cluster"]
        if not (href.startswith("/en/blog/")
                and href[len("/en/blog/"):] not in pub))
    faq = "".join(
        f"<details><summary>{escape(q)}</summary><p>{escape(a)}</p></details>"
        for q, a in r["faq"])
    related = "".join(
        f'<a href="/en/resources/{escape(other)}"><b>{escape(RESOURCES[other]["title"])}</b>'
        f'<span>Free {escape(RESOURCES[other]["format"].upper())} download &rarr;</span></a>'
        for other in RESOURCE_SLUGS if other != slug)
    feature_url, feature_label = r["feature"]
    js = _fill(_JS_TEMPLATE, {
        "CTA_JSON": json.dumps(_CTA, ensure_ascii=False),
        "ASSET_ID": r["asset_id"],
        "FORMAT_UPPER": fmt_upper,
    })
    desc = re.sub(r"\s+", " ", r["deck"])[:155]
    html = _fill(_PAGE, {
        "TITLE": escape(r["title"]),
        "DESC": escape(desc),
        "CANONICAL": f"{_SITE}/en/resources/{slug}",
        "JSONLD": _jsonld(slug, r),
        "CSS": _CSS,
        "BRANCH": escape(r["branch"]),
        "VERIFIED": _VERIFIED,
        "H1": escape(r["h1"]),
        "DECK": escape(r["deck"]),
        "FORMAT": fmt,
        "FORMAT_UPPER": fmt_upper,
        "FILE_URL": "/downloads/" + r["file"],
        "FILE": escape(r["file"]),
        "DOWNLOAD_EN": escape(en["download"].replace("{fmt}", fmt_upper)),
        "OPTIN_NOTE_EN": escape(en["optin_note"]),
        "ANSWER_EN": escape(en["answer"]),
        "OPTIN_EN": escape(en["optin"]),
        "DISCLAIMER_EN": escape(en["disclaimer"]),
        "STEPS": steps,
        "PREVIEW_TITLE": escape(r["preview_title"]),
        "PREVIEW_ROWS": rows,
        "CLUSTER": cluster,
        "FAQ": faq,
        "RELATED": related,
        "FEATURE_URL": escape(feature_url),
        "FEATURE_LABEL": escape(feature_label),
        "JS": js,
    })
    assert not _CJK_RE.search(html), "resource page must contain zero CJK characters"
    return html


def render_resource(slug: str) -> HTMLResponse:
    """Server-render one resource page; unknown slug -> 404."""
    r = RESOURCES.get(slug)
    if r is None:
        raise HTTPException(status_code=404)
    return HTMLResponse(_page(slug, r), headers=_NO_CACHE)


def serve_download(filename: str) -> FileResponse:
    """Whitelisted static asset. No database, no email, no redirect."""
    if _FILE_TO_ASSET.get(filename) is None:
        raise HTTPException(status_code=404)
    path = Path(__file__).parent / "static" / "downloads" / filename
    if not path.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(path, filename=filename, headers=_NO_CACHE)
