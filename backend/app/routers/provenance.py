"""内容溯源接口：为已生成的描述/文案产出可导出标记。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import ProductDescription, get_db, User
from ..experts.content_provenance import build_provenance

router = APIRouter()


class ProvenanceRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)
    model: str = ""
    platform: str = ""
    kind: str = "text"


@router.post("/build", summary="为一串文本生成溯源标记（XMP 字段 + C2PA 骨架）")
def build(req: ProvenanceRequest, user: User = Depends(get_current_user)):
    return build_provenance(req.text, model=req.model or None,
                            platform=req.platform or None, kind=req.kind)


@router.get("/descriptions/{description_id}", summary="按描述 ID 生成溯源标记")
def for_description(description_id: str, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    row = (db.query(ProductDescription)
           .filter(ProductDescription.id == description_id,
                   ProductDescription.user_id == user.id).first())
    if not row:
        raise HTTPException(404, "描述不存在")
    text = "\n".join([row.title or "", row.description or ""])
    return build_provenance(text, platform=row.platform,
                            kind="listing_description",
                            source_id=description_id)


class SignAssetRequest(BaseModel):
    image_base64: str = Field(..., min_length=16)
    title: str = ""
    platform: str = ""
    producer: str = ""
    source_id: str = ""
    kind: str = "listing_image"


@router.post("/sign-asset", summary="为图片做真签名并写入 JPEG/PNG 元数据")
def sign_asset_endpoint(req: SignAssetRequest, user: User = Depends(get_current_user)):
    """返回带签名的图片字节（base64）、manifest、XMP 与当场验签结果。"""
    import base64
    from ..experts.c2pa_signer import sign_asset

    try:
        data = base64.b64decode(req.image_base64, validate=False)
    except Exception:
        raise HTTPException(422, "image_base64 无法解码")
    if len(data) < 64:
        raise HTTPException(422, "图片字节过小")
    try:
        out = sign_asset(data, title=req.title, platform=req.platform,
                         producer=req.producer, source_id=req.source_id, kind=req.kind)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return out


@router.get("/signer-cert", summary="签名者证书（PEM，自签）")
def signer_cert():
    from ..experts.c2pa_signer import signer_cert_pem
    return {"pem": signer_cert_pem(), "self_signed": True,
            "note": "未接 CA 信任链；可对外分发公钥做真伪校验"}


class VerifyAssetRequest(BaseModel):
    image_base64: str


@router.post("/verify-asset", summary="校验带签图片：JUMBF/CBOR/COSE 解析 + 哈希与签名复核")
def verify_asset_endpoint(req: VerifyAssetRequest):
    import base64
    from ..experts.c2pa_signer import verify_asset_native

    try:
        data = base64.b64decode(req.image_base64, validate=False)
    except Exception:
        raise HTTPException(422, "image_base64 无法解码")
    return verify_asset_native(data)
