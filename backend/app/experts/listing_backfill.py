"""
GPSR 合规块「一键回填 Listing」平台适配层

gpsr_block_text 已能生成合规块文本；本模块把它转成各平台 API 可提交的
结构化 payload（回填字段 + 所需 API + 鉴权方式），实现「一键回填」的适配层。

⚠️ 真实写入需对应平台凭证（Amazon SP-API / eBay OAuth 等），须在服务端
安全存储后联调。本模块只负责生成「待回填请求体」与适配信息，不发起任何
外部 HTTP 调用。
"""
import json
import os
import datetime
import hashlib
import hmac
import urllib.request
import urllib.parse
from typing import Dict, List, Optional

import requests

from . import gpsr
from .platform_registry import platform_config

# 各平台回填目标字段 + API 参考 + 鉴权方式（工程默认，以官方最新文档为准）
_BACKFILL_TARGETS: Dict[str, Dict] = {
    "amazon": {
        "field": "product_description / A+ Content（合规块贴入描述或 A+ 模块）",
        "api": "Selling Partner API — PATCH /listings/2021-08-01/items/{sku}",
        "auth": "LWA + AWS SigV4（需 SP-API 开发者账号 + 合规读写权限）",
    },
    "amazon_us": {
        "field": "product_description（美国站无 GPSR 强制，但建议保留安全信息）",
        "api": "Selling Partner API — PATCH /listings/2021-08-01/items/{sku}",
        "auth": "LWA + AWS SigV4",
    },
    "ebay": {
        "field": "Item.Description（支持 HTML，合规块以 HTML 段落回填）",
        "api": "Trading API Add/ReviseItem 或 Bulk Data Exchange",
        "auth": "OAuth2（eBay Developer Program）",
    },
    "otto": {
        "field": "productDescription（德文）",
        "api": "Otto Partner API — PATCH /v1/products/{sku}",
        "auth": "API Key（合作者账号）",
    },
    "allegro": {
        "field": "description（波兰文，支持 HTML）",
        "api": "Allegro REST API — PATCH /sale/product-offers/{id}",
        "auth": "Bearer Token（OAuth2）",
    },
    "emag": {
        "field": "description（罗马尼亚文）",
        "api": "eMAG Marketplace API — product.save",
        "auth": "API Key（厂商账号）",
    },
    "kaufland": {
        "field": "description（德文）",
        "api": "Kaufland Global API — PATCH /seller-api/v2/offers/{id}",
        "auth": "API Token",
    },
    "bol": {
        "field": "description（荷兰文）",
        "api": "bol.com Retailer API — PUT /retailer/offers/{id}",
        "auth": "OAuth2（Client Credentials）",
    },
    "cdiscount": {
        "field": "Description（法文，长描述）",
        "api": "Cdiscount Marketplace API — Offer.SubmitOffer",
        "auth": "Token（厂商账号）",
    },
    "zalando": {
        "field": "productDescription（英文主目录，平台按站点本地化）",
        "api": "zDirect API — PATCH /products/{id}",
        "auth": "OAuth2（Partner 审核后）",
    },
    "tiktok": {
        "field": "product_detail / description（英文内容，平台本地化）",
        "api": "TikTok Shop API — POST /product/update",
        "auth": "App Key + Sign（开放平台）",
    },
    "fruugo": {
        "field": "description（英文主目录，平台自动翻译）",
        "api": "Fruugo Product API — product/update",
        "auth": "API Key",
    },
    "walmart": {
        "field": "productDescription（英文）",
        "api": "Walmart Marketplace API — PUT /v3/items/{sku}",
        "auth": "Client ID + Client Secret (Signature)",
    },
}


def backfill_target(platform: str) -> Dict:
    """返回该平台的回填目标字段 / API / 鉴权信息；未知平台回落通用。"""
    return _BACKFILL_TARGETS.get(platform, {
        "field": "description（平台默认描述字段）",
        "api": "platform-specific listing update API",
        "auth": "TBD（需该平台开发者凭证）",
    })


def build_backfill_payload(platform: str, product_name: str,
                           keywords: List[str],
                           eu_rep_line: str = "") -> Dict:
    """生成 GPSR 合规块 + 该平台回填适配信息（待真实 API 写入）。

    eu_rep_line: 欧代单行文本（来自 eu_rep.render_rep_line），传入则合规块内嵌真实欧代。
    """
    platform_config(platform)  # 校验平台合法性，未知则抛 KeyError
    report = gpsr.check(product_name, keywords, platform, eu_rep_line=eu_rep_line)
    categories = gpsr.detect_categories(product_name, keywords)
    languages = report["required_languages"]
    block = gpsr.gpsr_block_text(
        platform, categories, languages, product_name, eu_rep_line=eu_rep_line)
    target = backfill_target(platform)
    return {
        "platform": platform,
        "product_name": product_name,
        "risk_level": report["risk_level"],
        "ce_required": report["ce_required"],
        "required_languages": languages,
        "gpsr_block": block,
        "backfill": {
            "target_field": target["field"],
            "api_reference": target["api"],
            "auth_required": target["auth"],
            "content": block,
        },
        "auth_required": True,
        "note": ("本端点生成待回填的 GPSR 合规块（已内嵌欧代真实信息）与平台 API 适配信息；"
                 "真实写入需对应平台凭证（SP-API / OAuth 等），"
                 "须在服务端安全存储后联调。"),
    }


# ===================================================================
# 真实写回（凭证接线层）：凭证就绪即可联调；默认 dry-run，无凭证返回 blocked
# ===================================================================
def get_credentials(platform: str) -> Dict:
    """从环境变量读取该平台的回填凭证；未配置返回 None（即「待用户接入」）。

    命名约定：CROSSBOT_CRED_<PLATFORM>_<KEY>
      例：CROSSBOT_CRED_AMAZON_CLIENT_ID / CROSSBOT_CRED_AMAZON_CLIENT_SECRET
          CROSSBOT_CRED_EBAY_OAUTH_TOKEN
    凭证在部署环境（.env / 密钥管理）安全存储，切勿写入代码或提交仓库。
    """
    prefix = "CROSSBOT_CRED_" + platform.upper() + "_"
    creds = {k[len(prefix):].lower(): v for k, v in os.environ.items() if k.startswith(prefix)}
    return creds or None


def submit_backfill_payload(platform: str, payload: Dict, dry_run: bool = True) -> Dict:
    """把 build_backfill_payload 生成的合规块真实写回平台 listing。

    流程：
      1. 取凭证；无凭证 → 返回 credentials_required（即「待用户接入」）。
      2. 有凭证 → 按 backfill_target 的 api/auth 构造请求体。
      3. dry_run=True（默认，本环境）→ 只返回准备好的请求，不联网。
      4. dry_run=False + 有凭证 → 真实发起 HTTP 写回（须用户显式开启）。

    ⚠️ 真实写回使用各平台官方 endpoint + 鉴权（见 _REAL_ENDPOINTS / real_submit）。
    本环境默认 dry_run，不会联网；仅当部署环境配置凭证且调用方显式
    dry_run=False 时才真正写回。
    """
    creds = get_credentials(platform)
    if not creds:
        return {
            "status": "credentials_required",
            "platform": platform,
            "message": ("尚未配置该平台回填凭证（环境变量 CROSSBOT_CRED_<PLATFORM>_*）。"
                        "提供后可将合规块自动写回 listing，无需手工粘贴。"),
            "backfill": payload.get("backfill"),
        }
    if dry_run:
        req = _build_real_request(platform, payload, creds, live=False)
        return {
            "status": "ready_to_send",
            "platform": platform,
            "dry_run": True,
            "request": req,
            "message": "凭证就绪，未实际发送（dry_run=True）。置 dry_run=False 即真实写回 listing。",
        }
    # 真实发送（仅在有凭证且用户明确要求 dry_run=False 时）
    try:
        resp = real_submit(platform, payload, creds)
        return {
            "status": "submitted",
            "platform": platform,
            "http_status": resp.status_code,
            "response": resp.text[:500],
        }
    except Exception as e:  # noqa: BLE001 — 联调期网络/鉴权错误原样回传
        return {"status": "send_failed", "platform": platform, "error": str(e)}


# ===================================================================
# 真实写回：各平台官方 endpoint + 鉴权（requests 发起）
# ===================================================================

# 真实可写 endpoint（与 backfill_target 的"API 参考"对应，但这里是真实 URL）。
# 区域按欧洲站默认；多区域卖家按目标 marketplace 调整。
_REAL_ENDPOINTS: Dict[str, str] = {
    "ebay": "https://api.ebay.com/sell/inventory/v1/inventory_item",  # + /{sku}
    "amazon": "https://sellingpartnerapi-eu.amazon.com/listings/2021-08-01/items",  # + /{sku}
    "amazon_us": "https://sellingpartnerapi-na.amazon.com/listings/2021-08-01/items",
}

# 真实写回支持的平台（其余平台暂走凭证+手动回填，标注于 backfill_target）
_REAL_SUBMIT_PLATFORMS = set(_REAL_ENDPOINTS.keys())


def _build_real_request(platform: str, payload: Dict, creds: Dict,
                         live: bool = False) -> Dict:
    """构造真实请求（method/url/headers/body）用于 dry-run 预览与真实发送。

    live=False（预览/dry-run）：不联网取 token，使用凭证中的 token 或占位符。
    live=True（真实发送）：Amazon 会联网取 LWA token 并做 SigV4 签名。
    """
    block = payload.get("gpsr_block", "")
    sku = creds.get("sku") or payload.get("product_name", "")
    if platform == "ebay":
        url = f"{_REAL_ENDPOINTS['ebay']}/{sku}"
        token = creds.get("oauth_token") or creds.get("access_token") or creds.get("token")
        return {
            "method": "PUT",
            "url": url,
            "headers": {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                        "Accept": "application/json"},
            "body": {"product": {"description": block}},
        }
    if platform in ("amazon", "amazon_us"):
        url = f"{_REAL_ENDPOINTS[platform]}/{sku}"
        token = (_fetch_lwa_token(creds) if live
                 else creds.get("token") or "<LWA_TOKEN_live_fetch>")
        body = {
            "productType": creds.get("product_type", "PRODUCT"),
            "patches": [{"op": "replace", "path": "/attributes/description",
                         "value": [{"locale": "default", "value": block}]}],
        }
        if live:
            headers = _aws_signed_headers(url, "PATCH", token, creds)
        else:
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        return {"method": "PATCH", "url": url, "headers": headers, "body": body}
    # 其余平台：沿用适配层字段（凭证就绪但真实 endpoint 待补 → 提示手动）
    target = backfill_target(platform)
    return {
        "method": "PATCH",
        "url": "(见 backfill_target.api_reference，真实 endpoint 待补)",
        "headers": {"Authorization": "Bearer <token>"},
        "body": {"description": block},
        "note": f"平台 {platform} 真实 endpoint 待补；字段/鉴权见：{target['api']}",
    }


def real_submit(platform: str, payload: Dict, creds: Dict):
    """真实发起 HTTP 写回（requests）。返回 requests.Response。"""
    req = _build_real_request(platform, payload, creds, live=True)
    return requests.request(
        req["method"], req["url"],
        headers=req["headers"],
        json=req.get("body"),
        timeout=20,
    )


def _fetch_lwa_token(creds: Dict) -> str:
    """Amazon LWA：用 client_id/secret + refresh_token 换取 access token。"""
    resp = requests.post(
        "https://api.amazon.com/auth/o2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": creds.get("refresh_token"),
            "client_id": creds.get("client_id"),
            "client_secret": creds.get("client_secret"),
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("access_token", "")


def _aws_signed_headers(url: str, method: str, token: str, creds: Dict) -> Dict:
    """为 Amazon SP-API 请求生成 AWS SigV4 签名头（AWS4-HMAC-SHA256）。

    纯 Python 实现（hmac/hashlib），无第三方依赖。
    region 默认 eu-west-1（欧洲站），可用 creds["region"] 覆盖。
    """
    region = creds.get("region", "eu-west-1")
    service = "execute-api"
    t = datetime.datetime.utcnow()
    amzdate = t.strftime("%Y%m%dT%H%M%SZ")
    datestamp = t.strftime("%Y%m%d")
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc
    canonical_uri = parsed.path or "/"
    canonical_querystring = ""
    payload_hash = hashlib.sha256(b"").hexdigest()

    canonical_headers = (
        f"host:{host}\n"
        f"x-amz-access-token:{token}\n"
        f"x-amz-date:{amzdate}\n"
    )
    signed_headers = "host;x-amz-access-token;x-amz-date"
    canonical_request = "\n".join([
        method, canonical_uri, canonical_querystring,
        canonical_headers, signed_headers, payload_hash,
    ])
    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{datestamp}/{region}/{service}/aws4_request"
    string_to_sign = "\n".join([
        algorithm, amzdate, credential_scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    ])
    k_date = _hmac(("AWS4" + creds.get("aws_secret", "")).encode("utf-8"), datestamp)
    k_region = _hmac(k_date, region)
    k_service = _hmac(k_region, service)
    k_signing = _hmac(k_service, "aws4_request")
    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"),
                         hashlib.sha256).hexdigest()
    authorization = (
        f"{algorithm} Credential={creds.get('aws_key','')}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    return {
        "Authorization": authorization,
        "x-amz-date": amzdate,
        "x-amz-access-token": token,
        "Content-Type": "application/json",
    }


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()
