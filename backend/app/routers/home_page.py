"""/zh 完整首页（能力地图版）所需的静态资产路由。

首页本身仍由 main.py 已有的 /zh/ 路由读取 static/home.html 提供，
本文件只新增 /zh/home-assets/** 前缀，用于取回首页的样式与实拍图。
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

_DIR = Path(__file__).resolve().parent.parent / "static" / "site-preview" / "home-assets"
_HEADERS = {"Cache-Control": "no-cache, no-store, must-revalidate"}
_FILES = {
    "site.css": "text/css",
    "nav.css": "text/css",
    "hero-man.jpg": "image/jpeg",
    "pl-pack.jpg": "image/jpeg",
    "night-call.jpg": "image/jpeg",
    "ops-screens.jpg": "image/jpeg",
    "boss-meeting.jpg": "image/jpeg",
}


@router.get("/zh/home-assets/{name}", include_in_schema=False)
def home_asset(name: str):
    media = _FILES.get(name)
    if not media:
        raise HTTPException(status_code=404)
    return FileResponse(_DIR / name, media_type=media, headers=_HEADERS)
