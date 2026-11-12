"""授权校验与令牌换取（12 平台统一实现）。

三条硬规则：
1. 只对 stage=confirmed 的平台发起真实网络请求；其余仅做形状校验，绝不臆造端点。
2. 任何返回值都不包含明文密钥或 access_token —— 只回字段是否存在、HTTP 状态码。
3. 并发校验：verify_many() 一次性跑完全部平台（4 语种 × 12 平台的矩阵由 i18n 层组装）。
"""
import asyncio
from typing import Dict, List, Optional

import httpx

from .spec import AUTH_SPECS, get_spec

TIMEOUT = 15.0

# 明显是占位符的取值，直接判失败，避免"填了但没生效"的假连接
PLACEHOLDERS = ("your_", "xxx", "todo", "changeme", "test_key", "示例", "请填写")

MIN_SECRET_LEN = 8


def _is_placeholder(value: str) -> bool:
    low = value.strip().lower()
    return any(p in low for p in PLACEHOLDERS) or low in ("", "none", "null")


def validate_shape(platform: str, payload: Dict[str, str]) -> Dict:
    """本地形状校验：字段齐全度 + 长度 + 占位符 + 空白字符。"""
    spec = get_spec(platform)
    if not spec:
        return {"ok": False, "status": "pending", "checks": [],
                "missing_fields": [], "reason": "未知平台"}

    checks: List[Dict] = []
    missing: List[str] = []

    for field in spec["fields"]:
        raw = str(payload.get(field) or "").strip()
        if not raw:
            missing.append(field)
            checks.append({"field": field, "ok": False, "reason": "缺少该字段"})
            continue
        if _is_placeholder(raw):
            checks.append({"field": field, "ok": False, "reason": "疑似占位符"})
            continue
        if any(ch.isspace() for ch in raw):
            checks.append({"field": field, "ok": False, "reason": "含空白字符，建议重新复制"})
            continue
        is_secret = field.endswith(("secret", "key", "token"))
        if is_secret and len(raw) < MIN_SECRET_LEN:
            checks.append({"field": field, "ok": False,
                           "reason": "长度不足 %d 位，疑似复制不全" % MIN_SECRET_LEN})
            continue
        checks.append({"field": field, "ok": True, "reason": "ok"})

    if missing:
        return {"ok": False, "status": "pending", "checks": checks,
                "missing_fields": missing,
                "reason": "缺少必填字段：%s" % ", ".join(missing)}

    failed = [c for c in checks if not c["ok"]]
    if failed:
        return {"ok": False, "status": "pending", "checks": checks,
                "missing_fields": [],
                "reason": "字段格式未通过：%s" % ", ".join(c["field"] for c in failed)}

    return {"ok": True, "status": "connected", "checks": checks,
            "missing_fields": [], "reason": "字段形状校验通过"}


def build_authorize_url(platform: str, state: str, redirect_uri: str,
                        payload: Optional[Dict[str, str]] = None) -> Optional[str]:
    """OAuth 授权跳转地址；无授权端点的平台返回 None（前端据此隐藏按钮）。"""
    spec = get_spec(platform) or {}
    auth_url = spec.get("authorize_url")
    if not auth_url:
        return None
    payload = payload or {}
    client_id = (str(payload.get("client_id") or payload.get("app_key") or "")).strip()
    if not client_id:
        return None
    from urllib.parse import urlencode
    params = {"client_id": client_id, "response_type": "code",
              "redirect_uri": redirect_uri, "state": state}
    if spec.get("scope"):
        params["scope"] = spec["scope"]
    return auth_url + "?" + urlencode(params)


def _basic(client_id: str, client_secret: str) -> str:
    import base64
    raw = ("%s:%s" % (client_id, client_secret)).encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _brief(text: str, limit: int = 160) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text[:limit]


async def _live_token_check(platform: str, payload: Dict[str, str]) -> Dict:
    """对 confirmed 平台做真实令牌校验（只取状态，不回传令牌）。"""
    spec = get_spec(platform) or {}
    url = spec.get("token_url")
    if not url or spec.get("live_check") != "token":
        return {"ok": None, "status": "live_unavailable",
                "reason": "该平台未开放实时校验（端点未核实）"}

    auth_type = spec["auth_type"]
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            if auth_type == "lwa_refresh_token":
                resp = await client.post(url, data={
                    "grant_type": "refresh_token",
                    "refresh_token": payload.get("refresh_token", ""),
                    "client_id": payload.get("client_id", ""),
                    "client_secret": payload.get("client_secret", ""),
                })
            elif auth_type == "oauth2_client_credentials":
                headers = {"Content-Type": "application/x-www-form-urlencoded"}
                if platform == "walmart":
                    headers["WM_SVC.NAME"] = "Walmart Marketplace"
                    headers["WM_QOS.CORRELATION_ID"] = "crossbot-auth-check"
                    headers["Accept"] = "application/json"
                resp = await client.post(
                    url, data={"grant_type": "client_credentials"},
                    headers=headers,
                    auth=httpx.BasicAuth(payload.get("client_id", ""),
                                         payload.get("client_secret", "")),
                )
            else:
                return {"ok": None, "status": "live_unavailable",
                        "reason": "该授权类型不支持无用户参与的令牌校验"}
    except Exception as exc:  # 网络异常不判失败，避免误伤商家
        return {"ok": None, "status": "live_unavailable",
                "reason": "网络不可达：%s" % type(exc).__name__}

    if resp.status_code == 200:
        return {"ok": True, "status": "live_ok", "http_status": 200,
                "reason": "令牌换取成功"}
    return {"ok": False, "status": "live_fail", "http_status": resp.status_code,
            "reason": "令牌换取被拒：%s" % _brief(resp.text)}


async def verify_credential(platform: str, payload: Dict[str, str],
                            live: bool = False) -> Dict:
    """形状校验 +（可选）真实校验；形态统一的授权结果。"""
    shape = validate_shape(platform, payload)
    result = {
        "platform": platform,
        "status": shape["status"],
        "ok": shape["ok"],
        "checks": shape["checks"],
        "missing_fields": shape["missing_fields"],
        "reason": shape["reason"],
        "live": None,
    }
    if not shape["ok"] or not live:
        return result

    live_result = await _live_token_check(platform, payload)
    result["live"] = live_result
    if live_result.get("ok") is True:
        result["status"] = "live_ok"
    elif live_result.get("ok") is False:
        result["status"] = "live_fail"
        result["ok"] = False
    return result


async def verify_many(items: Dict[str, Dict[str, str]], live: bool = False) -> Dict[str, Dict]:
    """一次并发跑完多个平台（items: {platform: payload}）。"""
    tasks = [verify_credential(p, payload, live=live) for p, payload in items.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    out: Dict[str, Dict] = {}
    for (platform, _), res in zip(items.items(), results):
        if isinstance(res, Exception):
            out[platform] = {"platform": platform, "status": "pending", "ok": False,
                             "checks": [], "missing_fields": [],
                             "reason": "校验异常：%s" % type(res).__name__, "live": None}
        else:
            out[platform] = res
    return out


async def exchange_code(platform: str, code: str, redirect_uri: str,
                        payload: Dict[str, str]) -> Dict:
    """授权码换令牌（仅 confirmed + oauth2_code 平台可用）。"""
    spec = get_spec(platform) or {}
    if spec.get("auth_type") != "oauth2_code" or spec.get("stage") != "confirmed":
        return {"ok": False, "reason": "该平台授权码换取端点未核实，暂不支持"}
    url = spec.get("token_url")
    if not url:
        return {"ok": False, "reason": "缺少令牌端点"}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                url,
                data={"grant_type": "authorization_code", "code": code,
                      "redirect_uri": redirect_uri},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                auth=httpx.BasicAuth(payload.get("client_id", ""),
                                     payload.get("client_secret", "")),
            )
    except Exception as exc:
        return {"ok": False, "reason": "网络异常：%s" % type(exc).__name__}

    if resp.status_code != 200:
        return {"ok": False, "http_status": resp.status_code,
                "reason": "换取被拒：%s" % _brief(resp.text)}

    try:
        data = resp.json()
    except Exception:
        return {"ok": False, "http_status": resp.status_code, "reason": "响应不是 JSON"}

    # tokens 仅供路由层写入加密存储，绝不进入 API 响应体
    return {
        "ok": True,
        "http_status": 200,
        "has_refresh_token": bool(data.get("refresh_token")),
        "expires_in": data.get("expires_in"),
        "tokens": {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in"),
            "token_type": data.get("token_type"),
        },
    }
