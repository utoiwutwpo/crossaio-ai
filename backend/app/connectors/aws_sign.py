"""AWS Signature Version 4（真实现，用于 Amazon SP-API 直连）。

只依赖 hashlib/hmac，签名算法按 AWS 官方文档实现：
  canonical_request → string_to_sign → HMAC 链 → Authorization 头
"""
import hashlib
import hmac
from datetime import datetime, timezone
from urllib.parse import quote

ALGO = "AWS4-HMAC-SHA256"


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_query(params: dict) -> str:
    """按 AWS 规则排序并 URL 编码（空格 %20、斜杠保留编码）。"""
    if not params:
        return ""
    items = []
    for k in sorted(params):
        v = params[k]
        if v is None:
            continue
        items.append((quote(str(k), safe="-_.~"), quote(str(v), safe="-_.~")))
    return "&".join(f"{k}={v}" for k, v in items)


def signing_key(secret: str, date: str, region: str, service: str) -> bytes:
    k_date = _hmac(("AWS4" + secret).encode("utf-8"), date)
    k_region = _hmac(k_date, region)
    k_service = _hmac(k_region, service)
    return _hmac(k_service, "aws4_request")


def sign_request(*, method: str, url_path: str, query: dict | None,
                 headers: dict, payload: bytes | str = b"",
                 access_key: str, secret_key: str, region: str,
                 service: str = "execute-api",
                 when: datetime | None = None) -> dict:
    """返回需要附加到请求上的全部头（含 Authorization）。"""
    now = (when or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    date = now[:8]
    payload_bytes = payload.encode("utf-8") if isinstance(payload, str) else payload
    payload_hash = _sha256_hex(payload_bytes or b"")

    hdrs = {k.lower(): str(v).strip() for k, v in headers.items()}
    hdrs["host"] = hdrs.get("host", "")
    hdrs["x-amz-date"] = now
    signed_names = ";".join(sorted(hdrs))
    canonical_headers = "".join(f"{k}:{hdrs[k]}\n" for k in sorted(hdrs))

    uri = url_path if url_path.startswith("/") else "/" + url_path
    creq = "\n".join([method.upper(), uri, canonical_query(query or {}),
                      canonical_headers, signed_names, payload_hash])
    scope = f"{date}/{region}/{service}/aws4_request"
    sts = "\n".join([ALGO, now, scope, _sha256_hex(creq.encode("utf-8"))])
    sig = hmac.new(signing_key(secret_key, date, region, service),
                   sts.encode("utf-8"), hashlib.sha256).hexdigest()

    out = {k: v for k, v in hdrs.items() if k not in ("host", "x-amz-date")}
    out["x-amz-date"] = now
    out["Authorization"] = (
        f"{ALGO} Credential={access_key}/{scope}, "
        f"SignedHeaders={signed_names}, Signature={sig}")
    return out
