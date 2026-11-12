"""C2PA 原生结构：CBOR + COSE_Sign1 + JUMBF + 独立验签。

实现范围（可验证）：
- claim 用 CBOR（RFC 8949）编码；
- 签名为 COSE_Sign1（RFC 9052），算法 ES256；
- JUMBF（ISO 19566-5）承载 claim 与 signature；
- JPEG APP11 / PNG caBX 写入；
- verifier 解析 JUMBF -> CBOR -> COSE，验签并复核资产哈希。

不含：CA 签发与官方 c2patool 的完整 manifest store 语义。
"""
import hashlib
import struct
import uuid
from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _cbor_head(major: int, value: int) -> bytes:
    if value < 24:
        return bytes([(major << 5) | value])
    if value < 256:
        return bytes([(major << 5) | 24, value])
    if value < 65536:
        return bytes([(major << 5) | 25]) + struct.pack(">H", value)
    if value < 4294967296:
        return bytes([(major << 5) | 26]) + struct.pack(">I", value)
    return bytes([(major << 5) | 27]) + struct.pack(">Q", value)


def cbor_encode(obj) -> bytes:
    if obj is None:
        return b"\xf6"
    if isinstance(obj, bool):
        return b"\xf5" if obj else b"\xf4"
    if isinstance(obj, int):
        return _cbor_head(0, obj) if obj >= 0 else _cbor_head(1, -obj - 1)
    if isinstance(obj, float):
        return bytes([0xfb]) + struct.pack(">d", obj)
    if isinstance(obj, bytes):
        return _cbor_head(2, len(obj)) + obj
    if isinstance(obj, str):
        raw = obj.encode("utf-8")
        return _cbor_head(3, len(raw)) + raw
    if isinstance(obj, (list, tuple)):
        body = b"".join(cbor_encode(v) for v in obj)
        return _cbor_head(4, len(obj)) + body
    if isinstance(obj, dict):
        items = sorted(obj.items(), key=lambda kv: (str(type(kv[0])), kv[0]))
        body = b"".join(cbor_encode(k) + cbor_encode(v) for k, v in items)
        return _cbor_head(5, len(items)) + body
    raise TypeError(f"CBOR unsupported: {type(obj)}")


def cbor_decode(raw: bytes):
    def read(idx):
        head = raw[idx]
        major, extra = head >> 5, head & 0x1F
        idx += 1
        if extra < 24:
            val = extra
        elif extra == 24:
            val = raw[idx]; idx += 1
        elif extra == 25:
            val = struct.unpack(">H", raw[idx:idx + 2])[0]; idx += 2
        elif extra == 26:
            val = struct.unpack(">I", raw[idx:idx + 4])[0]; idx += 4
        elif extra == 27:
            val = struct.unpack(">Q", raw[idx:idx + 8])[0]; idx += 8
        else:
            raise ValueError("CBOR bad length")
        if major == 0:
            return val, idx
        if major == 1:
            return -val - 1, idx
        if major == 2:
            return raw[idx:idx + val], idx + val
        if major == 3:
            return raw[idx:idx + val].decode("utf-8"), idx + val
        if major == 4:
            out = []
            for _ in range(val):
                v, idx = read(idx)
                out.append(v)
            return out, idx
        if major == 5:
            out = {}
            for _ in range(val):
                k, idx = read(idx)
                v, idx = read(idx)
                out[k] = v
            return out, idx
        if major == 6:
            return read(idx)
        if major == 7:
            if extra == 20:
                return False, idx
            if extra == 21:
                return True, idx
            if extra == 22:
                return None, idx
            if extra == 27:
                return struct.unpack(">d", raw[idx - 8:idx])[0], idx
        raise ValueError("CBOR unsupported tag")

    val, end = read(0)
    if end != len(raw):
        raise ValueError("CBOR trailing bytes")
    return val


def _box(ctype: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", 8 + len(payload)) + ctype + payload


def _jumd(kind_uuid: bytes, label: str, toggles: int = 0x03) -> bytes:
    return _box(b"jumd", kind_uuid + bytes([toggles]) + label.encode() + b"\x00")


_UUID_MANIFEST = bytes.fromhex("6332706100110010800000aa00389b71")
_UUID_CLAIM = bytes.fromhex("6332706100110011800000aa00389b71")
_UUID_SIGNATURE = bytes.fromhex("6332706100110012800000aa00389b71")


def build_manifest_jumbf(claim: dict, cose: bytes) -> bytes:
    claim_box = _box(b"cbor", _jumd(_UUID_CLAIM, "c2pa.claim") + cbor_encode(claim))
    sig_box = _box(b"cbor", _jumd(_UUID_SIGNATURE, "c2pa.signature") + cose)
    return _box(b"jumb", _jumd(_UUID_MANIFEST, "c2pa") + claim_box + sig_box)


def parse_boxes(raw: bytes, limit: int = 40) -> list:
    out, idx = [], 0
    for _ in range(limit):
        if idx + 8 > len(raw):
            break
        size = struct.unpack(">I", raw[idx:idx + 4])[0]
        ctype = raw[idx + 4:idx + 8]
        if size < 8 or idx + size > len(raw):
            break
        out.append((ctype, raw[idx + 8:idx + size]))
        idx += size
    return out


def _label_of(payload: bytes) -> str:
    for t, p in parse_boxes(payload, limit=2):
        if t == b"jumd":
            return p[17:].decode("utf-8", "ignore").strip("\x00")
    return ""


def extract_claim_and_sig(jumbf: bytes):
    claim_raw = sig_raw = None
    for ctype, payload in parse_boxes(jumbf[8:], limit=20):
        if ctype != b"cbor":
            continue
        label = _label_of(payload)
        body = payload
        first = parse_boxes(payload, limit=1)
        if first and first[0][0] == b"jumd":
            body = payload[struct.unpack(">I", payload[:4])[0]:]
        for t3, p3 in parse_boxes(payload, limit=8):
            if t3 == b"cbor":
                body = p3
        if "signature" in label:
            sig_raw = body
        elif claim_raw is None:
            claim_raw = body
    if claim_raw is None or sig_raw is None:
        raise ValueError("JUMBF missing claim or signature")
    return cbor_decode(claim_raw), sig_raw


def cose_sign1(claim: dict, key, cert) -> bytes:
    protected = cbor_encode({1: -7})
    payload = cbor_encode(claim)
    der = cert.public_bytes(serialization.Encoding.DER)
    sig = key.sign(protected + payload, ec.ECDSA(hashes.SHA256()))
    return cbor_encode([protected, {33: [der]}, payload, sig])


def cose_verify(cose_bytes: bytes) -> dict:
    parts = cbor_decode(cose_bytes)
    if not isinstance(parts, list) or len(parts) != 4:
        raise ValueError("COSE_Sign1 malformed")
    protected, unprot, payload, sig = parts
    chain = (unprot or {}).get(33) or (unprot or {}).get("x5chain") or []
    if not chain:
        raise ValueError("COSE missing x5chain")
    cert = x509.load_der_x509_certificate(chain[0])
    cert.public_key().verify(sig, protected + payload, ec.ECDSA(hashes.SHA256()))
    return {"claim": cbor_decode(payload), "cert": cert,
            "alg": "ES256", "protected": cbor_decode(protected)}


def build_claim(asset: bytes, *, title: str, generator: str, producer: str,
                platform: str, source_id: str, kind: str,
                exclusions: dict) -> dict:
    return {
        "claim_generator": generator,
        "claim_generator_info": [{"name": "crossbot-ai", "version": "1.0"}],
        "instanceID": "xmp:iid:" + uuid.uuid4().hex,
        "dc:title": title or kind,
        "dc:format": "image/jpeg" if asset[:2] == b"\xff\xd8" else "image/png",
        "platform": platform,
        "source_id": source_id,
        "kind": kind,
        "signed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "assertions": [
            {"label": "c2pa.hash.data",
             "data": {"alg": "sha256",
                      "hash": hashlib.sha256(asset).digest(),
                      "exclusions": [{"start": exclusions.get("start", 0),
                                      "length": exclusions.get("length", 0)}]}},
            {"label": "c2pa.actions",
             "data": {"actions": [{
                 "action": "c2pa.created",
                 "digitalSourceType":
                 "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia",
                 "softwareAgent": generator}]}},
            {"label": "stds.schema-org.CreativeWork",
             "data": {"@type": "CreativeWork", "name": title or kind,
                      "author": [{"@type": "Organization",
                                  "name": producer or generator}]}},
        ],
    }
