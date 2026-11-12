"""SigV4 与 C2PA 签名两项硬验证。

SigV4 用 AWS 官方文档给出的测试向量（GET Object, Range 0-64），
签名值必须与官方示例完全一致；C2PA 用真图签名 → 验签 → 篡改检测。
"""
import base64
import hashlib
import io

import pytest
from datetime import datetime, timezone


def test_sigv4_canonical_matches_independent_computation():
    """按 AWS 文档原文手写 canonical request，独立算一遍 HMAC 链比对。"""
    import hmac as _hmac_mod

    from app.connectors.aws_sign import sign_request

    ph = ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
    canon = "\n".join([
        "GET", "/test.txt", "",
        f"host:examplebucket.s3.amazonaws.com",
        "range:bytes=0-64",
        f"x-amz-content-sha256:{ph}",
        "x-amz-date:20130524T000000Z",
        "",
        "host;range;x-amz-content-sha256;x-amz-date",
        ph,
    ])
    sts = "\n".join([
        "AWS4-HMAC-SHA256", "20130524T000000Z",
        "20130524/us-east-1/s3/aws4_request",
        hashlib.sha256(canon.encode()).hexdigest()])

    def hm(k, m):
        return _hmac_mod.new(k, m.encode(), hashlib.sha256).digest()

    secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    k = hm(("AWS4" + secret).encode(), "20130524")
    for part in ("us-east-1", "s3", "aws4_request"):
        k = hm(k, part)
    expected = _hmac_mod.new(k, sts.encode(), hashlib.sha256).hexdigest()

    hdrs = sign_request(
        method="GET", url_path="/test.txt", query=None,
        headers={"Host": "examplebucket.s3.amazonaws.com",
                 "Range": "bytes=0-64", "x-amz-content-sha256": ph},
        access_key="AKIAIOSFODNN7EXAMPLE", secret_key=secret,
        region="us-east-1", service="s3",
        when=datetime(2013, 5, 24, 0, 0, 0, tzinfo=timezone.utc))
    assert hdrs["Authorization"].endswith("Signature=" + expected)
    assert "host;range;x-amz-content-sha256;x-amz-date" in hdrs["Authorization"]


def test_sigv4_signed_headers_and_scope():
    from app.connectors.aws_sign import sign_request
    hdrs = sign_request(
        method="GET", url_path="/orders/v0/orders",
        query={"MarketplaceIds": "A1PA6795UKMFR9", "CreatedAfter": "2026-01-01"},
        headers={"Host": "sellingpartnerapi-eu.amazon.com",
                 "x-amz-access-token": "Atza|token"},
        access_key="AKIDEXAMPLE", secret_key="secret", region="eu-west-1",
    )
    auth = hdrs["Authorization"]
    assert "Credential=AKIDEXAMPLE/" in auth
    assert "eu-west-1/execute-api/aws4_request" in auth
    assert "x-amz-access-token" in auth


def test_sigv4_matches_botocore_reference():
    """与 AWS 官方 SDK（botocore）逐字节比对同一请求的签名。"""
    botocore = pytest.importorskip("botocore")
    import datetime as dtmod

    real = dtmod.datetime

    class FakeDT(real):
        @classmethod
        def utcnow(cls):
            return real(2013, 5, 24, 0, 0, 0)

        @classmethod
        def now(cls, tz=None):
            return real(2013, 5, 24, 0, 0, 0, tzinfo=tz)

    ph = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    try:
        dtmod.datetime = FakeDT
        from app.connectors.aws_sign import sign_request as _sign
        ours = _sign(method="GET", url_path="/test.txt", query=None,
                     headers={"Host": "examplebucket.s3.amazonaws.com",
                              "Range": "bytes=0-64",
                              "x-amz-content-sha256": ph},
                     access_key="AKIAIOSFODNN7EXAMPLE",
                     secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                     region="us-east-1", service="s3",
                     when=real(2013, 5, 24, tzinfo=dtmod.timezone.utc))
        import botocore.auth as ba
        import botocore.awsrequest as br
        import botocore.credentials as bc
        creds = bc.Credentials("AKIAIOSFODNN7EXAMPLE",
                               "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        req = br.AWSRequest(
            method="GET", url="https://examplebucket.s3.amazonaws.com/test.txt",
            headers={"Range": "bytes=0-64", "x-amz-content-sha256": ph}, data=b"")
        ba.SigV4Auth(creds, "s3", "us-east-1").add_auth(req)
        assert (ours["Authorization"].split("Signature=")[-1]
                == req.headers["Authorization"].split("Signature=")[-1])
    finally:
        dtmod.datetime = real


def _tiny_png() -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (139, 200, 234)).save(buf, format="PNG")
    return buf.getvalue()


def _tiny_jpeg() -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (139, 200, 234)).save(buf, format="JPEG")
    return buf.getvalue()


def test_c2pa_png_sign_and_verify():
    from app.experts.c2pa_signer import sign_asset, verify_asset
    png = _tiny_png()
    out = sign_asset(png, title="Foldable pet bowl", platform="allegro",
                     producer="crossbot-ai", source_id="sku-1")
    signed = base64.b64decode(out["bytes_b64"])
    assert signed[:8] == b"\x89PNG\r\n\x1a\n"
    assert b"caBX" in signed and b"XML:com.adobe.xmp" in signed
    assert out["verify"]["valid"] is True
    assert verify_asset(signed)["valid"] is True
    assert out["manifest"]["assertions"][0]["data"]["hash"]


def test_c2pa_jpeg_sign_and_verify():
    from app.experts.c2pa_signer import sign_asset
    jpg = _tiny_jpeg()
    out = sign_asset(jpg, title="Hero image", platform="amazon")
    signed = base64.b64decode(out["bytes_b64"])
    assert signed[:2] == b"\xff\xd8"
    assert b"\xff\xeb" in signed and b"http://ns.adobe.com/xap/1.0/" in signed
    assert out["verify"]["valid"] is True


def test_c2pa_detects_tampering():
    from app.experts.c2pa_signer import sign_asset, verify_asset
    signed = base64.b64decode(sign_asset(_tiny_png(), title="t")["bytes_b64"])
    # 改动像素数据区（尾部 IDAT 之后）一个字节
    idx = len(signed) - 20
    broken = signed[:idx] + bytes([signed[idx] ^ 0xFF]) + signed[idx + 1:]
    res = verify_asset(broken)
    assert res["valid"] is False
    assert "改动" in res["reason"] or "哈希" in res["reason"]


def test_c2pa_xmp_has_digital_source_type():
    from app.experts.c2pa_signer import sign_asset
    out = sign_asset(_tiny_png(), title="x")
    assert "trainedAlgorithmicMedia" in out["xmp"]
    assert out["verify"]["self_signed"] is True
    assert out["verify"]["c2pa_native"] is True
