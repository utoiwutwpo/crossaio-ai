"""POST /api/v1/leads - answer-then-ask subscription, no automated email.

Why a new endpoint instead of /api/v1/newsletter/subscribe:
  that router sends a Chinese-language confirmation email as soon as SMTP_HOST
  is set. The EU-facing page must never trigger an unsolicited email, and every
  user-facing string on this path is English.

Attribution: every successful write also emits
  - an AnalyticsEvent("lead_capture") with utm_* resolved from query /
    caio_attr cookie / Referer, so channels[].leads can be judged per channel;
  - one structured JSON line to stdout (Render logs), with an email hash and
    domain only, never the address in plaintext. That line survives a deploy
    that clears the ephemeral SQLite volume.

GDPR: explicit unticked consent, one-click unsubscribe, hashed IP, no resale.
"""
import hashlib
import json
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..lead_models import RuleAlertLead
from .analytics import _fallback_utm, ip_hash, track_event

router = APIRouter()
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,}$")
UTM_CONTENT_MAX = 100


class LeadIn(BaseModel):
    email: str = Field(..., max_length=255)
    opt_in: bool = Field(default=False)
    lang: str = Field(default="en", max_length=10)
    page: str = Field(default="", max_length=200)
    source: str = Field(default="answer-then-ask", max_length=50)
    utm_content: str = Field(default="", max_length=UTM_CONTENT_MAX)


def _cookie(request: Request, name: str) -> str:
    return (request.cookies.get(name) or "")[:64]


def _structured_log(row: RuleAlertLead, utm: dict, state: str, domain: str,
                    request: Request) -> None:
    """One JSON line per write; stdout is captured by Render logs."""
    payload = {
        "event": "lead_capture",
        "ts": datetime.utcnow().isoformat() + "Z",
        "state": state,
        "lead_id": row.id,
        "email_sha256": row.email_sha256,
        "email_domain": domain,
        "channel": (row.utm_source or "direct"),
        "utm_source": row.utm_source,
        "utm_medium": row.utm_medium,
        "utm_campaign": row.utm_campaign,
        "utm_content": row.utm_content,
        "page": row.page,
        "lang": row.lang,
        "caio_vid": row.caio_vid,
        "ip_hash": row.ip_hash,
    }
    # Never print the raw email address into logs.
    print("CROSSAIO_LEAD " + json.dumps(payload, ensure_ascii=False, sort_keys=True),
          flush=True)


@router.post("", summary="Subscribe to EU rule-change alerts (no automated email)")
def create_lead(payload: LeadIn, request: Request, db: Session = Depends(get_db)):
    email = (payload.email or "").strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Please enter a valid work email.")
    if not payload.opt_in:
        raise HTTPException(status_code=400,
                            detail="Consent is required before we store your address.")

    utm = _fallback_utm(request) or {}
    utm_content = (payload.utm_content or request.query_params.get("utm_content")
                   or "")[:UTM_CONTENT_MAX]
    domain = email.rsplit("@", 1)[-1][:190]
    digest = hashlib.sha256(email.encode("utf-8")).hexdigest()

    row = db.query(RuleAlertLead).filter(RuleAlertLead.email == email).first()
    if row is not None:
        # Idempotent. Do NOT re-enable an unsubscribed address automatically.
        state = "unsubscribed" if row.unsubscribed else "exists"
        _structured_log(row, utm, state, domain, request)
        return {"ok": True, "state": state,
                "unsubscribe_url": "/api/v1/leads/unsubscribe?token=" + str(row.id),
                "message": "This address is already on the list. No email is sent."}

    row = RuleAlertLead(
        email=email,
        email_sha256=digest,
        source=(payload.source or "answer-then-ask")[:50],
        lang=(payload.lang or "en")[:10],
        page=(payload.page or "")[:200],
        utm_source=(utm.get("utm_source") or "")[:100],
        utm_medium=(utm.get("utm_medium") or "")[:100],
        utm_campaign=(utm.get("utm_campaign") or "")[:100],
        utm_content=utm_content,
        caio_vid=_cookie(request, "caio_vid"),
        ip_hash=ip_hash(request),
        opt_in=True,
        unsubscribed=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    state = "created"

    # Channel-attributable analytics event; only for a genuinely new lead so a
    # double submit cannot inflate the commercial verdict.
    track_event(db, "lead_capture", request, platform="web",
                utm_source=row.utm_source or None,
                utm_medium=row.utm_medium or None,
                utm_campaign=row.utm_campaign or None,
                meta={"opt_in": True, "email_domain": domain,
                      "page": row.page, "lang": row.lang,
                      "utm_content": row.utm_content,
                      "caio_vid": row.caio_vid,
                      "source": row.source})
    _structured_log(row, utm, state, domain, request)

    return {"ok": True, "state": state,
            "unsubscribe_url": "/api/v1/leads/unsubscribe?token=" + str(row.id),
            "message": "You are on the list. No automated email is sent."}


@router.get("/unsubscribe", summary="One-click unsubscribe", response_class=HTMLResponse)
def unsubscribe(token: str = Query(..., min_length=8, max_length=64),
                db: Session = Depends(get_db)):
    row = db.query(RuleAlertLead).filter(RuleAlertLead.id == token).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Subscription not found.")
    row.unsubscribed = True
    db.commit()
    return HTMLResponse(
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<title>Unsubscribed | CrossAIO</title>"
        "<body style='font-family:system-ui;max-width:560px;margin:60px auto;"
        "line-height:1.7'><h1>You have been unsubscribed</h1>"
        "<p>You will no longer receive CrossAIO rule-change alerts. "
        "No further email will be sent.</p>"
        "<p><a href='/en/blog/error-5995-fix'>Back to the Error 5995 guide</a></p>"
        "</body></html>")
