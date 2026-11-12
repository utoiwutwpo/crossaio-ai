"""内容溯源标记（Art.50(2)）。

诚实边界：本模块产出的是**未签名的声明骨架**（IPTC/XMP 字段 + C2PA 结构），
可用于平台元数据与侧车文件；真正的 C2PA 签名需要证书链，不在本版本内。
"""
import hashlib
from datetime import datetime, timezone
from typing import Optional


def build_provenance(text: str, *, model: Optional[str] = None,
                     platform: Optional[str] = None,
                     kind: str = "text",
                     source_id: Optional[str] = None) -> dict:
    digest = hashlib.sha256((text or "").encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    return {
        "ai_generated": True,
        "kind": kind,
        "platform": platform or "",
        "source_id": source_id or "",
        "generated_at": now,
        "model": model or "unknown",
        "content_hash": f"sha256:{digest}",
        "digital_source_type": "trainedAlgorithmicMedia",
        # 可直接写进图片/文档 XMP 的字段（IPTC Extension 1.1）
        "xmp_fields": {
            "Iptc4xmpExt:DigitalSourceType":
                "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia",
            "xmp:CreatorTool": model or "CrossAIO",
            "xmp:MetadataDate": now,
        },
        # C2PA 结构骨架（未签名，不可当作已验证凭证）
        "c2pa_manifest": {
            "claim_generator": f"CrossAIO/1.0 {model or ''}".strip(),
            "signed": False,
            "assertions": [
                {"label": "c2pa.actions", "data": {"actions": [
                    {"action": "c2pa.created", "digitalSourceType":
                     "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"}
                ]}},
                {"label": "c2pa.hash.data", "data": {"algorithm": "sha256",
                                                    "hash": digest}},
            ],
        },
        "note": "骨架未签名：Art.50(2) 要求机器可读标记，正式对外举证需证书链签名",
    }
