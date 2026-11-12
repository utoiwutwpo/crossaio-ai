"""用户注册 / 登录 / 信息（含 Google OAuth 登录、忘记密码）"""
import base64
import hashlib
import hmac
import secrets
import time
import uuid
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db, User
from ..schemas import UserCreate, UserLogin, GoogleAuthRequest, TokenResponse, UserOut
from ..auth import hash_password, verify_password, create_access_token, get_current_user
from ..billing import plan_config, usage_today
from .analytics import track_event

router = APIRouter()


@router.post("/register", response_model=TokenResponse, summary="注册并直接登录")
def register(
    body: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    utm_source: Optional[str] = None,
    utm_medium: Optional[str] = None,
    utm_campaign: Optional[str] = None,
):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="该邮箱已注册")
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name or "",
        company_name=body.company_name or "",
        plan="free",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    # 验证闭环埋点：signup + 渠道归因（utm 从前端注册表单/落地页带来）
    track_event(db, "signup", request, user_id=user.id,
                utm_source=utm_source, utm_medium=utm_medium,
                utm_campaign=utm_campaign)
    cfg = plan_config(user.plan)
    return TokenResponse(
        access_token=create_access_token(user.id),
        plan=user.plan,
        usage_today=0,
        daily_limit=cfg["daily_limit"],
    )


@router.post("/login", response_model=TokenResponse, summary="登录")
def login(body: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    cfg = plan_config(user.plan)
    return TokenResponse(
        access_token=create_access_token(user.id),
        plan=user.plan,
        usage_today=usage_today(db, user.id),
        daily_limit=cfg["daily_limit"],
    )


@router.get("/me", response_model=UserOut, summary="当前用户信息")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cfg = plan_config(user.plan)
    return UserOut(
        id=user.id, email=user.email, full_name=user.full_name,
        company_name=user.company_name, plan=user.plan,
        created_at=user.created_at,
        usage_today=usage_today(db, user.id),
        daily_limit=cfg["daily_limit"],
    )


# ---------- Google 登录（Sign up / Log in with Google） ----------

# ===== 共用：ID token 服务端校验 + 按邮箱登录/注册 =====
async def _google_user_from_idtoken(credential: str) -> dict:
    """服务端校验 Google id_token（tokeninfo 验签 + exp + aud + email_verified），返回信息 dict。"""
    try:
        async with httpx.AsyncClient(timeout=10, proxy=settings.proxy_url or None) as client:
            r = await client.get("https://oauth2.googleapis.com/tokeninfo",
                                 params={"id_token": credential})
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="无法连接 Google 校验服务，请稍后再试")
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Google 凭证无效或已过期")
    info = r.json()
    if info.get("aud") != settings.google_client_id:
        raise HTTPException(status_code=401, detail="Google 凭证与本站不匹配（aud 校验失败）")
    if info.get("email_verified") not in ("true", True):
        raise HTTPException(status_code=401, detail="Google 邮箱未验证")
    return info


def _google_login_or_register(db: Session, info: dict) -> User:
    """同邮箱自动关联老账号；新邮箱自动注册（free 档，密码置为不可用的随机串）。"""
    email = info["email"]
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            password_hash=hash_password(uuid.uuid4().hex + uuid.uuid4().hex),
            full_name=info.get("name", ""),
            plan="free",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@router.get("/google-config", summary="Google 登录可用性与前端 Client ID")
def google_config():
    """未配置 GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET 时 enabled=false，前端按钮给出引导提示而非报错。"""
    return {"enabled": bool(settings.google_client_id and settings.google_client_secret),
            "client_id": settings.google_client_id}


@router.post("/google", response_model=TokenResponse, summary="Google ID token 登录/注册（GIS 弹窗，自动关联同邮箱账号）")
async def google_auth(body: GoogleAuthRequest, db: Session = Depends(get_db)):
    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google 登录未启用：请在 backend/.env 配置 GOOGLE_CLIENT_ID")
    info = await _google_user_from_idtoken(body.credential)
    user = _google_login_or_register(db, info)
    cfg = plan_config(user.plan)
    return TokenResponse(
        access_token=create_access_token(user.id),
        plan=user.plan,
        usage_today=usage_today(db, user.id),
        daily_limit=cfg["daily_limit"],
    )


# ===== OAuth2 授权码流程（服务端，使用 Client Secret；主登录方式） =====
# 入口与回调共用 GET /users/google（顶层路径，redirect_uri 与 Google 控制台登记一致）：
#   1) 无 code 参数 → 构造 Google 授权 URL 并 302 跳转（state 签名后存 HttpOnly Cookie）
#   2) 带 code 参数 → code+secret 换 id_token → 校验 → 登录/注册 → 带 token 回跳 /app
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

oauth_router = APIRouter()   # main.py 以无前缀方式挂载，回调路径 = {APP_URL}/users/google


def _google_redirect_uri() -> str:
    return settings.app_url.rstrip("/") + "/users/google"


def _sign_state(payload: str) -> str:
    return hmac.new(settings.jwt_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _validate_next(next_url: str) -> str:
    """只允许站内相对路径，防开放重定向。"""
    if not next_url.startswith("/") or next_url.startswith("//") or "://" in next_url:
        return "/app"
    return next_url


@oauth_router.get("/users/google", include_in_schema=False)
async def google_oauth_flow(request: Request, response: Response,
                            db: Session = Depends(get_db)):
    if not (settings.google_client_id and settings.google_client_secret):
        raise HTTPException(
            status_code=501,
            detail="Google 登录未启用：请在 backend/.env 配置 GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET")

    code = request.query_params.get("code")
    if not code:
        # ---- 入口：跳转 Google 授权页 ----
        next_url = _validate_next(request.query_params.get("next") or "/app")
        state = secrets.token_urlsafe(24)
        payload = f"{next_url}|{state}"
        signed = f"{payload}.{_sign_state(payload)}"
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": _google_redirect_uri(),
            "response_type": "code",
            "scope": "openid email profile",
            "prompt": "select_account",
            "state": state,
        }
        redirect = RedirectResponse(GOOGLE_AUTH_URL + "?" + urlencode(params))
        # secure 动态判断：https 请求（含 cloudflared 的 X-Forwarded-Proto）才加 Secure，
        # 否则用户经 http（如 Tailscale IP / localhost）访问时 cookie 不回传 → state 校验必挂
        _https = (request.url.scheme == "https"
                  or request.headers.get("x-forwarded-proto", "") == "https")
        redirect.set_cookie("cb_oauth_state", signed, max_age=1800, httponly=True,
                            samesite="lax", secure=_https)
        return redirect

    # ---- 回调：校验 state → code 换 id_token → 登录/注册 → 回跳 ----
    state_param = request.query_params.get("state", "")
    raw = request.cookies.get("cb_oauth_state", "")
    payload, _, mac = raw.rpartition(".")
    if not payload or not hmac.compare_digest(_sign_state(payload), mac):
        raise HTTPException(status_code=400, detail="OAuth state 校验失败，请重新发起登录")
    next_url, _, state_in_cookie = payload.partition("|")
    if not secrets.compare_digest(state_in_cookie, state_param):
        raise HTTPException(status_code=400, detail="OAuth state 不匹配，请重新发起登录")

    try:
        async with httpx.AsyncClient(timeout=10, proxy=settings.proxy_url or None) as client:
            r = await client.post(GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": _google_redirect_uri(),
                "grant_type": "authorization_code",
            })
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="无法连接 Google 换取凭证，请稍后再试")
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Google 授权码无效或已过期")
    id_token = (r.json() or {}).get("id_token")
    if not id_token:
        raise HTTPException(status_code=401, detail="Google 未返回有效身份凭证")

    info = await _google_user_from_idtoken(id_token)
    user = _google_login_or_register(db, info)

    next_url = _validate_next(next_url)
    sep = "&" if "?" in next_url else "?"
    target = f"{next_url}{sep}token={create_access_token(user.id)}"
    redirect = RedirectResponse(target)
    redirect.delete_cookie("cb_oauth_state", path="/")
    return redirect


# ---------- 忘记密码 / 重置密码 ----------
# 令牌用 HMAC 签名，不落库：
#   payload = user_id|exp|密码指纹(sha256(password_hash)[:16])
#   密码一改，指纹变 → 旧链接立即失效（天然一次性）
_RESET_TTL_SECONDS = 1800


def _pw_fingerprint(user: User) -> str:
    return hashlib.sha256(user.password_hash.encode()).hexdigest()[:16]


def _reset_token(user: User) -> str:
    payload = f"{user.id}|{int(time.time()) + _RESET_TTL_SECONDS}|{_pw_fingerprint(user)}"
    sig = hmac.new(settings.jwt_secret.encode(), ("pwreset|" + payload).encode(),
                   hashlib.sha256).hexdigest()[:32]
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=") + "." + sig


def _read_reset_token(token: str) -> tuple:
    """校验签名与过期，返回 (user_id, 密码指纹)。失败抛 400。"""
    try:
        raw, sig = token.split(".", 1)
        payload = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode()
    except Exception:
        raise HTTPException(status_code=400, detail="重置链接无效")
    expect = hmac.new(settings.jwt_secret.encode(), ("pwreset|" + payload).encode(),
                      hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(expect, sig):
        raise HTTPException(status_code=400, detail="重置链接无效")
    parts = payload.split("|")
    if len(parts) != 3:
        raise HTTPException(status_code=400, detail="重置链接无效")
    uid, exp, fp = parts
    try:
        if int(exp) < int(time.time()):
            raise HTTPException(status_code=400, detail="重置链接已过期，请重新申请")
    except ValueError:
        raise HTTPException(status_code=400, detail="重置链接无效")
    return uid, fp


RESET_TEXT = {
    "zh": {
        "subject": "重置你的 CrossAIO 密码",
        "hello": "你正在重置 CrossAIO 账号的登录密码。",
        "btn": "设置新密码",
        "note": "链接 30 分钟内有效，且只能使用一次。若不是你本人操作，忽略这封邮件即可。",
        "foot": "CrossAIO · 跨境电商合规工作台",
    },
    "en": {
        "subject": "Reset your CrossAIO password",
        "hello": "You asked to reset the password for your CrossAIO account.",
        "btn": "Set a new password",
        "note": "This link expires in 30 minutes and works once. If you didn't ask for it, ignore this email.",
        "foot": "CrossAIO · cross-border compliance workbench",
    },
    "de": {
        "subject": "Setze dein CrossAIO-Passwort zurück",
        "hello": "Du hast angefordert, das Passwort für dein CrossAIO-Konto zurückzusetzen.",
        "btn": "Neues Passwort setzen",
        "note": "Der Link ist 30 Minuten gültig und nur einmal verwendbar. Falls du das nicht warst, ignoriere diese E-Mail.",
        "foot": "CrossAIO · Compliance-Workbench für den EU-Handel",
    },
    "fr": {
        "subject": "Réinitialisez votre mot de passe CrossAIO",
        "hello": "Vous avez demandé à réinitialiser le mot de passe de votre compte CrossAIO.",
        "btn": "Définir un nouveau mot de passe",
        "note": "Ce lien expire dans 30 minutes et ne fonctionne qu'une fois. Si vous n'êtes pas à l'origine de la demande, ignorez cet e-mail.",
        "foot": "CrossAIO · poste de travail conformité UE",
    },
}


async def _send_reset_email(to: str, link: str, lang: str) -> bool:
    """优先 Resend HTTP API，其次 SMTP；都未配置则返回 False（不报错）。"""
    t = RESET_TEXT.get(lang) or RESET_TEXT["en"]
    html = f"""<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:560px;margin:0 auto;padding:24px;color:#0f172a">
  <div style="font-weight:800;font-size:18px;margin-bottom:18px">CrossAIO</div>
  <p style="font-size:15px;line-height:1.7">{t['hello']}</p>
  <p style="margin:26px 0">
    <a href="{link}" style="background:linear-gradient(90deg,#3b82f6,#8b5cf6);color:#fff;text-decoration:none;padding:13px 26px;border-radius:999px;font-weight:700;display:inline-block">{t['btn']}</a>
  </p>
  <p style="font-size:13px;color:#64748b;line-height:1.7">{t['note']}</p>
  <p style="font-size:12px;color:#94a3b8;margin-top:26px;border-top:1px solid #e2e8f0;padding-top:14px">{t['foot']}</p>
</div>"""
    if settings.resend_api_key:
        try:
            async with httpx.AsyncClient(timeout=15, proxy=settings.proxy_url or None) as client:
                r = await client.post("https://api.resend.com/emails",
                                      headers={"Authorization": f"Bearer {settings.resend_api_key}",
                                               "Content-Type": "application/json"},
                                      json={"from": settings.resend_from, "to": [to],
                                            "subject": t["subject"], "html": html})
            return r.status_code in (200, 201)
        except Exception:
            return False
    if settings.smtp_host:
        from ..mailer import send_email
        try:
            return bool(send_email(to, t["subject"], html))
        except Exception:
            return False
    return False


@router.get("/mail-status", summary="邮件发送通道是否已配置（不含任何密钥）")
def mail_status():
    if settings.resend_api_key:
        return {"configured": True, "channel": "resend", "from": settings.resend_from}
    if settings.smtp_host:
        return {"configured": True, "channel": "smtp", "from": settings.smtp_from or settings.smtp_user}
    return {"configured": False, "channel": "", "from": ""}


@router.post("/password/forgot", summary="发送重置密码邮件")
async def password_forgot(body: dict, db: Session = Depends(get_db)):
    email = (body.get("email") or "").strip().lower()
    lang = (body.get("lang") or "en")[:2]
    if lang not in ("zh", "en", "de", "fr"):
        lang = "en"
    generic = {"ok": True, "mail_configured": bool(settings.resend_api_key or settings.smtp_host)}
    if not email or "@" not in email:
        return generic                      # 不泄露账号是否存在
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return generic
    token = _reset_token(user)
    link = f"{settings.public_url}/{'' if lang == 'zh' else lang + '/'}reset?token={token}"
    sent = await _send_reset_email(user.email, link, lang)
    return {"ok": True, "mail_configured": bool(settings.resend_api_key or settings.smtp_host), "sent": sent}


@router.post("/password/reset", summary="用令牌设置新密码")
def password_reset(body: dict, db: Session = Depends(get_db)):
    token = (body.get("token") or "").strip()
    pw = body.get("password") or ""
    if len(pw) < 8:
        raise HTTPException(status_code=400, detail="密码至少 8 位")
    uid, fp = _read_reset_token(token)
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=400, detail="重置链接无效")
    if not hmac.compare_digest(fp, _pw_fingerprint(user)):
        raise HTTPException(status_code=400, detail="重置链接已使用，请重新申请")
    user.password_hash = hash_password(pw)
    db.commit()
    return {"ok": True}
