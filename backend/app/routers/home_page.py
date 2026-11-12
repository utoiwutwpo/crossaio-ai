"""/zh 完整首页（能力地图版）所需的静态资产路由。

首页本身仍由 main.py 已有的 /zh/ 路由读取 static/home.html 提供，
本文件只新增 /zh/home-assets/** 前缀，用于取回首页的样式与实拍图。
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

_DIR = Path(__file__).resolve().parent.parent / "static" / "site-preview" / "home-assets"
# 图片体积大、改动少：允许浏览器与 CDN 缓存 7 天，避免每次进首页都重下 1.9MB 实拍图。
# CSS 仍禁缓存，保证改版后样式立即生效。
_IMG_HEADERS = {"Cache-Control": "public, max-age=604800"}
_CSS_HEADERS = {"Cache-Control": "no-cache, no-store, must-revalidate"}
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
    return FileResponse(_DIR / name, media_type=media,
                        headers=_IMG_HEADERS if media.startswith("image/") else _CSS_HEADERS)
