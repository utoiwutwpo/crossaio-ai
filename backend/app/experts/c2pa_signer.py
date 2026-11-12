"""C2PA 风格的内容凭证：真 ES256 签名 + 真写入 JPEG/PNG 二进制元数据。

与 C2PA 的关系（必须说清）：
- 已实现：硬绑定哈希（c2pa.hash.data + 排除段）、claim 断言（c2pa.actions、
  Iptc4xmpExt:DigitalSourceType）、X.509 证书链、ES256 签名、篡改检测、
  真实嵌入 JPEG APP1(XMP)+APP11(C2PA) 与 PNG iTXt+caBX。
- 未实现：CBOR 编码与 COSE_Sign1 封装（本实现用 JSON），证书自签、未接 CA。
- 结论：签名可被本系统或任何持有公钥的第三方验证真伪，但不得宣称
  "通过 C2PA 官方验证"。
"""
import base64
import hashlib
import json
import os
import struct
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from . import c2pa_native as native

CERT_DIR = Path(os.environ.get("C2PA_CERT_DIR", Path(__file__).resolve().parents[2] / "certs"))
MAGIC = b"C2PA1"
XMP_NS = b"http://ns.adobe.com/xap/1.0/\x00"


def _ensure_keypair():
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    key_path = Path(os.environ.get("C2PA_KEY_PATH", CERT_DIR / "c2pa_key.pem"))
    cert_path = Path(os.environ.get("C2PA_CERT_PATH", CERT_DIR / "c2pa_cert.pem"))
    if key_path.exists() and cert_path.exists():
        key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        return key, x509.load_pem_x509_certificate(cert_path.read_bytes())

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "crossbot-ai C2PA Signer"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "crossbot-ai"),
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
    ])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .sign(key, hashes.SHA256()))
    key_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return key, cert


def signer_cert_pem() -> str:
    _, cert = _ensure_keypair()
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def _canon(claim: dict) -> bytes:
    return json.dumps(claim, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def xmp_packet(manifest: dict, *, producer: str = "") -> str:
    title = manifest.get("title") or manifest.get("dc:title") or ""
    generator = manifest.get("claim_generator") or "crossbot-ai/1.0"
    signed_at = str(manifest.get("signed_at") or "")[:19]
    return (
        '<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF '
        'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about="" '
        'xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" '
        'xmlns:xmp="http://ns.adobe.com/xap/1.0/" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'Iptc4xmpExt:DigitalSourceType='
        '"http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia" '
        f'xmp:CreatorTool="{producer or manifest["claim_generator"]}" '
        f'xmp:MetadataDate="{manifest["signed_at"][:19]}Z" '
        'xmp:Label="AI-generated">'
        f'<dc:title><rdf:Alt><rdf:li xml:lang="x-default">{title}</rdf:li></rdf:Alt></dc:title>'
        '</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>'
    )


def _seg_jpeg(data: bytes, manifest_payload: bytes, xmp: str) -> tuple:
    xmp_bytes = XMP_NS + xmp.encode("utf-8")
    xmp_seg = b"\xff\xe1" + struct.pack(">H", 2 + len(xmp_bytes)) + xmp_bytes
    c2pa_len = 2 + len(manifest_payload)
    if c2pa_len > 0xFFFF:
        raise ValueError("manifest 超出 JPEG APP11 单段上限")
    c2pa_seg = b"\xff\xeb" + struct.pack(">H", c2pa_len) + manifest_payload
    new = data[:2] + xmp_seg + c2pa_seg + data[2:]
    return new, 2, len(xmp_seg) + len(c2pa_seg)


def _seg_png(data: bytes, manifest_payload: bytes, xmp: str) -> tuple:
    def chunk(ctype: bytes, payload: bytes) -> bytes:
        return (struct.pack(">I", len(payload)) + ctype + payload
                + struct.pack(">I", zlib.crc32(ctype + payload) & 0xFFFFFFFF))

    itxt = (b"XML:com.adobe.xmp\x00\x00\x00\x00\x00" + xmp.encode("utf-8"))
    pos = 8 + 25                        # 签名(8) + IHDR 整块(25)
    blob = chunk(b"iTXt", itxt) + chunk(b"caBX", manifest_payload)
    new = data[:pos] + blob + data[pos:]
    return new, pos, len(blob)


def _embed(data: bytes, manifest_payload: bytes, xmp: str) -> tuple:
    if data[:2] == b"\xff\xd8":
        return _seg_jpeg(data, manifest_payload, xmp)
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return _seg_png(data, manifest_payload, xmp)
    raise ValueError("只支持 JPEG / PNG 二进制嵌入；其它格式仅产出 manifest 与 XMP")


def _find_manifest(data: bytes) -> dict | None:
    idx = data.find(MAGIC)
    if idx < 0:
        return None
    end = data.find(b"?>", idx)
    try:
        tail = data[idx + len(MAGIC):]
        obj, _ = json.JSONDecoder().raw_decode(tail.decode("utf-8", "ignore"))
        return obj if isinstance(obj, dict) and "assertions" in obj else None
    except Exception:
        return None


def build_manifest(asset: bytes, *, title: str = "", generator: str = "crossbot-ai/1.0",
                   producer: str = "", platform: str = "", source_id: str = "",
                   kind: str = "listing_image") -> dict:
    return {
        "claim_generator": generator,
        "title": title,
        "platform": platform,
        "source_id": source_id,
        "kind": kind,
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "assertions": [
            {"label": "c2pa.hash.data",
             "data": {"alg": "sha256", "hash": hashlib.sha256(asset).hexdigest(),
                      "exclusions": {"start": 0, "length": 0}}},
            {"label": "c2pa.actions",
             "data": {"actions": [{
                 "action": "c2pa.created",
                 "digitalSourceType":
                 "http://cv.IPTC.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia".replace("IPTC", "iptc"),
                 "softwareAgent": generator}]}},
            {"label": "stds.schema-org.CreativeWork",
             "data": {"@type": "CreativeWork", "name": title or kind,
                      "author": [{"@type": "Organization",
                                  "name": producer or generator}]}},
        ],
        "x5chain": [],
        "alg": "ES256",
    }


def sign_asset(data: bytes, *, title: str = "", platform: str = "",
               producer: str = "", source_id: str = "",
               kind: str = "listing_image") -> dict:
    return sign_asset_native(data, title=title, platform=platform,
                             producer=producer, source_id=source_id, kind=kind)


def sign_asset_legacy_json(data: bytes, *, title: str = "", platform: str = "",
                           producer: str = "", source_id: str = "",
                           kind: str = "listing_image") -> dict:
    key, cert = _ensure_keypair()
    manifest = build_manifest(data, title=title, platform=platform,
                              producer=producer, source_id=source_id, kind=kind)
    manifest["x5chain"] = [base64.b64encode(
        cert.public_bytes(serialization.Encoding.DER)).decode()]

    # 迭代收敛：嵌入 → 排除段重算哈希 → 改 claim → 重签，直到段长与哈希稳定
    signed, start, length = data, 0, 0
    for _ in range(6):
        payload = MAGIC + json.dumps(manifest, ensure_ascii=False).encode("utf-8")
        signed, start, length = _embed(data, payload, xmp_packet(manifest, producer=producer))
        stripped = signed[:start] + signed[start + length:]
        digest = hashlib.sha256(stripped).hexdigest()
        data_block = manifest["assertions"][0]["data"]
        if data_block["hash"] == digest and data_block["exclusions"]["length"] == length:
            break
        data_block["hash"] = digest
        data_block["exclusions"] = {"start": start, "length": length}
        manifest.pop("signature", None)
        manifest["signature"] = base64.b64encode(
            key.sign(_canon(manifest), ec.ECDSA(hashes.SHA256()))).decode()

    return {
        "mime": "image/jpeg" if signed[:2] == b"\xff\xd8" else "image/png",
        "bytes_b64": base64.b64encode(signed).decode(),
        "manifest": manifest,
        "xmp": xmp_packet(manifest, producer=producer),
        "verify": verify_asset(signed),
    }


def verify_asset(data: bytes) -> dict:
    native_result = verify_asset_native(data)
    if native_result.get("valid") or "JUMBF" not in str(native_result.get("reason", "")):
        return native_result
    manifest = _find_manifest(data)
    if not manifest:
        return {"valid": False, "reason": "未找到签名段"}
    ex = (manifest["assertions"][0]["data"].get("exclusions") or {})
    start, length = int(ex.get("start", 0)), int(ex.get("length", 0))
    if length <= 0:
        return {"valid": False, "reason": "排除段缺失"}
    stripped = data[:start] + data[start + length:]
    digest = hashlib.sha256(stripped).hexdigest()
    claimed = manifest["assertions"][0]["data"]["hash"]
    if digest != claimed:
        return {"valid": False, "reason": "资产哈希不匹配（文件被改动）",
                "claimed": claimed, "actual": digest}

    sig_b64 = manifest.get("signature", "")
    try:
        cert = x509.load_der_x509_certificate(base64.b64decode(manifest["x5chain"][0]))
        cert.public_key().verify(base64.b64decode(sig_b64),
                                 _canon({k: v for k, v in manifest.items()
                                         if k != "signature"}),
                                 ec.ECDSA(hashes.SHA256()))
        return {"valid": True, "reason": "哈希与 ES256 签名均通过",
                "signer": cert.subject.rfc4514_string(),
                "cert_valid_until": cert.not_valid_after_utc.strftime("%Y-%m-%d"),
                "self_signed": True, "c2pa_native": False,
                "note": "JSON manifest + 自签证书，官方 c2patool 不保证识别"}
    except Exception as e:
        return {"valid": False, "reason": f"验签失败：{type(e).__name__}"}


# ---------------- 原生 C2PA（CBOR + COSE_Sign1 + JUMBF） ----------------

def _locate_jumbf(data: bytes):
    idx = data.rfind(b"jumb")
    if idx < 4:
        return None, 0, 0
    start = idx - 4
    size = struct.unpack(">I", data[start:start + 4])[0]
    return data[start:start + size], start, size


def _strip_inserted(data: bytes) -> bytes:
    """按容器结构移除本系统插入的元数据段，得到原始资产。

    PNG：定位 IHDR 之后连续的两个 chunk（iTXt + caBX）；
    JPEG：从 SOI 之后连续跳过 APP1(XMP) 与 APP11(C2PA) 段。
    不依赖 claim 里的区间数字，避免循环收敛误差。
    """
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        pos = 8 + 25
        skip = 0
        for _ in range(2):
            if pos + 8 > len(data):
                break
            size = struct.unpack(">I", data[pos:pos + 4])[0]
            ctype = data[pos + 4:pos + 8]
            if ctype not in (b"iTXt", b"caBX"):
                break
            skip += 12 + size
            pos += 12 + size
        head = 8 + 25
        return data[:head] + data[head + skip:]

    if data[:2] == b"\xff\xd8":
        idx, skip = 2, 0
        while idx + 4 <= len(data):
            if data[idx] != 0xFF:
                break
            marker = data[idx + 1]
            if marker not in (0xE1, 0xEB):
                break
            seg = struct.unpack(">H", data[idx + 2:idx + 4])[0]
            skip += 2 + seg
            idx += 2 + seg
            if skip > 4_000_000:
                break
        return data[:2] + data[2 + skip:]

    return data


def _json_safe_assertions(claim: dict) -> list:
    out = []
    for a in claim.get("assertions") or []:
        data = dict(a.get("data") or {})
        if isinstance(data.get("hash"), (bytes, bytearray)):
            data["hash"] = bytes(data["hash"]).hex()
        out.append({"label": a.get("label", ""), "data": data})
    return out


def sign_asset_native(data: bytes, *, title: str = "", platform: str = "",
                      producer: str = "", source_id: str = "",
                      kind: str = "listing_image") -> dict:
    key, cert = _ensure_keypair()
    signed, start, length = data, 0, 0
    claim, jumbf = None, b""
    for _ in range(8):
        claim = native.build_claim(data, title=title, generator="crossbot-ai/1.0",
                                   producer=producer, platform=platform,
                                   source_id=source_id, kind=kind,
                                   exclusions={"start": start, "length": length})
        jumbf = native.build_manifest_jumbf(claim, native.cose_sign1(claim, key, cert))
        signed, start, new_len = _embed(data, jumbf, xmp_packet(claim, producer=producer))
        if new_len == length:
            break
        length = new_len

    return {
        "mime": "image/jpeg" if signed[:2] == b"\xff\xd8" else "image/png",
        "bytes_b64": base64.b64encode(signed).decode(),
        "structure": "jumbf+cbor+cose-sign1",
        "jumbf_len": len(jumbf),
        "manifest": {
            "claim_generator": claim["claim_generator"],
            "title": claim["dc:title"],
            "instanceID": claim["instanceID"],
            "signed_at": claim["signed_at"],
            "alg": "ES256",
            "assertions": _json_safe_assertions(claim),
        },
        "xmp": xmp_packet(claim, producer=producer),
        "verify": verify_asset_native(signed),
    }


def verify_asset_native(data: bytes) -> dict:
    try:
        jumbf, start, length = _locate_jumbf(data)
        if not jumbf:
            return {"valid": False, "reason": "未找到 JUMBF 段"}
        claim, cose = native.extract_claim_and_sig(jumbf)
        checked = native.cose_verify(cose)

        stripped = _strip_inserted(data)
        digest = hashlib.sha256(stripped).digest()
        claimed = claim["assertions"][0]["data"]["hash"]
        if isinstance(claimed, str):
            claimed = bytes.fromhex(claimed)
        if digest != claimed:
            return {"valid": False, "reason": "资产哈希不匹配（文件被改动）",
                    "claimed": claimed.hex(), "actual": digest.hex()}

        cert = checked["cert"]
        return {"valid": True, "reason": "CBOR claim + COSE_Sign1(ES256) + 哈希均通过",
                "structure": "jumbf+cbor+cose-sign1",
                "signer": cert.subject.rfc4514_string(),
                "cert_valid_until": cert.not_valid_after_utc.strftime("%Y-%m-%d"),
                "x5chain_len": 1, "self_signed": True, "c2pa_native": True,
                "c2patool_verified": False,
                "note": "结构与签名为 C2PA 原生编码；未经 CA 签发，不宣称通过官方 c2patool"}
    except Exception as e:
        return {"valid": False, "reason": f"校验失败：{type(e).__name__}: {str(e)[:160]}"}
